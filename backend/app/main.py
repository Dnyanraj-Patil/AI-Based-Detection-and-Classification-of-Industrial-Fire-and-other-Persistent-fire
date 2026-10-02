"""ThermoIntel FastAPI application entrypoint.

The API server must become available independently of the FIRMS/processing
pipeline.  Data ingestion and derived-intelligence refresh therefore run in
background tasks instead of blocking FastAPI startup.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.db.database import engine
from app.db.migrations import ensure_schema

from app.api.dashboard import router as dashboard_router
from app.api.events import router as events_router
from app.api.facilities import router as facilities_router
from app.api.firms import router as firms_router
from app.api.intelligence import router as legacy_intelligence_router
from app.api.risk import router as risk_router
from app.api.locations import router as locations_router
from app.api.routes.intelligence import router as intelligence_router
from app.services.event_clustering import cluster_firms_events
from app.services.event_intelligence_service import (
    process_all_event_intelligence,
)
from app.services.event_repository import save_thermal_events
from app.services.event_risk_service import process_all_event_risk
from app.services.firms_ingestion import ingest_firms_events
from app.services.industrial_context_service import (
    process_all_event_industrial_context,
)
from app.services.ml_anomaly_service import train_or_refresh_ml_model
from app.services.landcover_service import process_recent_landcover


# ============================================================
# CONFIGURATION
# ============================================================

FIRMS_INGEST_INTERVAL = 60  # seconds

logger = logging.getLogger("thermointel")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# Prevent two refresh pipelines from running at the same time.
_pipeline_lock = asyncio.Lock()


def ensure_runtime_schema() -> None:
    """Ensure classification columns exist and invalidate obsolete labels.

    Docker init SQL handles fresh databases. This small runtime migration also
    makes an existing PostgreSQL volume self-healing after an application
    upgrade, which prevents stale ``THERMAL ANOMALY`` rows from surviving.
    """
    statements = (
        """
        ALTER TABLE IF EXISTS processed.event_intelligence
        ADD COLUMN IF NOT EXISTS classification VARCHAR(100)
        """,
        """
        ALTER TABLE IF EXISTS processed.event_intelligence
        ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0
        """,
        """
        ALTER TABLE IF EXISTS processed.event_intelligence
        ADD COLUMN IF NOT EXISTS class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb
        """,
        """
        UPDATE processed.event_intelligence
        SET classification = NULL,
            classification_confidence = 0,
            class_probabilities = '{}'::jsonb
        WHERE UPPER(COALESCE(classification, '')) IN ('THERMAL ANOMALY', 'OTHER THERMAL ANOMALY')
        """,
    )
    # Apply the complete idempotent application schema first. This is essential
    # after RESET_THERMOINTEL, because Docker init scripts only run on a new volume.
    ensure_schema()
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))



# ============================================================
# DERIVED INTELLIGENCE PIPELINE
# ============================================================

def refresh_derived_intelligence() -> dict[str, Any]:
    """Rebuild thermal events and all derived intelligence tables.

    This function is synchronous because the underlying services/database
    operations are synchronous.  Call it through asyncio.to_thread() from
    FastAPI background tasks so the event loop remains responsive.
    """

    logger.info("Starting derived intelligence refresh")

    events = cluster_firms_events()
    saved = save_thermal_events(events)
    context = process_all_event_industrial_context()
    land_cover = process_recent_landcover(force=False)
    ml = train_or_refresh_ml_model()
    intelligence = process_all_event_intelligence()
    risk = process_all_event_risk()

    result = {
        "thermal_events": saved,
        "industrial_context": context,
        "land_cover": land_cover,
        "ml_anomaly": ml,
        "event_intelligence": intelligence,
        "risk_events": len(risk),
    }

    logger.info("Derived intelligence refresh completed: %s", result)
    return result


async def run_pipeline(*, initial: bool = False) -> None:
    """Run FIRMS ingestion followed by the derived intelligence pipeline."""

    if _pipeline_lock.locked():
        logger.info("Pipeline already running; skipping overlapping run")
        return

    async with _pipeline_lock:
        try:
            await asyncio.to_thread(ensure_runtime_schema)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Runtime schema repair failed")

        try:
            days = 7 if initial else 1
            logger.info(
                "Starting %s NASA FIRMS ingestion (%s day window)",
                "initial" if initial else "scheduled",
                days,
            )

            ingestion_result = await asyncio.to_thread(
                ingest_firms_events,
                days=days,
            )
            logger.info("FIRMS ingestion completed: %s", ingestion_result)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep the API alive. The derived refresh below still rebuilds
            # intelligence from whatever data is already in PostgreSQL.
            logger.exception("NASA FIRMS ingestion failed; refreshing existing data")

        try:
            intelligence_result = await asyncio.to_thread(
                refresh_derived_intelligence,
            )
            logger.info(
                "Intelligence refresh completed: %s",
                intelligence_result,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("ThermoIntel derived intelligence refresh failed")


# ============================================================
# FIRMS AUTO INGESTION
# ============================================================

async def firms_ingestion_loop() -> None:
    """Refresh the latest FIRMS data every 60 seconds."""

    while True:
        try:
            await asyncio.sleep(FIRMS_INGEST_INTERVAL)
            await run_pipeline(initial=False)
        except asyncio.CancelledError:
            logger.info("NASA FIRMS ingestion loop stopped")
            raise
        except Exception:
            # Defensive guard: the loop itself should always survive.
            logger.exception("Unexpected error in FIRMS ingestion loop")


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the API immediately and run data work in the background."""

    logger.info("========================================")
    logger.info("THERMOINTEL BACKEND STARTING")
    logger.info("========================================")

    # Start the recurring task first.  It does not perform work until after
    # the configured interval, so the API remains immediately available.
    ingestion_task = asyncio.create_task(
        firms_ingestion_loop(),
        name="thermointel-firms-ingestion",
    )

    # Run the first 7-day load in the background.  IMPORTANT: do not await it
    # here.  Awaiting it would make Uvicorn wait for NASA/database processing
    # before exposing /health and the API routes.
    initial_task = asyncio.create_task(
        run_pipeline(initial=True),
        name="thermointel-initial-pipeline",
    )

    logger.info("FastAPI API is ready")
    logger.info(
        "NASA FIRMS automatic ingestion interval: %s seconds",
        FIRMS_INGEST_INTERVAL,
    )

    try:
        yield
    finally:
        logger.info("Stopping ThermoIntel background tasks...")

        for task in (initial_task, ingestion_task):
            if not task.done():
                task.cancel()

        results = await asyncio.gather(
            initial_task,
            ingestion_task,
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception) and not isinstance(
                result, asyncio.CancelledError
            ):
                logger.error("Background task stopped with error: %r", result)

        logger.info("ThermoIntel backend stopped")


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="ThermoIntel API",
    version="0.1.0",
    description="AI-powered industrial thermal intelligence platform",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH / SYSTEM
