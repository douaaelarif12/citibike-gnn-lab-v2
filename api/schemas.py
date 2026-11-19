from typing import Literal

from pydantic import BaseModel, Field


class ExperimentRequest(BaseModel):
    name: str = Field(regex=r"^[a-zA-Z0-9_-]{3,64}$")
    history: Literal[6, 12, 24] = 6
    architecture: Literal["gcn_gru", "gru"] = "gcn_gru"
    loss: Literal["mse", "mae", "huber", "peak_weighted"] = "huber"
    graph: Literal["binary", "weighted"] = "binary"
    gcn_hidden: int = Field(16, ge=4, le=128)
    gru_hidden: int = Field(32, ge=4, le=256)
    dropout: float = Field(0.1, ge=0, lt=0.8)
    learning_rate: float = Field(0.001, gt=0, le=0.1)
    epochs: int = Field(20, ge=1, le=500)
    patience: int = Field(5, ge=1, le=50)
    seed: int = Field(42, ge=0, le=2**31 - 1)
    non_negative: bool = True
