import os
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


# ---------------------------------------------------------
# Load project-level .env
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


# ---------------------------------------------------------
# FIRMS configuration
# ---------------------------------------------------------

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY")

FIRMS_BASE_URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
)


# ---------------------------------------------------------
# Fetch FIRMS data
# ---------------------------------------------------------

def fetch_firms_data(
    source: str,
    west: float,
    south: float,
    east: float,
    north: float,
    day_range: int = 1,
    date: str | None = None,
) -> pd.DataFrame:

    if not FIRMS_MAP_KEY:
        raise RuntimeError(
            "FIRMS_MAP_KEY is not configured in .env"
        )

    if not 1 <= day_range <= 5:
        raise ValueError(
            "FIRMS day_range must be between 1 and 5."
        )

    if west >= east:
        raise ValueError(
            "west must be smaller than east."
        )

    if south >= north:
        raise ValueError(
            "south must be smaller than north."
        )

    area = f"{west},{south},{east},{north}"

    url = (
        f"{FIRMS_BASE_URL}/"
        f"{FIRMS_MAP_KEY}/"
        f"{source}/"
        f"{area}/"
        f"{day_range}"
    )
    if date:
        url = f"{url}/{date}"

    response = requests.get(
        url,
        timeout=60,
    )

    response.raise_for_status()

    return pd.read_csv(
        StringIO(response.text)
    )