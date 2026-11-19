from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ExperimentConfig:
    name: str = "gcn_gru_h6_mse"
    history: int = 6
    architecture: str = "gcn_gru"
    loss: str = "mse"
    graph: str = "binary"
    gcn_hidden: int = 16
    gru_hidden: int = 32
    dropout: float = 0.0
    learning_rate: float = 0.001
    epochs: int = 30
    patience: int = 5
    seed: int = 42
    non_negative: bool = True

    def validate(self):
        if self.history not in {6, 12, 24}:
            raise ValueError("history doit valoir 6, 12 ou 24")
        if self.architecture not in {"gcn_gru", "gru"}:
            raise ValueError("architecture non prise en charge")
        if self.loss not in {"mse", "mae", "huber", "peak_weighted"}:
            raise ValueError("loss non prise en charge")
        if self.graph not in {"binary", "weighted"}:
            raise ValueError("graph doit valoir binary ou weighted")
        if self.epochs < 1 or self.patience < 1:
            raise ValueError("epochs et patience doivent être positifs")
        return self

    def to_dict(self):
        return asdict(self)
