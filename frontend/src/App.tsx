import { useCallback, useEffect, useState } from 'react'
import { acknowledgeAlert, fetchDevices, fetchOpenAlerts, type Alert, type Device } from './api'
import { isStale, lastSeenLabel } from './format'

const REFRESH_MS = 10_000

export default function App() {
  const [devices, setDevices] = useState<Device[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [operator, setOperator] = useState('')
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [d, a] = await Promise.all([fetchDevices(), fetchOpenAlerts()])
      setDevices(d)
      setAlerts(a)
      setError(null)
    } catch (e) {
      setError((e as Error).message)
    }
  }, [])

  useEffect(() => {
    load()
    const timer = setInterval(load, REFRESH_MS)
    return () => clearInterval(timer)
  }, [load])

  async function acknowledge(id: number) {
    if (!operator.trim()) {
      setError('Enter your name before acknowledging an alert')
      return
    }
    try {
      await acknowledgeAlert(id, operator.trim())
      await load()
    } catch (e) {
      setError((e as Error).message)
    }
  }

  return (
    <main>
      <h1>fleet-pulse</h1>
      {error && <p className="error">{error}</p>}

      <section>
        <h2>Open alerts ({alerts.length})</h2>
        <label>
          Operator <input value={operator} onChange={(e) => setOperator(e.target.value)} placeholder="your name" />
        </label>
        {alerts.length === 0 ? (
          <p>No open alerts.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Device</th>
                <th>Alert</th>
                <th>Value</th>
                <th>Recorded</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id}>
                  <td>{a.device}</td>
                  <td>{a.message}</td>
                  <td className="num">
                    {a.metric} = {a.value}
                  </td>
                  <td>{lastSeenLabel(a.recorded_at)}</td>
                  <td>
                    <button onClick={() => acknowledge(a.id)}>Acknowledge</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section>
        <h2>Devices</h2>
        <table>
          <thead>
            <tr>
              <th>Device</th>
              <th>Kind</th>
              <th>Site</th>
              <th>Last seen</th>
              <th className="num">Open alerts</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((d) => (
              <tr key={d.id}>
                <td>
                  {d.name} <small>{d.external_id}</small>
                </td>
                <td>{d.kind}</td>
                <td>{d.site}</td>
                <td className={isStale(d.last_seen) ? 'warn' : ''}>{lastSeenLabel(d.last_seen)}</td>
                <td className={`num ${d.open_alerts > 0 ? 'warn' : ''}`}>{d.open_alerts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}
