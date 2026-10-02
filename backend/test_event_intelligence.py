from app.services.event_intelligence_service import (
    classify_event,
)


EVENT_ID = 1


def main():

    print(
        "========================================"
    )
    print(
        "THERMOINTEL EVENT INTELLIGENCE TEST"
    )
    print(
        "========================================"
    )

    result = classify_event(
        EVENT_ID
    )

    if result is None:

        print(
            f"Event {EVENT_ID} not found."
        )

        return

    print()

    print(
        f"Event ID: "
        f"{result['event_id']}"
    )

    print(
        f"Severity: "
        f"{result['severity']}"
    )

    print(
        f"Risk Confidence: "
        f"{result['confidence_score']:.4f}"
    )

    print(
        f"Classification: "
        f"{result['classification']}"
    )

    print(
        f"Classification Confidence: "
        f"{result['classification_confidence']:.4f}"
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
        f"Industrial Context: "
        f"{result['industrial_context']}"
    )

    print()

    print(
        "Intelligence Reason:"
    )

    print(
        result["intelligence_reason"]
    )

    print()

    print(
        "========================================"
    )
    print(
        "EVENT INTELLIGENCE TEST COMPLETE"
    )
    print(
        "========================================"
    )


if __name__ == "__main__":
    main()