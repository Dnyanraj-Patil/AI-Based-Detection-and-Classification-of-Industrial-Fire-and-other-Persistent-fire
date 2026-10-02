from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import text

from app.db.database import engine


router = APIRouter(
    prefix="/api/v1/facilities",
    tags=["Industrial Facilities"],
)


@router.get("")
def get_facilities(
    limit: int | None = Query(
        default=None,
        ge=1,
        le=100000,
        description="Optional maximum number of facilities to return. Omit for all facilities.",
    ),
    offset: int = Query(default=0, ge=0, description="Number of facilities to skip"),
    search: str | None = Query(default=None, max_length=120),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=500),
):
    """
    Return industrial facilities currently stored
    in raw.industrial_facilities.

    This endpoint reads directly from PostgreSQL on
    every request. It does not cache facility data.

    NOTE:
    This endpoint does NOT ingest new facilities from OSM.
    It only returns facilities already present in the database.
    """

    if (latitude is None) != (longitude is None):
        raise HTTPException(status_code=400, detail="latitude and longitude must be provided together.")
    if (latitude is not None or longitude is not None) and radius_km is None:
        radius_km = 25.0

    filters = []
    params = {"offset": offset}
    if search:
        filters.append("(COALESCE(name,'') ILIKE :search OR COALESCE(facility_type,'') ILIKE :search OR COALESCE(industrial_type,'') ILIKE :search)")
        params["search"] = f"%{search.strip()}%"
    if latitude is not None:
        filters.append("ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(:longitude, :latitude),4326)::geography,:radius_meters)")
        params.update({"latitude": latitude, "longitude": longitude, "radius_meters": radius_km * 1000})
    where_clause = "WHERE " + " AND ".join(filters) if filters else ""
    limit_clause = "" if limit is None else "LIMIT :limit"
    if limit is not None:
        params["limit"] = limit

    count_query = text(f"SELECT COUNT(*) FROM raw.industrial_facilities {where_clause}")
    facilities_query = text(f"""
        SELECT id, osm_type, osm_id, name, facility_type, industrial_type, latitude, longitude, source
        FROM raw.industrial_facilities
        {where_clause}
        ORDER BY id
        {limit_clause}
        OFFSET :offset
    """)

    try:

        with engine.connect() as connection:

            # -------------------------------------------------
            # GET ACTUAL DATABASE TOTAL
            # -------------------------------------------------

            total_count = connection.execute(count_query, params).scalar_one()

            total_count = int(total_count or 0)

            # -------------------------------------------------
            # GET CURRENT FACILITIES
            # -------------------------------------------------

            rows = (
                connection.execute(facilities_query, params)
                .mappings()
                .all()
            )

        # =====================================================
        # SERIALIZE FACILITIES
        # =====================================================

        facilities = []

        for row in rows:

            facility = {
                "id": row["id"],

                "osm_type": row["osm_type"],

                "osm_id": row["osm_id"],

                "name": row["name"],

                "facility_type":
                    row["facility_type"],

                "industrial_type":
                    row["industrial_type"],

                "latitude":
                    float(row["latitude"])
                    if row["latitude"] is not None
                    else None,

                "longitude":
                    float(row["longitude"])
                    if row["longitude"] is not None
                    else None,

                "source":
                    row["source"],
            }

            facilities.append(facility)

        # =====================================================
        # PAGINATION INFORMATION
        # =====================================================

        returned_count = len(facilities)

        next_offset = offset + returned_count

        has_more = next_offset < total_count

        # =====================================================
        # RESPONSE
        # =====================================================

        return {
            "count": returned_count,

            "total_count": total_count,

            "limit": limit,

            "offset": offset,

            "has_more": has_more,

            "next_offset":
                next_offset
                if has_more
                else None,

            "facilities": facilities,
        }

    except Exception as exc:

        # Log the actual exception in the backend console
        print(
            "[Facilities] Database error:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to retrieve industrial "
                "facilities from the database."
            ),
        ) from exc