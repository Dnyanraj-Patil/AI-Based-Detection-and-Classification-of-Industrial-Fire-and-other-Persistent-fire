import requests
import pandas as pd

from shapely import wkt


# ============================================================
# OVERPASS CONFIGURATION
# ============================================================

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

REQUEST_TIMEOUT = 210


# ============================================================
# FETCH INDUSTRIAL FACILITIES
# ============================================================

def fetch_industrial_facilities(
    west: float,
    south: float,
    east: float,
    north: float,
) -> pd.DataFrame:
    """
    Retrieve industrial facilities from OpenStreetMap
    through Overpass.

    Searches for:

        landuse=industrial
        industrial=*
        man_made=works

    Geometry is preserved as WKT.

    Parameters
    ----------
    west : float
        Western longitude.

    south : float
        Southern latitude.

    east : float
        Eastern longitude.

    north : float
        Northern latitude.

    Returns
    -------
    pandas.DataFrame
        Normalized OSM industrial facility records.
    """

    # --------------------------------------------------------
    # Validate bounding box
    # --------------------------------------------------------

    if west >= east:
        raise ValueError(
            "west must be smaller than east."
        )

    if south >= north:
        raise ValueError(
            "south must be smaller than north."
        )

    if not (
        -180 <= west <= 180
        and -180 <= east <= 180
    ):
        raise ValueError(
            "Longitude values must be between -180 and 180."
        )

    if not (
        -90 <= south <= 90
        and -90 <= north <= 90
    ):
        raise ValueError(
            "Latitude values must be between -90 and 90."
        )

    # --------------------------------------------------------
    # Overpass query
    # --------------------------------------------------------

    query = f"""
    [out:json][timeout:180];

    (
        node["landuse"="industrial"](
            {south},{west},{north},{east}
        );

        way["landuse"="industrial"](
            {south},{west},{north},{east}
        );

        relation["landuse"="industrial"](
            {south},{west},{north},{east}
        );

        node["industrial"](
            {south},{west},{north},{east}
        );

        way["industrial"](
            {south},{west},{north},{east}
        );

        relation["industrial"](
            {south},{west},{north},{east}
        );

        node["man_made"="works"](
            {south},{west},{north},{east}
        );

        way["man_made"="works"](
            {south},{west},{north},{east}
        );

        relation["man_made"="works"](
            {south},{west},{north},{east}
        );

        node["building"="industrial"](
            {south},{west},{north},{east}
        );

        way["building"="industrial"](
            {south},{west},{north},{east}
        );

        relation["building"="industrial"](
            {south},{west},{north},{east}
        );

        node["power"="plant"](
            {south},{west},{north},{east}
        );

        way["power"="plant"](
            {south},{west},{north},{east}
        );

        relation["power"="plant"](
            {south},{west},{north},{east}
        );

        node["man_made"="wastewater_plant"](
            {south},{west},{north},{east}
        );

        way["man_made"="wastewater_plant"](
            {south},{west},{north},{east}
        );

        relation["man_made"="wastewater_plant"](
            {south},{west},{north},{east}
        );
    );

    out geom center tags;
    """

    # --------------------------------------------------------
    # Request
    # --------------------------------------------------------

    last_error = None

    for overpass_url in OVERPASS_URLS:
        try:
            response = requests.post(
                overpass_url,
                data=query,
                headers={
                    "User-Agent": (
                        "ThermoIntel/0.1 "
                        "industrial-intelligence-development"
                    )
                },
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            break
        except requests.RequestException as exc:
            last_error = exc
    else:
        raise RuntimeError(
            "Unable to retrieve industrial facilities from OpenStreetMap Overpass: "
            f"{last_error}"
        ) from last_error

    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    try:

        data = response.json()

    except ValueError as exc:

        raise RuntimeError(
            "Overpass returned an invalid JSON response."
        ) from exc

    records = []

    # ========================================================
    # PROCESS OSM ELEMENTS
    # ========================================================

    for element in data.get("elements", []):

        tags = element.get("tags", {})

        osm_type = element.get("type")
        osm_id = element.get("id")

        if osm_type is None or osm_id is None:
            continue

        geometry_wkt = None

        # ====================================================
        # NODE
        # ====================================================

        if osm_type == "node":

            latitude = element.get("lat")
            longitude = element.get("lon")

            if (
                latitude is not None
                and longitude is not None
            ):

                geometry_wkt = (
                    f"POINT({longitude} {latitude})"
                )

        # ====================================================
        # WAY
        # ====================================================

        elif osm_type == "way":

            geometry = element.get(
                "geometry",
                []
            )

            coordinates = []

            for point in geometry:

                longitude = point.get("lon")
                latitude = point.get("lat")

                if (
                    longitude is None
                    or latitude is None
                ):
                    continue

                coordinates.append(
                    (
                        longitude,
                        latitude,
                    )
                )

            if len(coordinates) >= 3:

                # ------------------------------------------------
                # Closed way → polygon
                # ------------------------------------------------

                if (
                    coordinates[0]
                    == coordinates[-1]
                ):

                    geometry_wkt = (
                        "POLYGON(("
                        + ", ".join(
                            f"{lon} {lat}"
                            for lon, lat
                            in coordinates
                        )
                        + "))"
                    )

                # ------------------------------------------------
                # Open way → linestring
                # ------------------------------------------------

                else:

                    geometry_wkt = (
                        "LINESTRING("
                        + ", ".join(
                            f"{lon} {lat}"
                            for lon, lat
                            in coordinates
                        )
                        + ")"
                    )

            elif len(coordinates) == 2:

                geometry_wkt = (
                    "LINESTRING("
                    + ", ".join(
                        f"{lon} {lat}"
                        for lon, lat
                        in coordinates
                    )
                    + ")"
                )

        # ====================================================
        # RELATION
        # ====================================================

        elif osm_type == "relation":

            center = element.get(
                "center",
                {}
            )

            latitude = center.get("lat")
            longitude = center.get("lon")

            if (
                latitude is not None
                and longitude is not None
            ):

                geometry_wkt = (
                    f"POINT({longitude} {latitude})"
                )

        # ====================================================
        # FALLBACK CENTER
        # ====================================================

        if geometry_wkt is None:

            center = element.get(
                "center",
                {}
            )

            latitude = center.get("lat")
            longitude = center.get("lon")

            if (
                latitude is not None
                and longitude is not None
            ):

                geometry_wkt = (
                    f"POINT({longitude} {latitude})"
                )

        # ----------------------------------------------------
        # Skip unusable geometry
        # ----------------------------------------------------

        if geometry_wkt is None:
            continue

        # ====================================================
        # VALIDATE GEOMETRY
        # ====================================================

        try:

            geometry = wkt.loads(
                geometry_wkt
            )

            if geometry.is_empty:
                continue

            representative_point = (
                geometry.representative_point()
            )

            latitude = (
                representative_point.y
            )

            longitude = (
                representative_point.x
            )

        except Exception:
            continue

        # ====================================================
        # SAVE RECORD
        # ====================================================

        records.append(
            {
                "osm_type":
                    osm_type,

                "osm_id":
                    osm_id,

                "name":
                    tags.get("name"),

                "landuse":
                    tags.get("landuse"),

                "industrial":
                    tags.get("industrial"),

                "man_made":
                    tags.get("man_made"),

                "building":
                    tags.get("building"),

                "power":
                    tags.get("power"),

                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "geometry_wkt":
                    geometry_wkt,
            }
        )

    # ========================================================
    # CREATE DATAFRAME
    # ========================================================

    columns = [
        "osm_type",
        "osm_id",
        "name",
        "landuse",
        "industrial",
        "man_made",
        "building",
        "power",
        "latitude",
        "longitude",
        "geometry_wkt",
    ]

    df = pd.DataFrame(
        records,
        columns=columns,
    )

    # --------------------------------------------------------
    # Remove duplicate OSM objects
    # --------------------------------------------------------

    if not df.empty:

        df = (
            df.drop_duplicates(
                subset=[
                    "osm_type",
                    "osm_id",
                ]
            )
            .reset_index(drop=True)
        )

    return df