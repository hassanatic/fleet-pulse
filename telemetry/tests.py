import pytest
from rest_framework.test import APIClient

from .ingest import ingest
from .models import Alert, AlertRule, Device, Reading

pytestmark = pytest.mark.django_db


@pytest.fixture
def fleet():
    crane = Device.objects.create(external_id="CR-1", name="Crane 1", kind="machine", site="Port")
    truck = Device.objects.create(external_id="TR-7", name="Truck 7", kind="vehicle", site="Depot")
    AlertRule.objects.create(metric="oil_temp_c", operator=">", threshold=95, message="Oil too hot")
    AlertRule.objects.create(metric="battery_v", operator="<", threshold=11.5, device_kind="vehicle", message="Low battery")
    return crane, truck


def row(device, metric, value, t="2026-10-27T08:00:00+00:00"):
    return {"device": device, "metric": metric, "value": value, "recorded_at": t}


def test_stores_readings_and_raises_alerts_from_rules(fleet):
    result = ingest([row("CR-1", "oil_temp_c", 97.5), row("CR-1", "oil_temp_c", 80, "2026-10-27T08:01:00+00:00")])
    assert (result.stored, result.alerts, result.errors) == (2, 1, [])
    assert Alert.objects.get().rule.message == "Oil too hot"


def test_rule_scoped_to_a_device_kind(fleet):
    result = ingest([row("CR-1", "battery_v", 10.9), row("TR-7", "battery_v", 10.9)])
    assert result.alerts == 1
    assert Alert.objects.get().device.external_id == "TR-7"


def test_resent_batch_is_idempotent(fleet):
    batch = [row("CR-1", "oil_temp_c", 99)]
    ingest(batch)
    again = ingest(batch)
    assert (again.stored, again.duplicates, again.alerts) == (0, 1, 0)
    assert Reading.objects.count() == 1 and Alert.objects.count() == 1


def test_bad_rows_are_reported_and_good_rows_still_stored(fleet):
    result = ingest(
        [
            row("XX-0", "oil_temp_c", 50),
            row("CR-1", "", 50),
            row("CR-1", "oil_temp_c", "hot"),
            row("CR-1", "oil_temp_c", 50, "2026-10-27 08:00"),
            row("CR-1", "oil_temp_c", 50),
        ]
    )
    assert result.stored == 1
    assert [e["row"] for e in result.errors] == [0, 1, 2, 3]
    assert "timezone" in result.errors[3]["error"]


def test_inactive_rule_does_not_fire(fleet):
    AlertRule.objects.update(active=False)
    assert ingest([row("CR-1", "oil_temp_c", 120)]).alerts == 0


def test_api_ingest_devices_alerts_and_acknowledge(fleet):
    client = APIClient()
    res = client.post("/api/readings/", [row("TR-7", "battery_v", 11.0)], format="json")
    assert res.status_code == 201 and res.json()["alerts"] == 1

    devices = {d["external_id"]: d for d in client.get("/api/devices/").json()}
    assert devices["TR-7"]["open_alerts"] == 1
    assert devices["TR-7"]["last_seen"].startswith("2026-10-27T08:00:00")
    assert devices["CR-1"]["last_seen"] is None

    alert = client.get("/api/alerts/?open=1").json()[0]
    assert alert["message"] == "Low battery" and alert["value"] == 11.0

    assert client.post(f"/api/alerts/{alert['id']}/ack/", {}, format="json").status_code == 400
    ack = client.post(f"/api/alerts/{alert['id']}/ack/", {"by": "Aino"}, format="json").json()
    assert ack["acknowledged_by"] == "Aino"
    assert client.get("/api/alerts/?open=1").json() == []
    assert client.get("/api/devices/").json()[1]["open_alerts"] == 0


def test_api_rejects_a_batch_that_is_not_a_list(fleet):
    res = APIClient().post("/api/readings/", {"device": "CR-1"}, format="json")
    assert res.status_code == 400


def test_series_endpoint_returns_readings_in_time_order(fleet):
    crane, _ = fleet
    ingest([row("CR-1", "oil_temp_c", 70, "2026-10-27T08:02:00+00:00"), row("CR-1", "oil_temp_c", 60)])
    series = APIClient().get(f"/api/devices/{crane.id}/series/oil_temp_c/").json()
    assert [p["v"] for p in series] == [60, 70]
