# ThermoIntel deployment

## Local / SIH demonstration

1. Start Docker Desktop.
2. Run `RUN_THERMOINTEL.bat`.
3. Open `http://localhost:5173`.
4. API health: `http://localhost:8000/health`.

The dashboard is same-origin with the API inside Docker through nginx, so the containerized build does not depend on a hard-coded localhost API URL.

## Data pipeline

- PostgreSQL + PostGIS stores raw and processed geospatial data.
- NASA FIRMS/VIIRS ingestion refreshes continuously.
- OSM industrial infrastructure is stored India-wide.
- Thermal detections are clustered into canonical events.
- Industrial spatial context is calculated with PostGIS.
- Source classification and classification confidence are calculated by the intelligence service.
- Risk intelligence is calculated after classification.

## Large datasets

The Events and Facilities APIs return **all available records by default**. The React pages load the complete dataset but render it in client-side pages so tens of thousands of facilities/events do not create a huge DOM and blank the browser.

## Existing database upgrade

The backend performs a runtime schema repair for the classification fields and invalidates obsolete `THERMAL ANOMALY` labels. The next intelligence refresh recomputes the source classification.

## Security

Keep the NASA FIRMS map key in the local `.env` file and do not commit credentials to source control.
