def format_record(record):
    ordered = {key: record[key] for key in sorted(record)}
    return ordered
