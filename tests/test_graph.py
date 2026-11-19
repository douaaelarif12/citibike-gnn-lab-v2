import pandas as pd

from src.graph_builder import build_graph


def test_graph_excludes_trips_crossing_validation_cutoff():
    frame = pd.DataFrame({
        "start_station_id": ["A", "B"], "end_station_id": ["B", "A"],
        "started_at": pd.to_datetime(["2026-04-01 01:00", "2026-04-02 01:00"]),
        "ended_at": pd.to_datetime(["2026-04-01 01:10", "2026-04-02 01:10"]),
    })
    graph, edge_index, weights = build_graph(frame, ["A", "B"], pd.Timestamp("2026-04-02"), weighted=True)
    assert list(graph.edges()) == [("A", "B")]
    assert edge_index.shape == (2, 1)
    assert weights.tolist() == [1.0]
