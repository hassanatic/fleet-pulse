from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from telemetry.ingest import ingest
from telemetry.models import AlertRule, Device


class Command(BaseCommand):
    help = "Create example devices, alert rules and a few readings."

    def handle(self, *args, **options):
        for ext, name, kind, site in [
            ("CR-1", "Harbour crane 1", "machine", "Port of Oulu"),
            ("FL-3", "Forklift 3", "vehicle", "Warehouse A"),
            ("TR-7", "Truck 7", "vehicle", "Depot"),
        ]:
            Device.objects.get_or_create(external_id=ext, defaults={"name": name, "kind": kind, "site": site})
        for metric, op, threshold, kind, message in [
            ("oil_temp_c", ">", 95, "", "Hydraulic oil too hot"),
            ("battery_v", "<", 11.5, "vehicle", "Battery voltage low"),
            ("load_pct", ">", 100, "machine", "Load above rated capacity"),
        ]:
            AlertRule.objects.get_or_create(
                metric=metric, operator=op, threshold=threshold, device_kind=kind, defaults={"message": message}
            )
        now = timezone.now().replace(microsecond=0)
        rows = []
        for i in range(6):
            t = (now - timedelta(minutes=5 * (5 - i))).isoformat()
            rows += [
                {"device": "CR-1", "metric": "oil_temp_c", "value": 82 + i * 3, "recorded_at": t},
                {"device": "CR-1", "metric": "load_pct", "value": 70 + i * 7, "recorded_at": t},
                {"device": "FL-3", "metric": "battery_v", "value": 12.4 - i * 0.2, "recorded_at": t},
            ]
        result = ingest(rows)
        self.stdout.write(f"stored {result.stored}, duplicates {result.duplicates}, alerts {result.alerts}")
