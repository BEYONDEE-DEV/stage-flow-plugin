def schedule_payload(program):
    return {
        "programId": program["displayId"],
        "label": program["displayName"],
    }
