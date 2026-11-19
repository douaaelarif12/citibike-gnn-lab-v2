import pytest
import torch

from src.preprocessing import (chronological_split, create_sequences,
                               fit_activity_scaler, transform_activity)


def test_sequences_have_aligned_shapes_and_next_hour_targets():
    values = torch.arange(10 * 3 * 2, dtype=torch.float32).reshape(10, 3, 2)
    inputs, targets = create_sequences(values, history=4)
    assert inputs.shape == (6, 4, 3, 2)
    assert targets.shape == (6, 3)
    torch.testing.assert_close(inputs[0], values[:4])
    torch.testing.assert_close(targets[0], values[4].sum(-1))


def test_split_is_contiguous_and_keeps_test_isolated():
    split = chronological_split(100)
    assert split.train_slice == slice(0, 70)
    assert split.val_slice == slice(70, 85)
    assert split.test_slice == slice(85, 100)


def test_scaler_ignores_validation_and_test_values():
    train = torch.ones((4, 2, 3, 2))
    validation = torch.full((2, 2, 3, 2), 10_000.0)
    mean, std = fit_activity_scaler(train)
    assert mean.flatten().tolist() == [1.0, 1.0]
    transformed = transform_activity(validation, mean, std)
    assert torch.all(transformed > 1_000)


def test_invalid_history_fails_clearly():
    with pytest.raises(ValueError, match="history"):
        create_sequences(torch.zeros((3, 2, 2)), history=0)
