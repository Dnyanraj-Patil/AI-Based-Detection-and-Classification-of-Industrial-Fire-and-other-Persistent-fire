from app.services.industrial_context_service import (
    process_all_event_industrial_context,
)


def main():

    print("\n========================================")
    print("THERMOINTEL INDUSTRIAL CONTEXT")
    print("========================================")

    print(
        "\n[1/1] Processing industrial context..."
    )

    processed = (
        process_all_event_industrial_context()
    )

    print(
        f"Processed events: {processed}"
    )

    print("\n========================================")
    print(
        "INDUSTRIAL CONTEXT PROCESSING COMPLETE"
    )
    print("========================================")


if __name__ == "__main__":
    main()