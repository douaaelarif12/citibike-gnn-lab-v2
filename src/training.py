"""Reproducible experiment runner for CitiBike forecasting."""
from copy import deepcopy
from pathlib import Path
import time

import torch
import torch.nn as nn

from .config import ExperimentConfig
from .graph_builder import build_graph
from .models import GCNGRU, GRUBaseline
from .preprocessing import (add_calendar_features, build_activity,
                            chronological_split, create_sequences,
                            fit_activity_scaler, load_data, transform_activity)
from .utils import append_jsonl, calculate_metrics, save_checkpoint, set_seed


def _criterion(name, train_targets):
    if name == "mse":
        return nn.MSELoss()
    if name == "mae":
        return nn.L1Loss()
    if name == "huber":
        return nn.HuberLoss()
    threshold = torch.quantile(train_targets, 0.90)

    def peak_weighted(predictions, targets):
        weights = torch.where(targets >= threshold, 3.0, 1.0)
        return (weights * (predictions - targets).square()).mean()
    return peak_weighted


def _predict(model, data, edge_index, edge_weight):
    model.eval()
    with torch.no_grad():
        return torch.stack([model(sample, edge_index, edge_weight) for sample in data])


def run_experiment(config: ExperimentConfig, csv_path, output_dir):
    config.validate()
    set_seed(config.seed)
    started = time.perf_counter()
    output_dir = Path(output_dir)
    data = load_data(csv_path)
    X, _, stations, hours = build_activity(data, "2026-04-01", "2026-04-30 23:00:00")
    sequences, targets = create_sequences(add_calendar_features(X, hours), config.history)
    split = chronological_split(len(sequences))
    train_x, val_x, test_x = (sequences[split.train_slice], sequences[split.val_slice],
                              sequences[split.test_slice])
    train_y, val_y, test_y = (targets[split.train_slice], targets[split.val_slice],
                              targets[split.test_slice])
    mean, std = fit_activity_scaler(train_x)
    train_x, val_x, test_x = [transform_activity(part, mean, std)
                              for part in (train_x, val_x, test_x)]
    first_validation_target = hours[config.history + split.train_end]
    graph, edge_index, edge_weight = build_graph(
        data, stations, first_validation_target, weighted=config.graph == "weighted")
    if config.architecture == "gru":
        model = GRUBaseline(6, config.gru_hidden, config.dropout, config.non_negative)
    else:
        model = GCNGRU(6, config.gcn_hidden, config.gru_hidden,
                       config.dropout, config.non_negative)
    criterion = _criterion(config.loss, train_y)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=2, factor=0.5)
    best_loss, best_state, stale = float("inf"), None, 0
    for _epoch in range(config.epochs):
        model.train()
        for sample, target in zip(train_x, train_y):
            optimizer.zero_grad()
            loss = criterion(model(sample, edge_index, edge_weight), target)
            loss.backward()
            optimizer.step()
        val_loss = float(criterion(_predict(model, val_x, edge_index, edge_weight), val_y))
        scheduler.step(val_loss)
        if val_loss < best_loss - 1e-6:
            best_loss, best_state, stale = val_loss, deepcopy(model.state_dict()), 0
        else:
            stale += 1
            if stale >= config.patience:
                break
    model.load_state_dict(best_state)
    predictions = _predict(model, test_x, edge_index, edge_weight)
    metrics = calculate_metrics(predictions, test_y)
    naive = sequences[split.test_slice, -1, :, :2].sum(-1)
    result = {
        "status": "completed", "config": config.to_dict(), "metrics": metrics,
        "naive_metrics": calculate_metrics(naive, test_y),
        "stations": len(stations), "edges": graph.number_of_edges(),
        "test_samples": len(test_y), "duration_seconds": time.perf_counter() - started,
    }
    version = f"{config.name}-seed{config.seed}"
    save_checkpoint(model, output_dir / "models" / f"{version}.pth",
                    activity_mean=mean, activity_std=std, edge_index=edge_index,
                    edge_weight=edge_weight, station_ids=stations,
                    history=config.history, config=config.to_dict(), metrics=metrics)
    append_jsonl(result, output_dir / "experiments.jsonl")
    return result
