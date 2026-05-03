import { describe, it, expect } from 'vitest';
import { discoverDevices } from '../src/lib/discovery';
import type { HomeAssistant } from '../src/lib/ha-types';

function fakeHass(entityIds: string[]): HomeAssistant {
  const states: Record<string, any> = {};
  for (const id of entityIds) {
    const friendly = id.split('.')[1].replace(/^ggs_/, '').replace(/_/g, ' ');
    states[id] = {
      entity_id: id,
      state: 'off',
      attributes: { friendly_name: friendly },
    };
  }
  return { states } as unknown as HomeAssistant;
}

describe('discoverDevices', () => {
  it('returns nothing when there are no ggs entities', () => {
    const hass = fakeHass(['light.kitchen', 'fan.bedroom']);
    expect(discoverDevices(hass)).toEqual([]);
  });

  it('detects all four canonical devices', () => {
    const hass = fakeHass([
      'light.ggs_light_1',
      'light.ggs_light_2',
      'fan.ggs_fan_circulation',
      'fan.ggs_fan_exhaust',
    ]);
    const devices = discoverDevices(hass);
    expect(devices.map(d => d.entity)).toEqual([
      'light.ggs_light_1',
      'light.ggs_light_2',
      'fan.ggs_fan_circulation',
      'fan.ggs_fan_exhaust',
    ]);
    expect(devices.map(d => d.type)).toEqual(['light', 'light', 'fan', 'fan']);
  });

  it('builds the extras map for Light 1 schedule + ppfd entities', () => {
    const hass = fakeHass([
      'light.ggs_light_1',
      'number.ggs_light_1_schedule_mode_brightness',
      'text.ggs_light_1_schedule_mode_start_time',
      'text.ggs_light_1_schedule_mode_end_time',
      'number.ggs_light_1_schedule_mode_fade_time',
      'number.ggs_light_1_schedule_mode_dim_threshold',
      'number.ggs_light_1_schedule_mode_off_threshold',
      'number.ggs_light_1_ppfd_mode_target_ppfd',
      'text.ggs_light_1_ppfd_mode_start_time',
    ]);
    const devices = discoverDevices(hass);
    expect(devices).toHaveLength(1);
    expect(devices[0].extras).toMatchObject({
      schedule_brightness: 'number.ggs_light_1_schedule_mode_brightness',
      schedule_start_time: 'text.ggs_light_1_schedule_mode_start_time',
      schedule_end_time: 'text.ggs_light_1_schedule_mode_end_time',
      schedule_fade_time: 'number.ggs_light_1_schedule_mode_fade_time',
      schedule_dim_threshold: 'number.ggs_light_1_schedule_mode_dim_threshold',
      schedule_off_threshold: 'number.ggs_light_1_schedule_mode_off_threshold',
      ppfd_target_ppfd: 'number.ggs_light_1_ppfd_mode_target_ppfd',
      ppfd_start_time: 'text.ggs_light_1_ppfd_mode_start_time',
    });
  });

  it('builds extras for Fan Circulation including all three mode buckets', () => {
    const hass = fakeHass([
      'fan.ggs_fan_circulation',
      'text.ggs_fan_schedule_mode_start_time',
      'number.ggs_fan_schedule_mode_speed',
      'number.ggs_fan_schedule_mode_standby_speed',
      'number.ggs_fan_schedule_mode_oscillation',
      'switch.ggs_fan_schedule_mode_natural_wind',
      'text.ggs_fan_cycle_mode_start_time',
      'number.ggs_fan_cycle_mode_run_time',
      'number.ggs_fan_cycle_mode_off_time',
      'number.ggs_fan_cycle_mode_cycles',
      'select.ggs_fan_environment_mode_submode',
      'number.ggs_fan_environment_mode_speed',
    ]);
    const devices = discoverDevices(hass);
    expect(devices).toHaveLength(1);
    const d = devices[0];
    expect(d.entity).toBe('fan.ggs_fan_circulation');
    expect(d.extras.schedule_start_time).toBe('text.ggs_fan_schedule_mode_start_time');
    expect(d.extras.schedule_speed).toBe('number.ggs_fan_schedule_mode_speed');
    expect(d.extras.cycle_run_time).toBe('number.ggs_fan_cycle_mode_run_time');
    expect(d.extras.environment_submode).toBe('select.ggs_fan_environment_mode_submode');
  });

  it('does not mix Fan Circulation extras into Fan Exhaust', () => {
    const hass = fakeHass([
      'fan.ggs_fan_circulation',
      'fan.ggs_fan_exhaust',
      'number.ggs_fan_schedule_mode_speed',
      'number.ggs_fan_exhaust_schedule_mode_speed',
    ]);
    const devices = discoverDevices(hass);
    const circ = devices.find(d => d.entity === 'fan.ggs_fan_circulation')!;
    const exh = devices.find(d => d.entity === 'fan.ggs_fan_exhaust')!;
    expect(circ.extras.schedule_speed).toBe('number.ggs_fan_schedule_mode_speed');
    expect(exh.extras.schedule_speed).toBe('number.ggs_fan_exhaust_schedule_mode_speed');
  });

  it('respects the deviceIdFilter', () => {
    const hass = fakeHass(['light.ggs_light_1', 'light.ggs_light_2']);
    expect(discoverDevices(hass, 'ggs_1')).toHaveLength(2);
    expect(discoverDevices(hass, 'ggs_2')).toHaveLength(0);
  });

  it('uses friendly_name for the device name', () => {
    const hass: HomeAssistant = {
      states: {
        'light.ggs_light_1': {
          entity_id: 'light.ggs_light_1',
          state: 'on',
          attributes: { friendly_name: 'Light 1' },
        },
      },
    } as unknown as HomeAssistant;
    expect(discoverDevices(hass)[0].name).toBe('Light 1');
  });
});
