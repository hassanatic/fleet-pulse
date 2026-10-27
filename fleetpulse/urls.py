from django.contrib import admin
from django.urls import path

from telemetry import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/devices/", views.devices),
    path("api/readings/", views.readings),
    path("api/alerts/", views.alerts),
    path("api/alerts/<int:alert_id>/ack/", views.acknowledge),
    path("api/devices/<int:device_id>/series/<str:metric>/", views.metric_series),
]
