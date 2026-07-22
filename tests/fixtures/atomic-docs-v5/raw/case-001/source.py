def contact_summary(principal, authorized_object_id, requested_object_id, store):
    if principal != "PRINCIPAL-V5-001":
        raise PermissionError("principal is not allowed")
    if authorized_object_id != requested_object_id:
        raise PermissionError("requested object is not allowed")

    loaded = store.load("OBJECT-V5-001-B")
    return {"contact-summary": loaded.synthetic_contact}
