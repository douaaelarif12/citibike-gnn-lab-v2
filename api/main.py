from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .schemas import ExperimentRequest
from .services import ArtifactService
from .tasks import ExperimentTasks

ROOT = Path(__file__).resolve().parents[1]
service = ArtifactService(ROOT)
tasks = ExperimentTasks(ROOT)

app = FastAPI(title="CitiBike GNN Lab v2 API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"status": "ok", "dataset_available": service.raw_csv.exists()}


@app.get("/api/overview")
def overview():
    comparisons = service.comparisons()
    predictions = service.predictions()
    errors = service.station_errors()
    return {"stations": len(errors), "test_hours": len(predictions),
            "models": len(comparisons), "comparisons": comparisons,
            "data_source": "Jersey City Citi Bike — April 2026"}


@app.get("/api/stations")
def stations():
    return service.stations()


@app.get("/api/graph")
def graph(limit: int = Query(1000, ge=1, le=10000)):
    return {"nodes": service.stations(), "edges": service.edges()[:limit]}


@app.get("/api/models")
def models():
    return service.model_files()


@app.get("/api/metrics")
def metrics():
    return service.comparisons()


@app.get("/api/predictions")
def predictions():
    return service.predictions()


@app.get("/api/stations/{station_id}")
def station_detail(station_id: str):
    error = next((item for item in service.station_errors() if item["station_id"] == station_id), None)
    station = next((item for item in service.stations() if item["id"] == station_id), None)
    if not error and not station:
        raise HTTPException(404, "Station inconnue")
    return {"station": station, "evaluation": error}


@app.get("/api/experiments")
def experiments():
    return {"completed": service.experiments(), "tasks": tasks.all()}


@app.post("/api/experiments", status_code=202)
def launch_experiment(request: ExperimentRequest):
    return tasks.submit(request.dict())


@app.get("/api/experiments/{task_id}")
def experiment_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "Expérience inconnue")
    return task


@app.get("/api/downloads/{filename}")
def download(filename: str):
    allowed = {"reproducible_comparison.csv", "predictions_horaires_test.csv",
               "erreurs_par_station.csv", "model_comparison.csv"}
    if filename not in allowed:
        raise HTTPException(404, "Export inconnu")
    path = service.outputs / filename
    if not path.exists():
        raise HTTPException(404, "Export indisponible")
    return FileResponse(path, filename=filename)
