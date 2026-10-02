"""Download public datasets used by the ThermoIntel XGBoost pipeline.

The FIRMS sample is public; the ORNL/Earthdata flare bundle may require an Earthdata login:
- NASA FIRMS academy VIIRS sample CSV
- NASA/ORNL Global Gas Flare Survey 2012-2019

The FIRMS operational archive itself requires Earthdata/MAP_KEY access; this
script intentionally does not hard-code or ask for credentials.
"""
from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path

from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "external"
FLARE_DIR = DATA / "gas_flare_survey"
FIRMS_DIR = DATA / "firms_sample"
FLARE_URL = "https://data.ornldaac.earthdata.nasa.gov/protected/bundle/Methane_Flaring_Sites_VIIRS_1874.zip"
FIRMS_SAMPLE_URL = "https://firms.modaps.eosdis.nasa.gov/content/notebooks/sample_viirs_snpp_071223.csv"


def download(url: str, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    request = Request(url, headers={"User-Agent": "ThermoIntel/1.0"})
    try:
        response = urlopen(request, timeout=120)
    except Exception as exc:
        raise RuntimeError(
            f"Could not download {url}. It may require an Earthdata login or internet access."
        ) from exc
    with response:
        with destination.open("wb") as f:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)


def main():
    FLARE_DIR.mkdir(parents=True, exist_ok=True)
    FIRMS_DIR.mkdir(parents=True, exist_ok=True)

    flare_zip = DATA / "Methane_Flaring_Sites_VIIRS_1874.zip"
    try:
        download(FLARE_URL, flare_zip)
        with zipfile.ZipFile(flare_zip) as z:
            z.extractall(FLARE_DIR)
    except RuntimeError as exc:
        print(f"WARNING: optional ORNL/NASA flare survey was not downloaded: {exc}")
        print("The XGBoost pipeline will continue using FIRMS + OSM + land-cover features.")

    sample_path = FIRMS_DIR / "sample_viirs_snpp_071223.csv"
    try:
        download(FIRMS_SAMPLE_URL, sample_path)
    except RuntimeError as exc:
        print(f"WARNING: FIRMS sample was not downloaded: {exc}")
        print("Operational FIRMS ingestion still uses FIRMS_MAP_KEY from .env.")

    print("\nDataset setup complete. Files present:")
    print(f"  Gas flare survey: {FLARE_DIR} ({'available' if any(FLARE_DIR.rglob('*')) else 'not installed'})")
    print(f"  FIRMS sample:     {sample_path} ({'available' if sample_path.exists() else 'not installed'})")


if __name__ == "__main__":
    main()
