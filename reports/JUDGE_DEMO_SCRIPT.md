# Judge Demo — XGBoost Accuracy

## If judges ask: “What is the accuracy?”

Do not quote the XGBoost probability/confidence as accuracy.

Run:

```text
EVALUATE_XGBOOST.bat
```

Then show the generated metrics. The number to say is:

> “On our human-reviewed held-out test set, the XGBoost classifier achieved **[printed Accuracy]% accuracy**. We also report balanced accuracy and macro F1 because our classes are not guaranteed to be equally represented.”

Replace the bracketed value with the number printed by the evaluator. Do not pre-fill it.

## If judges ask: “How did you calculate it?”

> “We first collect thermal-event candidates from FIRMS and the ThermoIntel context pipeline. Human reviewers assign the actual source class. We keep those reviewed labels separate from the model confidence. XGBoost is then evaluated on reviewed events that are not used as ground-truth training examples. Accuracy is the number of correct classifications divided by the number of evaluated events.”

## If judges ask about confidence

> “The XGBoost confidence is the model's probability for its selected class. It is not the same thing as model accuracy. Accuracy is calculated separately against reviewed ground-truth labels.”

## If judges ask why the result is not 100%

> “Thermal satellite detections can have ambiguous causes and several classes can share similar thermal signatures. That is why we report multiple metrics and the confusion matrix instead of presenting a single confidence number as proof of accuracy.”
