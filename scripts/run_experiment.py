import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import ExperimentConfig  # noqa: E402
from src.training import run_experiment  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="gcn_gru_h6_huber")
    parser.add_argument("--history", type=int, choices=[6, 12, 24], default=6)
    parser.add_argument("--architecture", choices=["gcn_gru", "gru"], default="gcn_gru")
    parser.add_argument("--loss", choices=["mse", "mae", "huber", "peak_weighted"], default="huber")
    parser.add_argument("--graph", choices=["binary", "weighted"], default="binary")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    config = ExperimentConfig(**vars(args))
    print(run_experiment(config, ROOT / "data/raw/JC-202604-citibike-tripdata.csv", ROOT / "outputs"))


if __name__ == "__main__":
    main()
