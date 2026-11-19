
from pathlib import Path
import json
import os
import random
import tempfile
from datetime import datetime, timezone

import numpy as np
import torch
import pandas as pd


def calculate_metrics(predictions, targets):
    if predictions.shape != targets.shape:
        raise ValueError("Dimensions incompatibles")

    error = predictions - targets

    mae = torch.mean(torch.abs(error)).item()
    rmse = torch.sqrt(torch.mean(error ** 2)).item()

    bias = torch.mean(error).item()
    return {"MAE": mae, "RMSE": rmse, "bias": bias}


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


def append_jsonl(record, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched = {"created_at": datetime.now(timezone.utc).isoformat(), **record}
    with output_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(enriched, ensure_ascii=False) + "\n")


def save_results(results, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(results).to_csv(
        output_path,
        index=False
    )


def save_checkpoint(model, path, **metadata):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"model_state_dict": model.state_dict(), **metadata}
    handle, temporary_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    os.close(handle)
    try:
        torch.save(payload, temporary_name)
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
