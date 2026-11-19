
"""Data loading and leakage-safe temporal preprocessing."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch


@dataclass(frozen=True)
class TemporalSplit:
    train_end: int
    val_end: int
    total: int

    @property
    def train_slice(self):
        return slice(0, self.train_end)

    @property
    def val_slice(self):
        return slice(self.train_end, self.val_end)

    @property
    def test_slice(self):
        return slice(self.val_end, self.total)


def load_data(csv_path):
    df = pd.read_csv(
        csv_path,
        dtype={
            "start_station_id": "string",
            "end_station_id": "string"
        },
        parse_dates=["started_at", "ended_at"]
    )

    required = [
        "started_at", "ended_at",
        "start_station_id", "end_station_id",
        "start_lat", "start_lng",
        "end_lat", "end_lng"
    ]

    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Colonnes Citi Bike manquantes : {missing}")

    df = df.dropna(subset=required).copy()
    df = df.sort_values("started_at", kind="stable").reset_index(drop=True)

    return df


def build_activity(df, start_date, end_date):
    stations = sorted(
        set(df["start_station_id"])
        | set(df["end_station_id"])
    )

    hours = pd.date_range(
        start=start_date,
        end=end_date,
        freq="h"
    )

    departures = (
        df.assign(
            time_window=df["started_at"].dt.floor("h")
        )
        .groupby(["time_window", "start_station_id"])
        .size()
        .rename("departures")
    )
    departures.index = departures.index.set_names(
        ["time_window", "station_id"]
    )

    arrivals = (
        df.assign(
            time_window=df["ended_at"].dt.floor("h")
        )
        .groupby(["time_window", "end_station_id"])
        .size()
        .rename("arrivals")
    )
    arrivals.index = arrivals.index.set_names(
        ["time_window", "station_id"]
    )

    index = pd.MultiIndex.from_product(
        [hours, stations],
        names=["time_window", "station_id"]
    )

    activity = pd.concat(
        [departures, arrivals], axis=1
    ).reindex(index, fill_value=0).fillna(0)

    activity = activity.reset_index()

    X = torch.tensor(
        activity[["departures", "arrivals"]].to_numpy(),
        dtype=torch.float32
    ).reshape(len(hours), len(stations), 2)

    y = X.sum(dim=-1)

    return X, y, stations, hours


def create_sequences(X, history=6):
    if history < 1:
        raise ValueError("history doit être supérieur ou égal à 1")
    if len(X) <= history:
        raise ValueError("Pas assez d'heures pour construire les séquences")
    inputs = []
    targets = []

    for t in range(history - 1, len(X) - 1):
        inputs.append(X[t-history+1:t+1])
        targets.append(X[t+1, :, :2].sum(dim=-1))

    return torch.stack(inputs), torch.stack(targets)


def chronological_split(length, train_ratio=0.70, val_ratio=0.15):
    """Return contiguous train/validation/test boundaries without shuffling."""
    if length < 3:
        raise ValueError("Au moins trois séquences sont nécessaires")
    if not (0 < train_ratio < 1 and 0 < val_ratio < 1):
        raise ValueError("Les ratios doivent être compris entre 0 et 1")
    train_end = int(length * train_ratio)
    val_end = train_end + int(length * val_ratio)
    if train_end == 0 or val_end >= length:
        raise ValueError("Découpage train/validation/test invalide")
    return TemporalSplit(train_end=train_end, val_end=val_end, total=length)


def fit_activity_scaler(X_train):
    """Fit activity scaling from training inputs only."""
    if X_train.ndim != 4 or X_train.shape[-1] < 2:
        raise ValueError("Forme attendue : [samples, history, stations, features]")
    activity = X_train[..., :2]
    mean = activity.mean(dim=(0, 1, 2), keepdim=True)
    std = activity.std(dim=(0, 1, 2), keepdim=True).clamp(min=1e-6)
    return mean, std


def transform_activity(X, mean, std):
    result = X.clone()
    result[..., :2] = (result[..., :2] - mean) / std
    return result


def add_calendar_features(X, hours):
    hour_values = hours.hour.to_numpy()
    day_values = hours.dayofweek.to_numpy()

    calendar = torch.tensor(
        np.column_stack([
            np.sin(2 * np.pi * hour_values / 24),
            np.cos(2 * np.pi * hour_values / 24),
            np.sin(2 * np.pi * day_values / 7),
            np.cos(2 * np.pi * day_values / 7)
        ]),
        dtype=torch.float32
    )

    calendar = calendar.unsqueeze(1).expand(
        -1, X.shape[1], -1
    )

    return torch.cat([X, calendar], dim=-1)
