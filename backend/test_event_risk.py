from app.services.event_risk_service import (
    process_event_risk,
)


print()
print("=" * 40)
print("THERMOINTEL EVENT RISK TEST")
print("=" * 40)


event_id = 1


result = process_event_risk(
    event_id
)


if result is None:

    print(
        f"No intelligence found for event {event_id}"
    )

else:

    print()
    print(
        f"Event ID: {result['event_id']}"
    )

    print(
        f"Thermal Score: "
        f"{result['thermal_score']:.4f}"
    )

    print(
        f"Persistence Score: "
        f"{result['persistence_score']:.4f}"
    )

    print(
        f"Industrial Score: "
        f"{result['industrial_score']:.4f}"
    )

    print(
        f"Evidence Score: "
        f"{result['evidence_score']:.4f}"
    )

    print(
        f"Confidence: "
        f"{result['confidence_score']:.4f}"
    )

    print(
        f"Risk Score: "
        f"{result['risk_score']:.4f}"
    )

    print(
        f"Risk Band: "
        f"{result['risk_band']}"
    )

    print(
        f"Severity: "
        f"{result['severity']}"
    )

    print(
        f"Industrial Context: "
        f"{result['industrial_context']}"
    )

    print(
        f"Reason: "
        f"{result['intelligence_reason']}"
    )


print()
print("=" * 40)
print("EVENT RISK TEST COMPLETE")
print("=" * 40)