import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

MAP_KEY = os.getenv("FIRMS_MAP_KEY")


url = (
    "https://firms.modaps.eosdis.nasa.gov/"
    f"api/data_availability/csv/"
    f"{MAP_KEY}/ALL"
)


df = pd.read_csv(url)

print("\n========================================")
print("FIRMS DATA AVAILABILITY")
print("========================================")

print(df.to_string(index=False))