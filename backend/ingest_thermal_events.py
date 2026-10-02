from app.services.event_clustering import (
    cluster_firms_events,
)

from app.services.event_repository import (
    save_thermal_events,
)


def main():

    print("\n========================================")
    print("THERMOINTEL THERMAL EVENT PROCESSING")
    print("========================================")


    # --------------------------------------------------------
    # 1. Cluster
    # --------------------------------------------------------

    print(
        "\n[1/2] Building thermal events..."
    )

    events = cluster_firms_events()

    total_detections = sum(
        event["detection_count"]
        for event in events
    )

    print(
        f"Raw detections: "
        f"{total_detections}"
    )

    print(
        f"Thermal events: "
        f"{len(events)}"
    )


    # --------------------------------------------------------
    # 2. Persist
    # --------------------------------------------------------

    print(
        "\n[2/2] Saving thermal events..."
    )

    processed = save_thermal_events(
        events
    )

    print(
        f"Processed events: "
        f"{processed}"
    )


    print(
        "\n========================================"
    )

    print(
        "THERMAL EVENT PROCESSING COMPLETE"
    )

    print(
        "========================================"
    )


if __name__ == "__main__":
    main()