# ThermoIntel Source Classification — Model Card

## Purpose

ThermoIntel classifies satellite-observed thermal events into source categories for geospatial screening and prioritisation:

- INDUSTRIAL FIRE
- GAS FLARE / INDUSTRIAL THERMAL SOURCE
- FOREST / VEGETATION FIRE
- AGRICULTURAL BURNING
- OTHER THERMAL SOURCE

## Inputs

1. NASA FIRMS thermal observations: FRP, brightness temperature, acquisition time, satellite and detection confidence.
2. Event persistence: observation duration and number of detections.
3. OSM industrial context: mapped facility proximity, density, facility type and industrial-area membership.
4. ESA WorldCover 2021 v200: 10 m land-cover class sampled around the event centroid.

## Decision logic

The primary ML classifier is XGBoost over structured FIRMS, temporal, industrial-context and land-cover features. It is bootstrapped from the deterministic multi-source evidence classifier and can consume human-reviewed labels and public VIIRS Nightfire flare-site labels. Industrial classes require infrastructure evidence; flare classification additionally requires a nearby hydrocarbon-related facility signal. Agricultural burning requires cropland evidence. Forest/vegetation classification requires a vegetation land-cover signal. If contextual evidence is insufficient, the deterministic guardrail can override an unsupported specialised prediction.

## Interpretation

`classification_confidence` is the normalized top-class evidence score after the class-evidence transformation. It is **not** a calibrated probability of fire cause and must not be presented as such.

The class probability vector is the XGBoost model's relative probability distribution across the six candidate classes; it is not a calibrated physical-cause probability unless independently calibrated and validated against verified labels.

## Important limitations

- FIRMS observations are satellite-derived detections and can represent fire, agriculture or other thermal sources. A detection is not ground truth for fire cause.
- WorldCover is a land-cover context layer, not a fire-cause label.
- OSM industrial coverage is incomplete and varies geographically.
- The system does not claim supervised-model accuracy because no verified ground-truth fire-cause training set is included.

## Version

`XGBOOST_WEAK_SUPERVISION_V1`

## Confidence semantics
`classification_confidence` is the normalized evidence-fusion confidence of the
winning source class (derived from the classifier's class score distribution).
It is distinct from the raw NASA FIRMS detection-confidence field. The UI must
never display a raw FIRMS confidence value as source-class confidence.
