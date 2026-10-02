CREATE TABLE IF NOT EXISTS processed.thermal_events (
    id BIGSERIAL PRIMARY KEY,

    -- Event timing
    first_detected_at TIMESTAMPTZ NOT NULL,
    last_detected_at TIMESTAMPTZ NOT NULL,

    -- Detection statistics
    detection_count INTEGER NOT NULL DEFAULT 0,

    -- Thermal statistics
    max_frp DOUBLE PRECISION,
    average_frp DOUBLE PRECISION,

    max_bright_ti4 DOUBLE PRECISION,
    average_bright_ti4 DOUBLE PRECISION,

    -- Observation / centroid metadata
    observation_duration_minutes DOUBLE PRECISION NOT NULL DEFAULT 0,
    centroid_latitude DOUBLE PRECISION,
    centroid_longitude DOUBLE PRECISION,

    -- Deterministic event identity
    event_fingerprint VARCHAR(64) NOT NULL UNIQUE,

    -- Satellite information
    satellites TEXT[],

    -- Event geometry
    geom GEOMETRY(Point, 4326) NOT NULL,

    -- Event status
    status VARCHAR(30) NOT NULL DEFAULT 'active',

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE INDEX IF NOT EXISTS idx_thermal_events_geom
ON processed.thermal_events
USING GIST (geom);


CREATE INDEX IF NOT EXISTS idx_thermal_events_time
ON processed.thermal_events(
    first_detected_at,
    last_detected_at
);


CREATE INDEX IF NOT EXISTS idx_thermal_events_status
ON processed.thermal_events(status);