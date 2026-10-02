# ThermoIntel XGBoost Model Card

## Model

**Name:** `THERMOINTEL_XGBOOST_SOURCE_CLASSIFIER`  
**Version:** `1.0`  
**Framework:** XGBoost 3.1.3  
**Task:** multiclass tabular source classification

### Classes

- INDUSTRIAL FIRE
- GAS FLARE / INDUSTRIAL THERMAL SOURCE
- FOREST / VEGETATION FIRE
- AGRICULTURAL BURNING
- PERSISTENT THERMAL SOURCE
- OTHER THERMAL SOURCE

## Features

The classifier uses:

- FRP and average FRP
- brightness temperature
- detection count and observation duration
- nearest industrial-facility distance and facility density
- industrial-area membership
- facility-type keyword signals
- WorldCover land-cover class and confidence
- temporal season/hour features
- event latitude/longitude
- FRP per detection

## Training labels

The pipeline intentionally supports three label sources:

1. **Human-reviewed labels** in `data/ml_labels.csv` (highest priority).
2. **NASA/ORNL VIIRS Nightfire Global Gas Flare Survey** for events within
   approximately 2 km of a documented flare site, when the public dataset has
   been downloaded.
3. **Weak evidence bootstrap** generated from ThermoIntel's existing
   explainable context-first classifier.

This makes the system deployable without inventing a non-existent universal
fire-cause ground-truth dataset. It also means default model metrics are
*not* ground-truth accuracy.

## Evaluation

The training pipeline uses a coarse geographic holdout where possible, rather
than only a random split. It reports:

- holdout accuracy
- balanced accuracy
- macro F1

These are diagnostic measurements against the available training labels.
When most labels are weak bootstrap labels, high scores mainly show how well
XGBoost reproduces the bootstrap labeling policy; they do not establish
physical fire-cause accuracy.

## Context guardrails

XGBoost is the primary ML classifier, but ThermoIntel keeps context guardrails:

- gas-flare predictions require a nearby hydrocarbon/flare context;
- industrial-fire predictions require meaningful industrial proximity;
- unsupported specialized classifications can fall back to the evidence
  classifier.

This prevents a tabular model from turning a high-temperature satellite
pixel into an unsupported causal claim.

## Dataset notes

NASA FIRMS explicitly warns that satellite active-fire/thermal-anomaly
detections may correspond to fire, agriculture, hot smoke or other sources.
Operational FIRMS archive downloads require appropriate NASA access/MAP_KEY.
The bundled downloader uses the public FIRMS sample and public NASA/ORNL flare
survey as reproducible external inputs.

## Model artifact

After the first successful pipeline training:

- `backend/models/thermointel_xgboost_classifier.json`
- `backend/models/thermointel_xgboost_metrics.json`

are created automatically.
