CREATE TABLE IF NOT EXISTS processed.thermal_event_detections (
    event_id BIGINT NOT NULL,

    firms_event_id BIGINT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (
        event_id,
        firms_event_id
    ),

    CONSTRAINT fk_event
        FOREIGN KEY (event_id)
        REFERENCES processed.thermal_events(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_firms_event
        FOREIGN KEY (firms_event_id)
        REFERENCES raw.firms_events(id)
        ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS
idx_event_detection_firms
ON processed.thermal_event_detections(
    firms_event_id
);