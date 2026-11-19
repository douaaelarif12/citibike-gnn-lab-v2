# Contributing to CitiBike GNN Lab v2

Thank you for helping improve this applied spatio-temporal forecasting project.

## Scientific rules

- Keep train, validation, and test splits chronological.
- Fit scalers only on training inputs.
- Build experimental graphs without validation or test leakage.
- Select hyperparameters on validation data, not the final test set.
- Never present planned or simulated values as measured results.
- Preserve the original checkpoint and reference metrics.
- Do not commit raw Citi Bike data, model checkpoints, secrets, or local experiment logs.

## Development setup

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cd frontend
npm install
cd ..
```

## Required checks

Run these commands before proposing a change:

```powershell
.\.venv\Scripts\python.exe -m ruff check api src tests scripts
.\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run lint
npm test
npm run build
```

For interface changes, also verify the affected flow in Google Chrome with the local FastAPI service connected to the React application.

## Pull requests

Describe:

1. the problem being solved;
2. the files and behavior changed;
3. the real data or artifacts used;
4. the tests executed and their exact outcomes;
5. any remaining limitations.

Keep pull requests focused. Do not combine model-protocol changes with unrelated interface refactors unless both are required for the same feature.
