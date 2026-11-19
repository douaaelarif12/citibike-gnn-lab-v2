
import networkx as nx
import torch


def build_graph(df, stations, cutoff, weighted=False):
    """Build a training-only directed graph and optional trip-frequency weights."""
    cutoff = cutoff if hasattr(cutoff, "tzinfo") else cutoff
    train_df = df[(df["started_at"] < cutoff) & (df["ended_at"] < cutoff)]

    graph = nx.DiGraph()
    graph.add_nodes_from(stations)

    for start, end in zip(
        train_df["start_station_id"],
        train_df["end_station_id"]
    ):
        if start != end:
            if graph.has_edge(start, end):
                graph[start][end]["weight"] += 1.0
            else:
                graph.add_edge(start, end, weight=1.0)

    node_to_idx = {
        station: idx
        for idx, station in enumerate(stations)
    }

    edges = [
        [node_to_idx[u], node_to_idx[v]]
        for u, v in graph.edges()
    ]

    if edges:
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    else:
        edge_index = torch.empty((2, 0), dtype=torch.long)

    edge_weight = None
    if weighted:
        weights = [float(graph[u][v]["weight"]) for u, v in graph.edges()]
        edge_weight = torch.tensor(weights, dtype=torch.float32)
        if edge_weight.numel():
            edge_weight = edge_weight / edge_weight.mean().clamp(min=1e-6)

    return graph, edge_index, edge_weight
