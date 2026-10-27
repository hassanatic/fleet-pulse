"""Batch ingest of telemetry readings.

Devices send readings in batches, often over unreliable links, so ingest is:
- validated per row, with bad rows reported back instead of failing the whole batch;
- idempotent, because a resent batch must not create duplicate readings or alerts;
- one transaction per batch, so alerts never point at readings that were rolled back.
"""

from dataclasses import dataclass, field

from django.db import transaction
from django.utils.dateparse import parse_datetime

from .models import Alert, AlertRule, Device, Reading

MAX_BATCH = 5000


@dataclass
class IngestResult:
    stored: int = 0
    duplicates: int = 0
    alerts: int = 0
    errors: list[dict] = field(default_factory=list)


def ingest(rows: list[dict]) -> IngestResult:
    result = IngestResult()
    if len(rows) > MAX_BATCH:
        result.errors.append({"row": None, "error": f"batch larger than {MAX_BATCH} rows"})
        return result

    devices = {d.external_id: d for d in Device.objects.filter(external_id__in={str(r.get("device")) for r in rows})}
    rules = list(AlertRule.objects.filter(active=True))

    with transaction.atomic():
        for i, row in enumerate(rows):
            device = devices.get(str(row.get("device")))
            if device is None:
                result.errors.append({"row": i, "error": f"unknown device {row.get('device')!r}"})
                continue
            metric = row.get("metric")
            if not isinstance(metric, str) or not metric:
                result.errors.append({"row": i, "error": "metric missing"})
                continue
            try:
                value = float(row.get("value"))
            except (TypeError, ValueError):
                result.errors.append({"row": i, "error": f"value {row.get('value')!r} is not a number"})
                continue
            recorded_at = parse_datetime(str(row.get("recorded_at") or ""))
            if recorded_at is None or recorded_at.tzinfo is None:
                result.errors.append({"row": i, "error": "recorded_at must be an ISO 8601 time with a timezone"})
                continue

            reading, created = Reading.objects.get_or_create(
                device=device, metric=metric, recorded_at=recorded_at, defaults={"value": value}
            )
            if not created:
                result.duplicates += 1
                continue
            result.stored += 1
            for rule in rules:
                if rule.matches(device, metric, value):
                    Alert.objects.create(device=device, rule=rule, reading=reading)
                    result.alerts += 1
    return result
