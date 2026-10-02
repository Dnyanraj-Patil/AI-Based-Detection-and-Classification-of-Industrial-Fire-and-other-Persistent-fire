import os
import csv
from io import StringIO
from datetime import datetime

import requests
from sqlalchemy import text

from app.db.database import engine


# ============================================================
# CONFIGURATION
# ============================================================

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY")

# India + surrounding South Asia
FIRMS_AREA = "68,6,97.5,35.7"

# Primary near-real-time satellite source
FIRMS_SOURCES = [
    "VIIRS_NOAA21_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_SNPP_NRT",
]


# ============================================================
# FETCH NASA FIRMS DATA
# ============================================================

def fetch_firms_data(days: int = 7):
    """Fetch the latest 7 days of FIRMS data for India.

    NASA FIRMS Area API accepts a maximum DAY_RANGE of 5, so a 7-day
    request must be split into a 5-day current window plus a 2-day
    older window. We query the three global VIIRS NRT sensors and
    combine their CSV payloads.
    """
    if not FIRMS_MAP_KEY:
        raise RuntimeError("FIRMS_MAP_KEY environment variable is not configured.")

    days = int(days)
    if days < 1 or days > 7:
        raise ValueError("FIRMS days must be between 1 and 7.")

    # The FIRMS API maximum DAY_RANGE is 5.
    if days <= 5:
        requests_to_make = [(days, None)]
    else:
        requests_to_make = [(5, None), (days - 5, 5)]

    payloads = []

    for source in FIRMS_SOURCES:
        for day_range, date_offset in requests_to_make:
            url = (
                "https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
                f"{FIRMS_MAP_KEY}/{source}/{FIRMS_AREA}/{day_range}"
            )

            if date_offset is not None:
                from datetime import timedelta
                query_date = datetime.utcnow().date() - timedelta(days=date_offset)
                url += f"/{query_date.isoformat()}"

            last_error = None
            for attempt in range(1, 4):
                try:
                    response = requests.get(
                        url,
                        timeout=90,
                        headers={"User-Agent": "ThermoIntel/1.0 SIH thermal-intelligence"},
                    )
                    response.raise_for_status()
                    payloads.append(response.text)
                    break
                except requests.RequestException as exc:
                    last_error = exc
                    print(f"[FIRMS] {source} fetch attempt {attempt}/3 failed: {exc}")
                    if attempt < 3:
                        import time
                        time.sleep(5)
            else:
                raise RuntimeError(
                    f"NASA FIRMS request failed for {source} after 3 attempts: {last_error}"
                )

    # Merge CSV payloads while preserving one header.
    if not payloads:
        return ""

    lines = []
    header = None
    for payload in payloads:
        payload_lines = payload.splitlines()
        if not payload_lines:
            continue
        if header is None:
            header = payload_lines[0]
            lines.append(header)
        elif payload_lines[0] != header:
            # FIRMS products use the same schema; ignore unexpected headers.
            continue
        lines.extend(payload_lines[1:])

    return "\n".join(lines) + ("\n" if lines else "")


# ============================================================
# CSV PARSER
# ============================================================

def parse_csv(csv_text):
    """
    Parse NASA FIRMS CSV safely.

    NASA FIRMS occasionally contains whitespace around headers,
    so headers are normalized before processing.
    """

    if not csv_text or not csv_text.strip():
        return []

    reader = csv.DictReader(
        StringIO(csv_text)
    )

    records = []

    for row in reader:

        if not row:
            continue

        cleaned_row = {}

        for key, value in row.items():

            if key is None:
                continue

            clean_key = str(key).strip()

            if isinstance(value, str):
                value = value.strip()

            cleaned_row[clean_key] = value

        records.append(cleaned_row)

    return records


# ============================================================
# FLOAT PARSER
# ============================================================

def parse_float(value):
    """
    Safely convert a value to float.
    """

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        number = float(value)

        if number != number:
            return None

        return number

    except (TypeError, ValueError):
        return None


# ============================================================
# ACQUISITION DATE/TIME PARSER
# ============================================================

