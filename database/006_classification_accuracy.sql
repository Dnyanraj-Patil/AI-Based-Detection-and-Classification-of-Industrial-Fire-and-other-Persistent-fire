-- ThermoIntel classification/display repair.
-- Safe for fresh installs and harmless on existing installations.

ALTER TABLE IF EXISTS processed.event_intelligence
    ADD COLUMN IF NOT EXISTS classification VARCHAR(100);

ALTER TABLE IF EXISTS processed.event_intelligence
    ADD COLUMN IF NOT EXISTS classification_confidence DOUBLE PRECISION NOT NULL DEFAULT 0;

ALTER TABLE IF EXISTS processed.event_intelligence
    ADD COLUMN IF NOT EXISTS class_probabilities JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Old placeholder labels are not source classifications. Force them to be
-- recalculated by the Python evidence-fusion classifier.
UPDATE processed.event_intelligence
SET classification = NULL,
    classification_confidence = 0,
    class_probabilities = '{}'::jsonb
WHERE UPPER(COALESCE(classification, '')) IN (
    'THERMAL ANOMALY',
    'OTHER THERMAL ANOMALY'
);
