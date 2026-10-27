// How long ago a device last reported. A machine that went quiet is often the
// first sign of a problem, so anything older than the stale limit is flagged.

export const STALE_AFTER_MINUTES = 15

export function minutesSince(iso: string, now: Date = new Date()): number {
  return Math.floor((now.getTime() - new Date(iso).getTime()) / 60000)
}

export function lastSeenLabel(iso: string | null, now: Date = new Date()): string {
  if (!iso) return 'never'
  const m = minutesSince(iso, now)
  if (m < 1) return 'just now'
  if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} h ago`
  return `${Math.floor(h / 24)} d ago`
}

export function isStale(iso: string | null, now: Date = new Date()): boolean {
  return iso === null || minutesSince(iso, now) > STALE_AFTER_MINUTES
}
