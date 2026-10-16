def parse_lateness(value):
    """Separate numeric values from special or unknown statuses."""
    if value in (999, "999"):
        return {
            "reported_delay": None,
            "status": "cancelled_or_suspended",
        }

    if type(value) is int:
        return {
            "reported_delay": value,
            "status": "numeric",
        }

    return {
        "reported_delay": None,
        "status": "unknown",
    }


if __name__ == "__main__":
    assert parse_lateness(5) == {
        "reported_delay": 5,
        "status": "numeric",
    }

    assert parse_lateness(999)["reported_delay"] is None
    assert parse_lateness("999")["status"] == "cancelled_or_suspended"
    assert parse_lateness(None)["status"] == "unknown"

    print("Lateness parsing checks passed!")
    