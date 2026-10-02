# ThermoIntel — final submission run

## One-command run

1. Start **Docker Desktop**. PostgreSQL does NOT need to be installed on Windows.
2. Open this folder in VS Code.
3. Run `RUN_THERMOINTEL.bat`. No Python virtual environment and no separate frontend/backend terminal are required.
4. Open `http://localhost:5173`.

## What starts

- PostGIS database inside Docker on host port `55432`
- FastAPI backend on `8000`
- India-wide OpenStreetMap industrial baseline ingestion
- NASA FIRMS VIIRS NOAA-21 NRT, 7-day thermal ingestion
- Spatial/temporal thermal event clustering
- Explainable thermal classification
- Industrial spatial context
- Evidence-fused risk intelligence
- Thermal satellite visualization on the dashboard, including NOAA-21 / NOAA-20 / Suomi-NPP VIIRS thermal-anomaly layers
- Event View with direct PostGIS nearby-facility lookup (nearest + up to 10 nearby facilities)
- 60-second live FIRMS refresh for the latest day, while retaining the canonical 7-day event population

## Dashboard windows

`LIVE` means the complete currently retained 7-day canonical dataset. `24 HOURS`, `3 DAYS`, and `7 DAYS` are rolling filters over that same dataset. The backend and dashboard use the same selected window for event counts and summaries.

## Stop

Run `STOP_THERMOINTEL.bat`.

## Reset data

Run `RESET_THERMOINTEL.bat` only when a completely fresh database is required.

## Important

The thermal classification is an explainable screening layer. A satellite thermal anomaly is not by itself proof of a confirmed fire.

## Live refresh
The backend refreshes the latest FIRMS day every 60 seconds. The frontend dashboard, Events page, and Risk Analysis refresh on the same 60-second cadence. This is intentionally separate from the initial 7-day bootstrap so the system does not redownload the full 7-day dataset every minute.

## Classification and confidence

Thermal Events now uses the ThermoIntel **source classification confidence** (percentage) instead of displaying FIRMS's raw categorical `l/n/h` value in the class-confidence column. Event details show both separately:

- Class Confidence: ThermoIntel evidence-fusion confidence
- FIRMS Detection Confidence: NASA FIRMS `Low`, `Nominal`, or `High`

Events and facilities are loaded without an application-side 1000/5000 record cap; the UI uses client-side pagination for responsiveness.
