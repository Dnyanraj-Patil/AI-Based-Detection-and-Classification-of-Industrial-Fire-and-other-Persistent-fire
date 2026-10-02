# ThermoIntel classification guide

ThermoIntel separates **satellite detection confidence** from **ThermoIntel source-class confidence**.

## 1. FIRMS detection confidence

NASA FIRMS/VIIRS supplies a categorical detection-confidence field:

- `L` = Low
- `N` = Nominal
- `H` = High

The UI displays these as **FIRMS Detection Confidence**. They are not percentages.

## 2. ThermoIntel source classification

The intelligence engine combines the evidence available in the application:

- FRP (Fire Radiative Power)
- VIIRS brightness temperature
- repeated detections and observation duration
- OSM/PostGIS industrial-facility proximity
- industrial facility name/type metadata
- agricultural/land-use hints when such evidence is actually present

Possible source classes are:

- **GAS FLARE / INDUSTRIAL THERMAL SOURCE**
- **INDUSTRIAL FIRE**
- **WILDFIRE / NATURAL VEGETATION FIRE**
- **AGRICULTURAL BURNING**
- **PERSISTENT THERMAL SOURCE**
- **OTHER THERMAL SOURCE**

The **classification confidence** is an evidence-strength score in the range 50%–95%. It is intentionally different from the FIRMS categorical confidence.

## 3. Important interpretation rule

A FIRMS thermal anomaly is not ground truth for the cause of a fire. ThermoIntel therefore presents classification as an **evidence-based screening result** and preserves source provenance.

Agricultural burning is only assigned when agricultural evidence is actually available; the system does not manufacture a farm-fire label from a generic hotspot.
