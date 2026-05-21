# SKAI Hackathon MVP Boilerplate

Minimal offline starter for the hackathon idea: **Data -> Logic -> UI -> Action**.

## What is inside

- `app/app.py` - Streamlit UI with tabs: Data, Dashboard, Details.
- `app/data_loader.py` - CSV loading from `./data`, fallback to `./sample_data`.
- `app/metrics.py` - small placeholders for task-specific scoring and tables.
- `sample_data/` - tiny demo CSV files.
- `data/` - put local task data here.
- `output/` - app actions and exports go here.

## Prepared data

This task already includes the video + telemetry dataset in `data/`:

- `selected_video_alarms.csv`
- `video_files.csv`
- `track_summary.csv`
- `track_periods.csv`
- `track_points.csv`
- `max_speed_points.csv`
- `vehicles.csv`
- `work_rest_single_vehicle/` with 6 Drowsiness events on one vehicle.

Video paths in `video_files.csv` are relative to the project root, for example `datasets/media/video_events/...`.

## Run on Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app/app.py
```

If script activation is blocked:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Run on macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app/app.py
```

## Hackathon rules baked into this template

- Work offline by default: CSV files and local media folders only.
- Keep logic explainable: rules, scoring, simple analytics, small AI helpers if they work locally.
- Do not build production architecture: no auth, no real SKAI production integrations, no Kubernetes, no microservices.
- Finish two user flows, one value metric, and one action that writes to `./output`.
