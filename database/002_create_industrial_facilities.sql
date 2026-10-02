CREATE TABLE IF NOT EXISTS raw.industrial_facilities (
    id BIGSERIAL PRIMARY KEY,

    -- OpenStreetMap identification
    osm_type VARCHAR(10) NOT NULL,
    osm_id BIGINT NOT NULL,

    -- Facility information
    name TEXT,
    facility_type VARCHAR(100),
    industrial_type VARCHAR(100),

    -- Geographic information
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,

    geom GEOMETRY(Geometry, 4326) NOT NULL,

    -- Source information
    source VARCHAR(50) NOT NULL DEFAULT 'OpenStreetMap',
    source_url TEXT,

    -- Metadata
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate OSM objects
    CONSTRAINT uq_osm_facility
    UNIQUE (
        osm_type,
        osm_id
    )
);


CREATE INDEX IF NOT EXISTS idx_industrial_facilities_geom
ON raw.industrial_facilities
USING GIST (geom);


CREATE INDEX IF NOT EXISTS idx_industrial_facilities_type
ON raw.industrial_facilities(facility_type);


CREATE INDEX IF NOT EXISTS idx_industrial_facilities_industrial_type
ON raw.industrial_facilities(industrial_type);


CREATE INDEX IF NOT EXISTS idx_industrial_facilities_osm
ON raw.industrial_facilities(osm_id);