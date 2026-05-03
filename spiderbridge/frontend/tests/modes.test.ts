import { describe, it, expect } from 'vitest';
import {
  LIGHT_MODES,
  FAN_PRESET_MODES,
  FAN_ENV_SUBMODES,
  isEnvironmentMode,
} from '../src/lib/modes';

describe('LIGHT_MODES', () => {
  it('lists Manual, Schedule, PPFD', () => {
    expect(LIGHT_MODES).toEqual(['Manual', 'Schedule', 'PPFD']);
  });
});

describe('FAN_PRESET_MODES', () => {
  it('lists all eight modes in SF App order', () => {
    expect(FAN_PRESET_MODES).toEqual([
      'Manual',
      'Schedule',
      'Cycle',
      'Environment: Prioritize temperature',
      'Environment: Prioritize humidity',
      'Environment: Temperature only',
      'Environment: Humidity only',
      'Environment: Temperature & humidity',
    ]);
  });
});

describe('FAN_ENV_SUBMODES', () => {
  it('lists the five env variants without the prefix', () => {
    expect(FAN_ENV_SUBMODES).toEqual([
      'Prioritize temperature',
      'Prioritize humidity',
      'Temperature only',
      'Humidity only',
      'Temperature & humidity',
    ]);
  });
});

describe('isEnvironmentMode', () => {
  it('returns true for any "Environment: …" label', () => {
    expect(isEnvironmentMode('Environment: Prioritize temperature')).toBe(true);
    expect(isEnvironmentMode('Environment: Temperature & humidity')).toBe(true);
  });

  it('returns false for non-environment modes', () => {
    expect(isEnvironmentMode('Manual')).toBe(false);
    expect(isEnvironmentMode('Schedule')).toBe(false);
    expect(isEnvironmentMode('Cycle')).toBe(false);
  });

  it('returns false for empty / null inputs', () => {
    expect(isEnvironmentMode('')).toBe(false);
    expect(isEnvironmentMode(null)).toBe(false);
    expect(isEnvironmentMode(undefined)).toBe(false);
  });
});
