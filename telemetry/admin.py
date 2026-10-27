from django.contrib import admin

from .models import Alert, AlertRule, Device, Reading


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["name", "external_id", "kind", "site"]
    search_fields = ["name", "external_id"]


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ["metric", "operator", "threshold", "device_kind", "active"]


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["device", "rule", "created_at", "acknowledged_at", "acknowledged_by"]
    list_filter = ["acknowledged_at"]


admin.site.register(Reading)
