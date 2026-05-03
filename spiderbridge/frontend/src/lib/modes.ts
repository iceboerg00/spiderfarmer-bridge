export const LIGHT_MODES = ['Manual', 'Schedule', 'PPFD'] as const;
export type LightMode = typeof LIGHT_MODES[number];

export const FAN_PRESET_MODES = [
  'Manual',
  'Schedule',
  'Cycle',
  'Environment: Prioritize temperature',
  'Environment: Prioritize humidity',
  'Environment: Temperature only',
  'Environment: Humidity only',
  'Environment: Temperature & humidity',
] as const;
export type FanPresetMode = typeof FAN_PRESET_MODES[number];

export const FAN_ENV_SUBMODES = [
  'Prioritize temperature',
  'Prioritize humidity',
  'Temperature only',
  'Humidity only',
  'Temperature & humidity',
] as const;
export type FanEnvSubmode = typeof FAN_ENV_SUBMODES[number];

export function isEnvironmentMode(mode: string | null | undefined): boolean {
  return typeof mode === 'string' && mode.startsWith('Environment:');
}
