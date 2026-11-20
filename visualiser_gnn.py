"""Visualisations des prédictions réelles du modèle Citi Bike GCN-GRU sauvegardé.
Exécution : python visualiser_gnn.py depuis la racine du projet.
"""
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from api.services import ArtifactService
from src.preprocessing import load_data, build_activity, create_sequences, add_calendar_features
from src.models import GCNGRU

ROOT = Path(__file__).resolve().parent
CSV = ROOT / 'data' / 'raw' / 'JC-202604-citibike-tripdata.csv'
CHECKPOINT = ROOT / 'outputs' / 'models' / 'gcn_gru_retrained.pth'
FIGURES = ROOT / 'outputs' / 'figures'


def save_figure(fig, filename):
    destination = FIGURES / filename
    temporary = FIGURES / f'.{filename}.tmp.png'
    try:
        fig.savefig(temporary, dpi=160)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    for p in (CSV, CHECKPOINT):
        if not p.exists():
            sys.exit(f'ERREUR : fichier manquant : {p}')
    FIGURES.mkdir(parents=True, exist_ok=True)

    print('1/5 Chargement des données...')
    data = load_data(CSV)
    X, _, stations, hours = build_activity(data, '2026-04-01 00:00:00', '2026-04-30 23:00:00')

    # Le mode restreint évite l'exécution d'objets Python arbitraires.
    checkpoint = torch.load(CHECKPOINT, map_location='cpu', weights_only=True)
    history = int(checkpoint['history'])
    if list(stations) != list(checkpoint['station_ids']):
        sys.exit('ERREUR : les stations du CSV ne correspondent pas au checkpoint.')
    print(f'2/5 Préparation de {len(stations)} stations et historique de {history} heures...')
    X_seq, y_seq = create_sequences(add_calendar_features(X, hours), history=history)
    n = len(X_seq)
    val_end = int(n * .85)
    X_test = X_seq[val_end:].clone()
    y_test = y_seq[val_end:].numpy()
    naive = X_seq[val_end:, -1, :, :2].sum(-1).numpy()
    seasonal_start = history + val_end - 24
    seasonal_end = history + n - 24
    seasonal = X[seasonal_start:seasonal_end, :, :2].sum(-1).numpy()
    mean = checkpoint['activity_mean']
    std = checkpoint['activity_std']
    X_test[..., :2] = (X_test[..., :2] - mean) / std
    time_test = hours[history + val_end:history + n]

    model = GCNGRU(input_features=6)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    edge_index = checkpoint['edge_index']
    print('3/5 Calcul des prédictions réelles du GCN-GRU...')
    predictions = []
    with torch.no_grad():
        for i, sample in enumerate(X_test):
            predictions.append(model(sample, edge_index).numpy())
            if (i+1) % 25 == 0:
                print(f'    {i+1}/{len(X_test)} heures traitées')
    predicted = np.stack(predictions)
    assert predicted.shape == y_test.shape == naive.shape

    def metrics(a, b):
        return float(np.abs(a-b).mean()), float(np.sqrt(((a-b)**2).mean()))

    mae, rmse = metrics(predicted, y_test)
    naive_mae, naive_rmse = metrics(naive, y_test)
    seasonal_mae, seasonal_rmse = metrics(seasonal, y_test)
    print(f'    GCN-GRU : MAE={mae:.4f}, RMSE={rmse:.4f}')
    print(f'    Naïf    : MAE={naive_mae:.4f}, RMSE={naive_rmse:.4f}')
    print(f'    Saisonnier 24 h : MAE={seasonal_mae:.4f}, RMSE={seasonal_rmse:.4f}')

    print('4/5 Création des figures et fichiers CSV...')
    plt.rcParams.update({'figure.figsize': (12, 5), 'axes.grid': True, 'grid.alpha': .2})

    # 1. Activité agrégée : sommes à travers toutes les stations
    actual_total = y_test.sum(axis=1)
    pred_total = predicted.sum(axis=1)
    naive_total = naive.sum(axis=1)
    seasonal_total = seasonal.sum(axis=1)
    fig, ax = plt.subplots()
    ax.plot(time_test, actual_total, label='Réel', linewidth=2)
    ax.plot(time_test, pred_total, label='GCN-GRU', alpha=.85)
    ax.set(title='Activité horaire totale : réel vs GCN-GRU', ylabel='Départs + arrivées / heure', xlabel='Date et heure')
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    save_figure(fig, '01_reel_vs_gnn.png')
    plt.close(fig)

    # 2. Comparaison avec la baseline naïve
    fig, ax = plt.subplots()
    ax.plot(time_test, actual_total, label='Réel', linewidth=2)
    ax.plot(time_test, pred_total, label='GCN-GRU', alpha=.8)
    ax.plot(time_test, naive_total, label='Naïf', alpha=.7)
    ax.set(title='Comparaison sur la période de test', ylabel='Mouvements / heure', xlabel='Date et heure')
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()
    save_figure(fig, '02_comparaison_modeles.png')
    plt.close(fig)

    # 3. Les 3 stations les plus actives sur la période de test
    popular = np.argsort(y_test.sum(axis=0))[-3:][::-1]
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    for ax, j in zip(axes, popular):
        ax.plot(time_test, y_test[:, j], label='Réel', linewidth=1.7)
        ax.plot(time_test, predicted[:, j], label='GCN-GRU', linewidth=1.4)
        ax.set(ylabel='Mouvements', title=f'Station {stations[j]}')
        ax.legend(loc='upper right')
    axes[-1].set_xlabel('Date et heure')
    fig.autofmt_xdate()
    fig.tight_layout()
    save_figure(fig, '03_stations_actives.png')
    plt.close(fig)

    # 4. Erreur absolue moyenne par station (top 20 selon activité)
    station_mae = np.abs(predicted - y_test).mean(axis=0)
    top20 = np.argsort(y_test.sum(axis=0))[-20:][::-1]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(top20)), station_mae[top20])
    ax.set_xticks(range(len(top20)), [str(stations[j]) for j in top20], rotation=75, ha='right')
    ax.set(title='MAE par station (20 stations les plus actives)', ylabel='MAE (mouvements)')
    fig.tight_layout()
    save_figure(fig, '04_erreurs_par_station.png')
    plt.close(fig)

    pd.DataFrame({
        'heure': time_test,
        'reel_total': actual_total,
        'gcn_gru_total': pred_total,
        'naif_total': naive_total,
        'saisonnier_24h_total': seasonal_total,
    }).to_csv(ROOT / 'outputs' / 'predictions_horaires_test.csv', index=False)

    pd.DataFrame({
        'timestamp': np.repeat(time_test.to_numpy(), len(stations)),
        'station_id': np.tile(np.asarray(stations, dtype=str), len(time_test)),
        'actual': y_test.reshape(-1),
        'gcn_gru': predicted.reshape(-1),
        'naive': naive.reshape(-1),
        'seasonal_24h': seasonal.reshape(-1),
    }).to_csv(ROOT / 'outputs' / 'predictions_stations_test.csv', index=False)

    pd.DataFrame([
        {'Modele': 'Naive', 'MAE': naive_mae, 'RMSE': naive_rmse},
        {'Modele': 'Saisonnier 24 h', 'MAE': seasonal_mae, 'RMSE': seasonal_rmse},
        {'Modele': 'GCN-GRU enrichi', 'MAE': mae, 'RMSE': rmse},
    ]).to_csv(ROOT / 'outputs' / 'extended_comparison.csv', index=False)

    pd.DataFrame({
        'station_id': [str(s) for s in stations],
        'activite_test': y_test.sum(axis=0),
        'mae_gcn_gru': station_mae,
        'mae_naif': np.abs(naive-y_test).mean(axis=0),
    }).to_csv(ROOT / 'outputs' / 'erreurs_par_station.csv', index=False)

    network = ArtifactService(ROOT).export_network_artifacts()

    print('5/5 Terminé ! Résultats enregistrés dans outputs/figures/')
    for name in ['01_reel_vs_gnn.png', '02_comparaison_modeles.png',
                 '03_stations_actives.png', '04_erreurs_par_station.png']:
        print('  ', FIGURES / name)
    print('CSV : prédictions agrégées, prédictions par station, métriques locales et comparaison étendue')
    print(f"Réseau public agrégé : {network['stations']} stations, {network['edges']} connexions")

if __name__ == '__main__':
    main()
