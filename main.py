
from pathlib import Path

import pandas as pd
import torch
import torch.nn as nn

from src.preprocessing import (
    load_data,
    build_activity,
    create_sequences,
    add_calendar_features,
    chronological_split,
    fit_activity_scaler,
    transform_activity,
)
from src.graph_builder import build_graph
from src.models import GCNGRU
from src.utils import calculate_metrics, save_checkpoint


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data/raw/JC-202604-citibike-tripdata.csv"
OUTPUT_DIR = ROOT / "outputs"

HISTORY = 6
EPOCHS = 10
LEARNING_RATE = 0.001


def predict(model, X_data, edge_index):
    model.eval()
    predictions = []

    with torch.no_grad():
        for sample in X_data:
            predictions.append(model(sample, edge_index))

    return torch.stack(predictions)


def main():
    torch.manual_seed(42)

    print("=== GNN SPATIO-TEMPOREL : CITI BIKE ===")

    # 1. Chargement
    df = load_data(CSV_PATH)

    X, y, stations, hours = build_activity(
        df,
        "2026-04-01 00:00:00",
        "2026-04-30 23:00:00",
    )

    print(f"Trajets : {len(df)}")
    print(f"Stations : {len(stations)}")

    # 2. Séquences et calendrier
    X_enriched = add_calendar_features(X, hours)

    X_seq, y_seq = create_sequences(
        X_enriched, history=HISTORY
    )

    # 3. Découpage chronologique
    split = chronological_split(len(X_seq))
    train_end, val_end = split.train_end, split.val_end

    X_train = X_seq[:train_end]
    X_val = X_seq[train_end:val_end]
    X_test = X_seq[val_end:]

    y_train = y_seq[:train_end]
    y_val = y_seq[train_end:val_end]
    y_test = y_seq[val_end:]

    # 4. Graphe d'entraînement
    # Dernière cible d'entraînement :
    # index train_end + HISTORY - 1.
    # Le graphe n'utilise pas la validation.
    cutoff = hours[train_end + HISTORY]

    graph, edge_index, edge_weight = build_graph(
        df, stations, cutoff
    )

    print(f"Arêtes : {graph.number_of_edges()}")

    # 5. Normalisation de l'activité
    mean, std = fit_activity_scaler(X_train)
    X_train = transform_activity(X_train, mean, std)
    X_val = transform_activity(X_val, mean, std)
    X_test = transform_activity(X_test, mean, std)

    # 6. Modèle
    model = GCNGRU(input_features=6)

    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(
        model.parameters(), lr=LEARNING_RATE
    )

    # 7. Entraînement
    best_val_loss = float("inf")
    best_state = None

    import copy

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0

        for sample, target in zip(X_train, y_train):
            optimizer.zero_grad()

            prediction = model(sample, edge_index)
            loss = criterion(prediction, target)

            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        train_loss = total_loss / len(X_train)

        val_predictions = predict(
            model, X_val, edge_index
        )
        val_loss = criterion(
            val_predictions, y_val
        ).item()

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = copy.deepcopy(
                model.state_dict()
            )

        print(
            f"Epoch {epoch+1:02d}/{EPOCHS} | "
            f"Train: {train_loss:.4f} | "
            f"Val: {val_loss:.4f}"
        )

    # 8. Restaurer le meilleur modèle
    model.load_state_dict(best_state)

    # 9. Évaluation
    predictions = predict(
        model, X_test, edge_index
    )

    model_metrics = calculate_metrics(
        predictions, y_test
    )

    # Baseline naïve
    naive_predictions = (
        X_seq[val_end:, -1, :, :2].sum(dim=-1)
    )

    naive_metrics = calculate_metrics(
        naive_predictions, y_test
    )

    print("\n=== RÉSULTATS TEST ===")
    print("GCN-GRU enrichi :", model_metrics)
    print("Naïve :", naive_metrics)

    # 10. Sauvegarde
    OUTPUT_DIR.mkdir(
        parents=True, exist_ok=True
    )

    pd.DataFrame([
        {"Modele": "Naive", **naive_metrics},
        {"Modele": "GCN-GRU enrichi", **model_metrics},
    ]).to_csv(
        OUTPUT_DIR / "reproducible_comparison.csv",
        index=False,
    )

    save_checkpoint(
        model,
        OUTPUT_DIR / "models/gcn_gru_v2_reference.pth",
        activity_mean=mean,
        activity_std=std,
        edge_index=edge_index,
        edge_weight=edge_weight,
        station_ids=stations,
        history=HISTORY,
    )

    print("\nProjet exécuté avec succès !")


if __name__ == "__main__":
    main()
