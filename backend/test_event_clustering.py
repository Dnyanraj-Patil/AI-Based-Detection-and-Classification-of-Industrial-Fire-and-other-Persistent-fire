from app.services.event_clustering import (
    cluster_firms_events,
)


print("\n========================================")
print("THERMOINTEL EVENT CLUSTERING")
print("========================================")


events = cluster_firms_events()


# ============================================================
# SUMMARY
# ============================================================

total_detections = sum(
    event["detection_count"]
    for event in events
)


print(
    f"\nRaw detections: "
    f"{total_detections}"
)


print(
    f"Thermal events: "
    f"{len(events)}"
)


# ============================================================
# EVENT DETAILS
# ============================================================

for index, event in enumerate(
    events,
    start=1,
):

    print("\n----------------------------------------")

    print(
        f"EVENT #{index}"
    )

    print(
        f"Cluster ID: "
        f"{event['cluster_id']}"
    )

    print(
        f"Detections: "
        f"{event['detection_count']}"
    )

    print(
        f"Detection IDs: "
        f"{event['detection_ids']}"
    )

    print(
        f"Fingerprint: "
        f"{event['event_fingerprint']}"
    )

    print(
        f"First: "
        f"{event['first_detected_at']}"
    )

    print(
        f"Last: "
        f"{event['last_detected_at']}"
    )

    print(
        f"Observation span: "
        f"{event['observation_duration_minutes']} "
        f"minutes"
    )

    print(
        f"Max FRP: "
        f"{event['max_frp']}"
    )

    print(
        f"Average FRP: "
        f"{event['average_frp']}"
    )

    print(
        f"Max Brightness: "
        f"{event['max_bright_ti4']}"
    )

    print(
        f"Average Brightness: "
        f"{event['average_bright_ti4']}"
    )

    print(
        f"Location: "
        f"{event['latitude']}, "
        f"{event['longitude']}"
    )

    print(
        f"Satellites: "
        f"{event['satellites']}"
    )


print("\n========================================")
print("CLUSTERING TEST COMPLETE")
print("========================================")