def parse_acquisition(record):
    """
    Parse NASA FIRMS acquisition date and time.

    Normal FIRMS format:

        acq_date = YYYY-MM-DD
        acq_time = HHMM

    This parser also tolerates:

        HHMMSS
        HH:MM
        HH:MM:SS
        numeric HHMM values
    """

    acq_date = str(
        record.get("acq_date", "")
    ).strip()

    acq_time = str(
        record.get("acq_time", "")
    ).strip()

    if not acq_date or not acq_time:
        return None, None, None

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    acquisition_date = None

    date_formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
    ]

    for date_format in date_formats:

        try:

            acquisition_date = datetime.strptime(
                acq_date,
                date_format,
            ).date()

            break

        except ValueError:
            continue

    if acquisition_date is None:
        return None, None, None

    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    # Remove whitespace
    acq_time = acq_time.strip()

    # Handle Excel/CSV-style numeric values such as:
    # 913 -> 0913
    #
    # But don't blindly convert decimal timestamps.
    if "." in acq_time:

        try:
            numeric_time = float(acq_time)

            if numeric_time.is_integer():
                acq_time = str(
                    int(numeric_time)
                )

        except ValueError:
            pass

    # Remove separators
    normalized_time = (
        acq_time
        .replace(":", "")
        .replace(" ", "")
    )

    # FIRMS commonly gives HHMM.
    # Some feeds may provide HHMMSS.
    if normalized_time.isdigit():

        if len(normalized_time) <= 4:
            normalized_time = normalized_time.zfill(4)

            time_formats = [
                "%H%M",
            ]

        elif len(normalized_time) == 6:

            time_formats = [
                "%H%M%S",
            ]

        else:
            time_formats = [
                "%H%M",
                "%H%M%S",
            ]

    else:

        time_formats = [
            "%H%M",
            "%H:%M",
            "%H:%M:%S",
            "%H%M%S",
        ]

    acquisition_time = None

    for time_format in time_formats:

        try:

            acquisition_time = datetime.strptime(
                normalized_time,
                time_format,
            ).time()

            break

        except ValueError:
            continue

    if acquisition_time is None:
        return None, None, None

    # --------------------------------------------------------
    # DATETIME
    # --------------------------------------------------------

    acquisition_datetime = datetime.combine(
        acquisition_date,
        acquisition_time,
    )

    return (
        acquisition_date,
        acquisition_time,
        acquisition_datetime,
    )


# ============================================================
# DATABASE INSERT
# ============================================================

INSERT_QUERY = text(
    """
    INSERT INTO raw.firms_events (
        latitude,
        longitude,
        geom,

        acquisition_date,
        acquisition_time,
        acquisition_datetime,

        satellite,
        instrument,

        bright_ti4,
        bright_ti5,
        frp,

        confidence,
        daynight,
        version,
        source
    )

    SELECT
        CAST(:latitude AS DOUBLE PRECISION),

        CAST(:longitude AS DOUBLE PRECISION),

        ST_SetSRID(
            ST_MakePoint(
                CAST(:longitude AS DOUBLE PRECISION),
                CAST(:latitude AS DOUBLE PRECISION)
            ),
            4326
        ),

        CAST(:acquisition_date AS DATE),

        CAST(:acquisition_time AS TIME),

        CAST(:acquisition_datetime AS TIMESTAMP),

        CAST(:satellite AS VARCHAR),

        CAST(:instrument AS VARCHAR),

        CAST(:bright_ti4 AS DOUBLE PRECISION),

        CAST(:bright_ti5 AS DOUBLE PRECISION),

        CAST(:frp AS DOUBLE PRECISION),

        CAST(:confidence AS VARCHAR),

        CAST(:daynight AS VARCHAR),

        CAST(:version AS VARCHAR),

        CAST(:source AS VARCHAR)

    WHERE NOT EXISTS (
        SELECT 1
        FROM raw.firms_events

        WHERE
            latitude =
                CAST(:latitude AS DOUBLE PRECISION)

            AND longitude =
                CAST(:longitude AS DOUBLE PRECISION)

            AND acquisition_datetime =
                CAST(:acquisition_datetime AS TIMESTAMP)

            AND satellite =
                CAST(:satellite AS VARCHAR)

            AND instrument =
                CAST(:instrument AS VARCHAR)
    )
    """
)


# ============================================================
# INGEST FIRMS EVENTS
# ============================================================

