import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, GATConv


class GCNModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = GCNConv(2, 16)
        self.conv2 = GCNConv(16, 1)

    def forward(self, x, edge_index):
        x = F.relu(self.conv1(x, edge_index))
        return self.conv2(x, edge_index).squeeze(-1)


class GATModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = GATConv(2, 8, heads=2, concat=True)
        self.conv2 = GATConv(16, 1, heads=1, concat=False)

    def forward(self, x, edge_index):
        x = F.relu(self.conv1(x, edge_index))
        return self.conv2(x, edge_index).squeeze(-1)


class GCNGRU(nn.Module):
    def __init__(self, input_features=2, gcn_hidden=16, gru_hidden=32,
                 dropout=0.0, non_negative=False):
        super().__init__()
        self.gcn = GCNConv(input_features, gcn_hidden)
        self.gru = nn.GRU(
            input_size=gcn_hidden,
            hidden_size=gru_hidden,
            batch_first=True
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(gru_hidden, 1)
        self.non_negative = non_negative

    def forward(self, x, edge_index, edge_weight=None):
        # x: [history, stations, features]
        spatial = []

        for t in range(x.shape[0]):
            z = F.relu(self.gcn(x[t], edge_index, edge_weight=edge_weight))
            spatial.append(z)

        # [stations, history, 16]
        spatial = torch.stack(spatial, dim=1)

        temporal, _ = self.gru(spatial)

        output = self.fc(self.dropout(temporal[:, -1, :])).squeeze(-1)
        return F.softplus(output) if self.non_negative else output


class GRUBaseline(nn.Module):
    """Temporal baseline with no graph message passing."""
    def __init__(self, input_features=2, hidden_size=32, dropout=0.0,
                 non_negative=False):
        super().__init__()
        self.gru = nn.GRU(input_features, hidden_size, batch_first=True)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_size, 1)
        self.non_negative = non_negative

    def forward(self, x, edge_index=None, edge_weight=None):
        station_sequences = x.permute(1, 0, 2)
        temporal, _ = self.gru(station_sequences)
        output = self.fc(self.dropout(temporal[:, -1])).squeeze(-1)
        return F.softplus(output) if self.non_negative else output
