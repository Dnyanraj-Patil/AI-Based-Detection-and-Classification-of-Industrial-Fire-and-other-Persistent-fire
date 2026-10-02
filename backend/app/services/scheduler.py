import asyncio

from app.services.firms_ingestion import ingest_firms_events


# ============================================================
# FIRMS AUTO INGESTION
# ============================================================

async def firms_ingestion_loop():
    """
    Automatically fetch NASA FIRMS data every 60 seconds.

    Runs once immediately when the backend starts,
    then repeats every 60 seconds.
    """

    while True:

        try:
            print("[FIRMS] Starting automatic ingestion...")

            result = ingest_firms_events()

            print(
                "[FIRMS] Automatic ingestion completed:",
                result,
            )

        except Exception as exc:
            print(
                "[FIRMS] Automatic ingestion error:",
                repr(exc),
            )

        # Wait 60 seconds before the next ingestion
        await asyncio.sleep(60)


def start_firms_scheduler():
    """
    Start the FIRMS background ingestion task.
    """

    return asyncio.create_task(
        firms_ingestion_loop()
    )