def ingest_firms_events(days: int = 7):
    """
    Fetch NASA FIRMS data and insert only new events.

    Safe to run repeatedly.

    Duplicate detection uses:

        latitude
        longitude
        acquisition_datetime
        satellite
        instrument
    """

    print(
        "\n[FIRMS] Starting ingestion..."
    )

    # --------------------------------------------------------
    # FETCH
    # --------------------------------------------------------

    try:

        csv_text = fetch_firms_data(days=days)

    except Exception as exc:

        print(
            f"[FIRMS] Fetch failed: {exc}"
        )

        return {
            "received": 0,
            "inserted": 0,
            "skipped": 0,
            "error": str(exc),
        }

    # --------------------------------------------------------
    # PARSE
    # --------------------------------------------------------

    records = parse_csv(
        csv_text
    )

    print(
        f"[FIRMS] Received {len(records)} records."
    )

    if not records:

        return {
            "received": 0,
            "inserted": 0,
            "skipped": 0,
        }

    # --------------------------------------------------------
    # DEBUG FIRST RECORD
    # --------------------------------------------------------

    print(
        "[FIRMS] Columns:"
    )

    print(
        list(records[0].keys())
    )

    print(
        "[FIRMS] First record:"
    )

    print(
        records[0]
    )

    # --------------------------------------------------------
    # COUNTERS
    # --------------------------------------------------------

    inserted = 0
    skipped = 0

    invalid_coordinates = 0
    invalid_acquisition = 0
    duplicates = 0
    database_errors = 0

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    with engine.begin() as connection:

        for index, record in enumerate(records):

            # =================================================
            # COORDINATES
            # =================================================

            latitude = parse_float(
                record.get("latitude")
            )

            longitude = parse_float(
                record.get("longitude")
            )

            if (
                latitude is None
                or longitude is None
            ):

                invalid_coordinates += 1
                skipped += 1

                print(
                    "[FIRMS] Skipping record "
                    f"{index}: invalid coordinates"
                )

                continue

            # =================================================
            # ACQUISITION
            # =================================================

            (
                acquisition_date,
                acquisition_time,
                acquisition_datetime,
            ) = parse_acquisition(
                record
            )

            if (
                acquisition_date is None
                or acquisition_time is None
                or acquisition_datetime is None
            ):

                invalid_acquisition += 1
                skipped += 1

                print(
                    "[FIRMS] Skipping record "
                    f"{index}: invalid acquisition "
                    f"date/time"
                )

                continue

            # =================================================
            # NUMERIC VALUES
            # =================================================

            bright_ti4 = parse_float(
                record.get("bright_ti4")
            )

            bright_ti5 = parse_float(
                record.get("bright_ti5")
            )

            frp = parse_float(
                record.get("frp")
            )

            # =================================================
            # STRING VALUES
            # =================================================

            satellite = (
                str(
                    record.get(
                        "satellite",
                        ""
                    )
                ).strip()
                or None
            )

            instrument = (
                str(
                    record.get(
                        "instrument",
                        ""
                    )
                ).strip()
                or None
            )

            confidence = (
                str(
                    record.get(
                        "confidence",
                        ""
                    )
                ).strip()
                or None
            )

            daynight = (
                str(
                    record.get(
                        "daynight",
                        ""
                    )
                ).strip()
                or None
            )

            version = (
                str(
                    record.get(
                        "version",
                        ""
                    )
                ).strip()
                or None
            )

            # =================================================
            # INSERT
            # =================================================

            try:

                result = connection.execute(
                    INSERT_QUERY,
                    {
                        "latitude":
                            latitude,

                        "longitude":
                            longitude,

                        "acquisition_date":
                            acquisition_date,

                        "acquisition_time":
                            acquisition_time,

                        "acquisition_datetime":
                            acquisition_datetime,

                        "satellite":
                            satellite,

                        "instrument":
                            instrument,

                        "bright_ti4":
                            bright_ti4,

                        "bright_ti5":
                            bright_ti5,

                        "frp":
                            frp,

                        "confidence":
                            confidence,

                        "daynight":
                            daynight,

                        "version":
                            version,

                        "source":
                            "NASA_FIRMS",
                    },
                )

                if result.rowcount:

                    inserted += result.rowcount

                else:

                    duplicates += 1
                    skipped += 1

            except Exception as exc:

                database_errors += 1
                skipped += 1

                print(
                    "[FIRMS] Database error on "
                    f"record {index}: {exc}"
                )

    # ========================================================
    # RESULT
    # ========================================================

    result = {
        "received": len(records),
        "inserted": inserted,
        "skipped": skipped,

        "duplicates": duplicates,

        "invalid_coordinates":
            invalid_coordinates,

        "invalid_acquisition":
            invalid_acquisition,

        "database_errors":
            database_errors,
    }

    print(
        "\n[FIRMS] Ingestion summary"
    )

    print(
        f"[FIRMS] Received: "
        f"{result['received']}"
    )

    print(
        f"[FIRMS] Inserted: "
        f"{result['inserted']}"
    )

    print(
        f"[FIRMS] Duplicates: "
        f"{result['duplicates']}"
    )

    print(
        f"[FIRMS] Invalid coordinates: "
        f"{result['invalid_coordinates']}"
    )

    print(
        f"[FIRMS] Invalid acquisition: "
        f"{result['invalid_acquisition']}"
    )

    print(
        f"[FIRMS] Database errors: "
        f"{result['database_errors']}"
    )

    print(
        f"[FIRMS] Skipped: "
        f"{result['skipped']}"
    )

    print(
        "========================================"
    )

    return result