CREATE TABLE IF NOT EXISTS raw.firms_events (
    id BIGSERIAL PRIMARY KEY,

    -- Geographic location
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    -- PostGIS geographic point
    geom GEOMETRY(Point, 4326) NOT NULL,

    -- Satellite acquisition time
    acquisition_date DATE NOT NULL,
    acquisition_time TIME NOT NULL,
    acquisition_datetime TIMESTAMPTZ NOT NULL,

    -- Satellite information
    satellite VARCHAR(20) NOT NULL,
    instrument VARCHAR(30) NOT NULL,

    -- VIIRS measurements
    bright_ti4 DOUBLE PRECISION,
    bright_ti5 DOUBLE PRECISION,

    -- Pixel dimensions
    scan DOUBLE PRECISION,
    track DOUBLE PRECISION,

    -- Detection information
    confidence VARCHAR(10),
    frp DOUBLE PRECISION,
    daynight CHAR(1),

    -- FIRMS processing information
    version VARCHAR(50),

    -- Our system metadata
    source VARCHAR(100) NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate satellite observations
    CONSTRAINT uq_firms_event
    UNIQUE (
        latitude,
        longitude,
        acquisition_datetime,
        satellite,
        instrument,
        version
    )
);


-- Spatial index
CREATE INDEX IF NOT EXISTS idx_firms_events_geom
ON raw.firms_events
USING GIST (geom);


-- Time index
CREATE INDEX IF NOT EXISTS idx_firms_events_datetime
ON raw.firms_events(acquisition_datetime);


-- FRP index
CREATE INDEX IF NOT EXISTS idx_firms_events_frp
ON raw.firms_events(frp);


-- Satellite index
CREATE INDEX IF NOT EXISTS idx_firms_events_satellite
ON raw.firms_events(satellite);


-- Confidence index
CREATE INDEX IF NOT EXISTS idx_firms_events_confidence
ON raw.firms_events(confidence);