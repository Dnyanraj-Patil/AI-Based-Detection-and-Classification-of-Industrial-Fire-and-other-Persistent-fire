from sqlalchemy import text

from app.db.database import engine


INSERT_FIRMS_SQL = text(
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
        scan,
        track,
        confidence,
        frp,
        daynight,
        version,
        source
    )
    VALUES (
        :latitude,
        :longitude,
        ST_SetSRID(
            ST_MakePoint(
                :longitude,
                :latitude
            ),
            4326
        ),
        :acquisition_date,
        :acquisition_time,
        :acquisition_datetime,
        :satellite,
        :instrument,
        :bright_ti4,
        :bright_ti5,
        :scan,
        :track,
        :confidence,
        :frp,
        :daynight,
        :version,
        :source
    )
    ON CONFLICT (
        latitude,
        longitude,
        acquisition_datetime,
        satellite,
        instrument,
        version
    )
    DO NOTHING
    """
)


def insert_firms_dataframe(df) -> int:
    """
    Insert normalized FIRMS records into PostGIS.

    Returns the number of records processed.
    """

    if df.empty:
        return 0

    records = []

    for _, row in df.iterrows():

        records.append(
            {
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "acquisition_date": row[
                    "acquisition_datetime"
                ].date(),
                "acquisition_time": row[
                    "acquisition_datetime"
                ].time(),
                "acquisition_datetime": row[
                    "acquisition_datetime"
                ].to_pydatetime(),
                "satellite": row["satellite"],
                "instrument": row["instrument"],
                "bright_ti4": row[
                    "brightness_temperature_i4"
                ],
                "bright_ti5": row[
                    "brightness_temperature_i5"
                ],
                "scan": row["scan"],
                "track": row["track"],
                "confidence": row["confidence"],
                "frp": row["frp"],
                "daynight": row["daynight"],
                "version": row["version"],
                "source": row["source"],
            }
        )

    with engine.begin() as connection:

        connection.execute(
            INSERT_FIRMS_SQL,
            records,
        )

    return len(records)