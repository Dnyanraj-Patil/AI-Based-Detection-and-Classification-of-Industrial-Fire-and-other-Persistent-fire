"""Run the complete post-ingestion intelligence pipeline.

Order:
1. industrial spatial context
2. event intelligence classification
3. fused risk scoring
"""

from app.services.industrial_context_service import (
    process_all_event_industrial_context,
)
from app.services.event_intelligence_service import (
    process_all_event_intelligence,
)
from app.services.event_risk_service import (
    process_all_event_risk,
)


def main():
    print("\n=== ThermoIntel Intelligence Pipeline ===")

    context_count = process_all_event_industrial_context()
    print(f"[1/3] Industrial context: {context_count} events")

    intelligence = process_all_event_intelligence()
    print(f"[2/3] Event intelligence: {intelligence} events")

    risk = process_all_event_risk()
    print(f"[3/3] Risk scoring: {len(risk)} events")

    print("=== Pipeline complete ===\n")


if __name__ == "__main__":
    main()
