export interface Device {
  id: number
  external_id: string
  name: string
  kind: 'vehicle' | 'machine' | 'sensor'
  site: string
  open_alerts: number
  last_seen: string | null
}

export interface Alert {
  id: number
  device: string
  message: string
  metric: string
  value: number
  recorded_at: string
  acknowledged_at: string | null
  acknowledged_by: string
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.error ?? `request failed with ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const fetchDevices = () => fetch('/api/devices/').then((r) => json<Device[]>(r))

export const fetchOpenAlerts = () => fetch('/api/alerts/?open=1').then((r) => json<Alert[]>(r))

export const acknowledgeAlert = (id: number, by: string) =>
  fetch(`/api/alerts/${id}/ack/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ by }),
  }).then((r) => json<Alert>(r))
