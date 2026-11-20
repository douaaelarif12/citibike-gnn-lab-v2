import pytest
from fastapi.testclient import TestClient

from api.main import app, service

client = TestClient(app)


def test_health_and_real_metrics_are_available():
    health = client.get("/api/health")
    assert health.status_code == 200
    assert isinstance(health.json()["dataset_available"], bool)
    metrics = client.get("/api/metrics")
    assert metrics.status_code == 200
    assert {item["model"] for item in metrics.json()} == {
        "Naive", "Saisonnier 24 h", "GCN-GRU enrichi"
    }


def test_unknown_export_is_rejected():
    assert client.get("/api/downloads/secret.txt").status_code == 404


def test_experiment_validation_rejects_unsupported_history():
    response = client.post("/api/experiments", json={"name": "bad-history", "history": 8})
    assert response.status_code == 422


def test_experiment_launch_is_disabled_without_server_secret():
    response = client.post("/api/experiments", json={"name": "safe-public-api"})
    assert response.status_code == 503


@pytest.mark.skipif(not service.raw_csv.exists(), reason="Local Citi Bike CSV is not distributed")
def test_graph_uses_real_named_stations_and_weighted_links():
    response = client.get("/api/graph", params={"limit": 10000})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["nodes"]) == 216
    assert len(payload["edges"]) == 6362
    assert all(node["name"] and node["observations"] > 0 for node in payload["nodes"])
    assert all(edge["source"] != edge["target"] and edge["weight"] > 0 for edge in payload["edges"])
    assert payload["edges"] == sorted(payload["edges"], key=lambda edge: edge["weight"], reverse=True)


def test_real_station_predictions_and_seasonal_baseline_are_available():
    response = client.get("/api/stations/JC115/predictions")
    assert response.status_code == 200
    payload = response.json()
    assert payload["station"]["name"] == "Grove St PATH"
    assert len(payload["predictions"]) == 108
    assert set(payload["predictions"][0]) == {
        "timestamp", "actual", "gcn_gru", "naive", "seasonal_24h"
    }
    metrics = client.get("/api/metrics").json()
    seasonal = next(item for item in metrics if item["model"] == "Saisonnier 24 h")
    assert seasonal["mae"] == pytest.approx(0.8158864975)
    assert seasonal["rmse"] == pytest.approx(2.0505340099)
