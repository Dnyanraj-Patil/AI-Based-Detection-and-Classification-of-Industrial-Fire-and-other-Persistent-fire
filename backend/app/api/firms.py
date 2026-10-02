from fastapi import APIRouter, HTTPException

from app.services.firms_ingestion import ingest_firms_events


router = APIRouter(
    prefix="/api/v1/firms",
    tags=["NASA FIRMS"],
)


@router.post("/ingest")
def ingest_firms():

    try:
        result = ingest_firms_events()

        return {
            "status": "success",
            **result,
        }

    except Exception as exc:

        print("NASA FIRMS INGESTION ERROR:")
        print(repr(exc))

        raise HTTPException(
            status_code=500,
            detail=f"NASA FIRMS ingestion failed: {str(exc)}",
        ) from exc