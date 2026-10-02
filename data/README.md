# ThermoIntel ML datasets

The XGBoost classifier is designed to use three layers of training evidence:

1. `data/ml_labels.csv` — optional human-reviewed event labels. These take priority.
2. NASA/ORNL VIIRS Nightfire Global Gas Flare Survey — downloaded by
   `scripts/download_ml_datasets.py` and used as positive flare-site labels
   when a ThermoIntel event is within 2 km of a known site.
3. ThermoIntel's explainable multi-source evidence classifier — used as a
   weak-supervision bootstrap label for the remaining events.

The NASA FIRMS sample CSV is also downloaded for schema/regression checks. It
is not treated as fire-cause ground truth.

NASA FIRMS notes that active-fire/thermal-anomaly detections can represent
fire, agriculture, hot smoke or other sources, so the bundled bootstrap labels
must not be presented as verified ground truth.

Run from the project root:

```bat
python scripts\download_ml_datasets.py
```

Then rebuild/restart the backend. The normal pipeline retrains XGBoost when
the event population changes.

## Manual labels

Add rows such as:

```csv
event_id,label,reviewer,notes
123,INDUSTRIAL FIRE,reviewer1,Confirmed from satellite/inspection
```

Allowed labels are exactly the six labels used by the model.
