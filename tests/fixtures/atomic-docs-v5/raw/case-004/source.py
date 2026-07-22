def archive_record(record, archive):
    archive.keep(record, hours=72)


def publish_callback(client, payload):
    client.post(payload, signature=None)
