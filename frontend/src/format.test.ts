import { describe, expect, it } from 'vitest'
import { isStale, lastSeenLabel } from './format'

const now = new Date('2026-10-27T10:00:00Z')

describe('lastSeenLabel', () => {
  it('handles a device that never reported', () => {
    expect(lastSeenLabel(null, now)).toBe('never')
  })
  it('uses minutes, hours and days', () => {
    expect(lastSeenLabel('2026-10-27T09:59:40Z', now)).toBe('just now')
    expect(lastSeenLabel('2026-10-27T09:48:00Z', now)).toBe('12 min ago')
    expect(lastSeenLabel('2026-10-27T07:00:00Z', now)).toBe('3 h ago')
    expect(lastSeenLabel('2026-10-25T09:00:00Z', now)).toBe('2 d ago')
  })
})

describe('isStale', () => {
  it('flags devices that went quiet', () => {
    expect(isStale('2026-10-27T09:50:00Z', now)).toBe(false)
    expect(isStale('2026-10-27T09:40:00Z', now)).toBe(true)
    expect(isStale(null, now)).toBe(true)
  })
})
