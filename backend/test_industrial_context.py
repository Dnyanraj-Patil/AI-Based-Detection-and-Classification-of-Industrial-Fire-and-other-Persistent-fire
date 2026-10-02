from app.services.industrial_context_service import (
    calculate_event_industrial_context,
)


print("\n========================================")
print("THERMOINTEL INDUSTRIAL CONTEXT TEST")
print("========================================")


EVENT_ID = 1


context = calculate_event_industrial_context(
    EVENT_ID
)


if context is None:

    print("\nNo industrial context found.")

else:

    print(
        f"\nThermal Event: "
        f"{EVENT_ID}"
    )

    # --------------------------------------------------------
    # Nearest facility
    # --------------------------------------------------------

    print(
        f"\nNearest Facility ID: "
        f"{context['nearest_facility_id']}"
    )

    print(
        f"Nearest Facility: "
        f"{context['nearest_facility_name']}"
    )

    # --------------------------------------------------------
    # Distance
    # --------------------------------------------------------

    distance = (
        context[
            "nearest_facility_distance_meters"
        ]
    )

    if distance is None:

        print(
            "Distance: "
            "No facility within 10 km"
        )

    else:

        print(
            f"Distance: "
            f"{float(distance):.2f} meters"
        )

    # --------------------------------------------------------
    # Facility counts
    # --------------------------------------------------------

    print(
        f"Facilities within 1 km: "
        f"{context['facilities_within_1km']}"
    )

    print(
        f"Facilities within 5 km: "
        f"{context['facilities_within_5km']}"
    )

    # --------------------------------------------------------
    # Facility classification
    # --------------------------------------------------------

    print(
        f"Facility Type: "
        f"{context['nearest_facility_type']}"
    )

    print(
        f"Industrial Type: "
        f"{context['nearest_industrial_type']}"
    )

    # --------------------------------------------------------
    # Industrial area
    # --------------------------------------------------------

    print(
        f"Inside Industrial Area: "
        f"{context['is_inside_industrial_area']}"
    )


print("\n========================================")
print("INDUSTRIAL CONTEXT TEST COMPLETE")
print("========================================")