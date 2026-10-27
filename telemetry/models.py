from django.db import models


class Device(models.Model):
    """A machine or vehicle that reports telemetry, e.g. a crane, a forklift or a truck."""

    KIND_CHOICES = [
        ("vehicle", "Vehicle"),
        ("machine", "Machine"),
        ("sensor", "Fixed sensor"),
    ]

    external_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    site = models.CharField(max_length=120, blank=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.external_id})"


class Reading(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="readings")
    metric = models.CharField(max_length=64)
    value = models.FloatField()
    recorded_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["device", "metric", "-recorded_at"])]
        # A device can resend a batch after a network drop; the same sample must not count twice.
        constraints = [
            models.UniqueConstraint(fields=["device", "metric", "recorded_at"], name="unique_sample"),
        ]


class AlertRule(models.Model):
    OPERATORS = [(">", "greater than"), ("<", "less than")]

    metric = models.CharField(max_length=64)
    operator = models.CharField(max_length=1, choices=OPERATORS)
    threshold = models.FloatField()
    # Applies to every device of this kind when set, otherwise to all devices.
    device_kind = models.CharField(max_length=16, blank=True)
    message = models.CharField(max_length=200)
    active = models.BooleanField(default=True)

    def matches(self, device: Device, metric: str, value: float) -> bool:
        if not self.active or metric != self.metric:
            return False
        if self.device_kind and self.device_kind != device.kind:
            return False
        return value > self.threshold if self.operator == ">" else value < self.threshold

    def __str__(self) -> str:
        return f"{self.metric} {self.operator} {self.threshold}"


class Alert(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="alerts")
    rule = models.ForeignKey(AlertRule, on_delete=models.PROTECT)
    reading = models.ForeignKey(Reading, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
