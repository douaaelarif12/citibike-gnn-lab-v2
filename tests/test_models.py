import torch

from src.models import GCNGRU, GRUBaseline


def test_gcn_gru_forward_shape_and_non_negative_output():
    model = GCNGRU(input_features=6, non_negative=True)
    sample = torch.randn(6, 5, 6)
    edge_index = torch.tensor([[0, 1, 2, 3], [1, 2, 3, 4]])
    output = model(sample, edge_index)
    assert output.shape == (5,)
    assert torch.all(output >= 0)


def test_gru_baseline_forward_shape():
    model = GRUBaseline(input_features=6)
    assert model(torch.randn(12, 7, 6)).shape == (7,)
