import unittest
from unittest.mock import patch
from app.services.source_classifier import classify_source, CLASSES


class SourceClassifierLogicTests(unittest.TestCase):
    def test_industrial_event(self):
        features = {
            "max_frp": 80, "max_bright_ti4": 345, "observation_duration_minutes": 90,
            "detection_count": 5, "facility_distance": 300, "facilities_within_1km": 6,
            "facilities_within_5km": 20, "inside_industrial": True,
            "facility_type": "Refinery", "industrial_type": "oil refinery",
            "land_cover_class": "BUILT_UP", "land_cover_confidence": 0.9,
            "land_cover_source": "ESA_WORLDCOVER_2021_V200",
        }
        with patch("app.services.source_classifier.get_event_features", return_value=features):
            result = classify_source(1)
        self.assertEqual(result["classification"], "INDUSTRIAL FIRE")
        self.assertIn(result["classification"], CLASSES)

    def test_forest_event(self):
        features = {
            "max_frp": 40, "max_bright_ti4": 335, "observation_duration_minutes": 100,
            "detection_count": 5, "facility_distance": 999999, "facilities_within_1km": 0,
            "facilities_within_5km": 0, "inside_industrial": False,
            "facility_type": "", "industrial_type": "",
            "land_cover_class": "FOREST", "land_cover_confidence": 0.9,
            "land_cover_source": "ESA_WORLDCOVER_2021_V200",
        }
        with patch("app.services.source_classifier.get_event_features", return_value=features):
            result = classify_source(1)
        self.assertEqual(result["classification"], "FOREST / VEGETATION FIRE")

    def test_agricultural_event(self):
        features = {
            "max_frp": 12, "max_bright_ti4": 320, "observation_duration_minutes": 40,
            "detection_count": 3, "facility_distance": 999999, "facilities_within_1km": 0,
            "facilities_within_5km": 0, "inside_industrial": False,
            "facility_type": "", "industrial_type": "",
            "land_cover_class": "AGRICULTURE", "land_cover_confidence": 0.9,
            "land_cover_source": "ESA_WORLDCOVER_2021_V200",
        }
        with patch("app.services.source_classifier.get_event_features", return_value=features):
            result = classify_source(1)
        self.assertEqual(result["classification"], "AGRICULTURAL BURNING")


if __name__ == "__main__":
    unittest.main()
