from collections import Counter, defaultdict
import csv
import json
from pathlib import Path


class ArtifactService:
    def __init__(self, root: Path):
        self.root = root
        self.outputs = root / "outputs"
        self.raw_csv = root / "data" / "raw" / "JC-202604-citibike-tripdata.csv"
        self._stations = None
        self._edges = None
        self._station_predictions = None

    @staticmethod
    def _rows(path):
        if not path.exists():
            return []
        with path.open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))

    def comparisons(self):
        extended = self.outputs / "extended_comparison.csv"
        source = extended if extended.exists() else self.outputs / "reproducible_comparison.csv"
        rows = self._rows(source)
        return [{"model": row["Modele"], "mae": float(row["MAE"]),
                 "rmse": float(row["RMSE"]), "source": source.name}
                for row in rows]

    def predictions(self):
        rows = self._rows(self.outputs / "predictions_horaires_test.csv")
        return [{"timestamp": row["heure"], "actual": float(row["reel_total"]),
                 "gcn_gru": float(row["gcn_gru_total"]), "naive": float(row["naif_total"]),
                 "seasonal_24h": float(row["saisonnier_24h_total"])
                 if row.get("saisonnier_24h_total") else None}
                for row in rows]

    def station_predictions(self, station_id=None):
        if self._station_predictions is None:
            rows = self._rows(self.outputs / "predictions_stations_test.csv")
            grouped = defaultdict(list)
            for row in rows:
                grouped[row["station_id"]].append({
                    "timestamp": row["timestamp"],
                    "actual": float(row["actual"]),
                    "gcn_gru": float(row["gcn_gru"]),
                    "naive": float(row["naive"]),
                    "seasonal_24h": float(row["seasonal_24h"]),
                })
            self._station_predictions = dict(grouped)
        if station_id is None:
            return self._station_predictions
        return self._station_predictions.get(station_id, [])

    def station_errors(self):
        rows = self._rows(self.outputs / "erreurs_par_station.csv")
        return [{"station_id": row["station_id"], "activity": float(row["activite_test"]),
                 "gcn_gru_mae": float(row["mae_gcn_gru"]),
                 "naive_mae": float(row["mae_naif"])} for row in rows]

    def _load_network(self):
        coordinates = defaultdict(list)
        station_names = defaultdict(Counter)
        edges = Counter()
        if not self.raw_csv.exists():
            self._stations, self._edges = [], []
            return
        with self.raw_csv.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                start, end = row.get("start_station_id"), row.get("end_station_id")
                try:
                    coordinates[start].append((float(row["start_lat"]), float(row["start_lng"])))
                    coordinates[end].append((float(row["end_lat"]), float(row["end_lng"])))
                except (TypeError, ValueError, KeyError):
                    continue
                start_name, end_name = row.get("start_station_name"), row.get("end_station_name")
                if start and start_name:
                    station_names[start][start_name] += 1
                if end and end_name:
                    station_names[end][end_name] += 1
                if start and end and start != end:
                    edges[(start, end)] += 1
        self._stations = [{"id": station,
                           "name": station_names[station].most_common(1)[0][0]
                           if station_names[station] else station,
                           "lat": sum(p[0] for p in points) / len(points),
                           "lng": sum(p[1] for p in points) / len(points),
                           "observations": len(points)}
                          for station, points in sorted(coordinates.items()) if station]
        self._edges = [{"source": source, "target": target, "weight": weight}
                       for (source, target), weight in edges.most_common()]

    def stations(self):
        if self._stations is None:
            self._load_network()
        return self._stations

    def edges(self):
        if self._edges is None:
            self._load_network()
        return self._edges

    def experiments(self):
        path = self.outputs / "experiments.jsonl"
        if not path.exists():
            return []
        with path.open(encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]

    def model_files(self):
        folder = self.outputs / "models"
        return [{"name": path.stem, "filename": path.name, "bytes": path.stat().st_size}
                for path in sorted(folder.glob("*.pth"))]
