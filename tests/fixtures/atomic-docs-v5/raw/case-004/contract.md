# Synthetic Service Contracts

## Retention Contract

Contract ID: `CONTRACT-V5-004-A`

Authority revision: `REV-V5-004-A`

Applicability: verified for `CONSUMER-V5-004-A` and `archive_record` in `source.py`.

Synthetic transient records must be retained for no more than 24 hours.

## Callback Contract

Contract ID: `CONTRACT-V5-004-B`

Authority revision: `REV-V5-004-B`

Applicability: verified for `CONSUMER-V5-004-B` and `publish_callback` in `source.py`.

Every outbound callback must include a generated request signature.
