# fleet-pulse

Telemetry ingest and alerting for a fleet of machines and vehicles, with a small operator dashboard.
Django and Django REST Framework on the backend, React and TypeScript on the frontend.

Cranes, forklifts and trucks report readings such as hydraulic oil temperature, load or battery voltage.
fleet-pulse stores those readings, checks them against alert rules, and gives operators one screen with
the open alerts and every device's last report, where an alert is acknowledged by name.

## How ingest works

Devices send batches over links that drop, so `POST /api/readings/` is built for that:

- **Per-row validation.** An unknown device, a missing metric, a non-numeric value or a timestamp without
  a timezone is reported back with its row number; the valid rows in the same batch are still stored.
- **Idempotent.** A unique constraint on (device, metric, recorded_at) means a resent batch neither
  duplicates readings nor raises the same alert twice; the response counts the duplicates.
- **One transaction per batch,** so an alert never points at a reading that was rolled back.
- **Rules** compare a metric against a threshold (`>` or `<`) and can be limited to one kind of device,
  for example low battery only for vehicles.

## API

| Method | Path | |
|---|---|---|
| POST | `/api/readings/` | JSON list of `{device, metric, value, recorded_at}`; returns stored, duplicates, alerts, errors |
| GET | `/api/devices/` | devices with open alert count and last report time |
| GET | `/api/alerts/?open=1` | open alerts with the reading that triggered them |
| POST | `/api/alerts/<id>/ack/` | `{"by": "name"}`; refuses an acknowledgement without a name |
| GET | `/api/devices/<id>/series/<metric>/` | the latest 500 readings of one metric, oldest first |

Devices and rules are managed in the Django admin.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo        # three devices, three rules, sample readings
.venv/bin/python manage.py runserver

cd frontend && npm install && npm run dev   # http://localhost:5173, proxies /api to Django
```

## Tests

```bash
.venv/bin/pytest                     # backend: ingest, rules, idempotency, API, acknowledge
cd frontend && npm test && npm run build
```

CI runs both on every push.

## Not in it

No authentication or per-site permissions, no message broker (devices post over HTTP), no time-series
database (readings are rows in the Django database, SQLite by default), and no notifications.