# ============================================================

@app.get("/", tags=["System"])
def root() -> dict[str, str]:
    """Simple root endpoint for a quick backend availability check."""

    return {
        "service": "ThermoIntel API",
        "status": "ok",
    }


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Health endpoint used by Docker and manual checks.

    Database connectivity is checked so a green backend cannot hide a broken
    PostGIS connection. Empty datasets are valid during the first ingestion.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            row = connection.execute(text("""
                SELECT to_regclass('raw.firms_events') AS firms_events,
                       to_regclass('processed.thermal_events') AS thermal_events,
                       to_regclass('raw.industrial_facilities') AS facilities,
                       to_regclass('processed.event_intelligence') AS intelligence,
                       to_regclass('processed.event_risk_scores') AS risk
            """)).mappings().one()
        if any(row[key] is None for key in row):
            return {"status": "ok", "service": "ThermoIntel API", "database": "ok", "schema": "initializing"}
        return {"status": "ok", "service": "ThermoIntel API", "database": "ok", "schema": "ok"}
    except Exception as exc:
        logger.exception("Health database check failed")
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database is not ready") from exc


@app.get("/api/v1/system/status", tags=["System"])
def system_status() -> dict[str, object]:
    """Return a deployment-safe snapshot of database and pipeline data state."""
    try:
        with engine.connect() as connection:
            tables = connection.execute(text("""
                SELECT to_regclass('raw.firms_events') AS firms_events,
                       to_regclass('processed.thermal_events') AS thermal_events,
                       to_regclass('raw.industrial_facilities') AS facilities,
                       to_regclass('processed.event_intelligence') AS intelligence,
                       to_regclass('processed.event_risk_scores') AS risk
            """)).mappings().one()
            counts = connection.execute(text("""
                SELECT
                  (SELECT COUNT(*) FROM raw.firms_events) AS firms_events,
                  (SELECT COUNT(*) FROM processed.thermal_events) AS thermal_events,
                  (SELECT COUNT(*) FROM raw.industrial_facilities) AS facilities,
                  (SELECT COUNT(*) FROM processed.event_intelligence) AS intelligence,
                  (SELECT COUNT(*) FROM processed.event_risk_scores) AS risk,
                  (SELECT COUNT(*) FROM processed.event_ml_scores WHERE predicted_class IS NOT NULL) AS ml_scored_events
            """)).mappings().one()
            ml_registry = connection.execute(text("""
                SELECT model_name, model_version, trained_on_events, source_max_updated_at, updated_at
                FROM processed.ml_model_registry
                WHERE model_name = 'THERMOINTEL_XGBOOST_SOURCE_CLASSIFIER'
            """)).mappings().first()
        return {
            "status": "ok",
            "tables": dict(tables),
            "counts": {k: int(v or 0) for k, v in counts.items()},
            "xgboost": dict(ml_registry) if ml_registry else {"status": "waiting_for_training"},
        }
    except Exception as exc:
        logger.exception("System status check failed")
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ThermoIntel database schema is not ready") from exc


@app.post("/api/v1/system/reprocess", tags=["System"])
def reprocess_now() -> dict[str, object]:
    """Rebuild all derived thermal, context, intelligence and risk tables."""
    try:
        ensure_runtime_schema()
        result = refresh_derived_intelligence()
        return {"status": "ok", "result": result}
    except Exception as exc:
        logger.exception("Manual reprocess failed")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="ThermoIntel reprocessing failed") from exc


# ============================================================
# ROUTERS
# ============================================================

# Keep all existing frontend-facing API routers.
app.include_router(firms_router)
app.include_router(events_router)
app.include_router(facilities_router)
app.include_router(dashboard_router)
app.include_router(risk_router)
app.include_router(locations_router)

# The newer intelligence router contains /summary, /events, /high-risk,
# and /events/{event_id}.  Register it before the legacy /{event_id} router
# so paths such as /summary and /events are never captured by the generic
# legacy parameter route.
app.include_router(intelligence_router)
app.include_router(legacy_intelligence_router)
