from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .ingest import ingest
from .models import Alert, Device, Reading


class DeviceSerializer(serializers.ModelSerializer):
    open_alerts = serializers.IntegerField(read_only=True)
    last_seen = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ["id", "external_id", "name", "kind", "site", "open_alerts", "last_seen"]

    def get_last_seen(self, obj):
        last = obj.readings.order_by("-recorded_at").values_list("recorded_at", flat=True).first()
        return last.isoformat() if last else None


class AlertSerializer(serializers.ModelSerializer):
    device = serializers.CharField(source="device.name")
    message = serializers.CharField(source="rule.message")
    metric = serializers.CharField(source="reading.metric")
    value = serializers.FloatField(source="reading.value")
    recorded_at = serializers.DateTimeField(source="reading.recorded_at")

    class Meta:
        model = Alert
        fields = ["id", "device", "message", "metric", "value", "recorded_at", "acknowledged_at", "acknowledged_by"]


@api_view(["GET"])
def devices(request):
    qs = Device.objects.annotate(open_alerts=Count("alerts", filter=Q(alerts__acknowledged_at__isnull=True))).order_by(
        "name"
    )
    return Response(DeviceSerializer(qs, many=True).data)


@api_view(["POST"])
def readings(request):
    rows = request.data if isinstance(request.data, list) else request.data.get("readings")
    if not isinstance(rows, list):
        return Response({"error": "send a JSON list of readings"}, status=status.HTTP_400_BAD_REQUEST)
    result = ingest(rows)
    code = status.HTTP_201_CREATED if result.stored else status.HTTP_200_OK
    if not result.stored and not result.duplicates and result.errors:
        code = status.HTTP_400_BAD_REQUEST
    return Response(result.__dict__, status=code)


@api_view(["GET"])
def alerts(request):
    qs = Alert.objects.select_related("device", "rule", "reading")
    if request.query_params.get("open") == "1":
        qs = qs.filter(acknowledged_at__isnull=True)
    return Response(AlertSerializer(qs[:200], many=True).data)


@api_view(["POST"])
def acknowledge(request, alert_id: int):
    alert = get_object_or_404(Alert, pk=alert_id)
    who = str(request.data.get("by", "")).strip()
    if not who:
        return Response({"error": "say who acknowledged the alert"}, status=status.HTTP_400_BAD_REQUEST)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = who
        alert.save(update_fields=["acknowledged_at", "acknowledged_by"])
    return Response(AlertSerializer(alert).data)


@api_view(["GET"])
def metric_series(request, device_id: int, metric: str):
    device = get_object_or_404(Device, pk=device_id)
    rows = Reading.objects.filter(device=device, metric=metric).order_by("-recorded_at")[:500]
    return Response([{"t": r.recorded_at.isoformat(), "v": r.value} for r in reversed(rows)])
