# ThermoIntel Source Classification Methodology

ThermoIntel now uses a hybrid XGBoost + evidence-guardrail architecture.

## 1. Inputs

- NASA FIRMS thermal detections: FRP, brightness temperature, timing and
  persistence.
- PostGIS/OSM industrial context: nearest facility, facility density,
  industrial-area membership and facility type.
- ESA WorldCover land-cover class/confidence.
- Optional public NASA/ORNL VIIRS Nightfire flare-site catalog.
- Optional human-reviewed labels.

## 2. XGBoost classifier

A multiclass XGBoost model consumes the structured feature vector and outputs
probabilities for:

1. INDUSTRIAL FIRE
2. GAS FLARE / INDUSTRIAL THERMAL SOURCE
3. FOREST / VEGETATION FIRE
4. AGRICULTURAL BURNING
5. PERSISTENT THERMAL SOURCE
6. OTHER THERMAL SOURCE

The model uses weak supervision by default because a complete verified
India-wide fire-cause dataset covering all six classes is not available in the
project. Human-reviewed labels override bootstrap labels.

## 3. Guardrails

The model cannot independently turn a thermal signal into a specialised cause.
Gas-flare predictions require nearby hydrocarbon/flare context, and industrial
fire predictions require meaningful industrial proximity. When context is
incompatible, the existing explainable evidence classifier is retained.

## 4. Evaluation

The training job records accuracy, balanced accuracy and macro F1 on a coarse
geographic holdout where possible. When bootstrap labels are used, these
metrics measure agreement with the bootstrap labeling policy, not verified
physical-cause accuracy.

## 5. Why XGBoost

The ThermoIntel feature space is tabular rather than raw imagery. XGBoost is
well suited to nonlinear interactions among thermal, temporal, spatial and
land-cover features while remaining lightweight enough for CPU deployment.

NASA FIRMS itself cautions that satellite active-fire/thermal anomalies may
represent fire, agriculture, hot smoke or other sources. ThermoIntel therefore
presents the output as evidence-based source screening rather than a confirmed
ground-truth cause.
