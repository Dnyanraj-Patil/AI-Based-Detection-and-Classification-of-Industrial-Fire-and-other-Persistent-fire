# ThermoIntel V6 Change Log

## Stability and scale fixes
- Thermal Events API: server-side pagination, server-side search, total/day/night counts.
- Industrial Facilities API: server-side pagination and server-side search.
- Frontend never loads 47k+ facilities or the complete event table into React state.
- Only the visible page is rendered, preventing browser blanking/freezing.
- Added database indexes for event/facility pagination and lookup.

## Classification presentation
- Thermal Events prioritizes a valid classification from event risk/intelligence data.
- Legacy `THERMAL ANOMALY` values are never shown as a final source class.
- Thermal Events displays classification confidence, not FIRMS detection confidence.
- Risk API normalizes legacy classification values as well.

## Data sources
- NASA FIRMS for thermal detections.
- ESA WorldCover 2021 v200 for 10 m land-cover context.
- OpenStreetMap for industrial infrastructure context.

## Important scientific limitation
ThermoIntel is an explainable deterministic evidence-fusion classifier. It does not
claim that a satellite thermal detection alone proves the physical cause of a fire.
