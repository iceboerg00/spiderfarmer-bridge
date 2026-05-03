import type { HomeAssistant } from './ha-types';

export type DeviceType = 'light' | 'fan';

export interface DiscoveredDevice {
  /** Logical id derived from the prefix, e.g. 'ggs_1'. v1 always emits 'ggs_1'. */
  id: string;
  type: DeviceType;
  /** Top-level entity_id, e.g. 'light.ggs_light_1' or 'fan.ggs_fan_circulation'. */
  entity: string;
  /** Display name from the entity's friendly_name attribute. */
  name: string;
  /**
   * Map of slot keys → entity_ids for sub-device entities (settings).
   *  - light: schedule_brightness, schedule_start_time, …, ppfd_target_ppfd, …
   *  - fan:   schedule_speed, cycle_run_time, environment_submode, …
   */
  extras: Record<string, string>;
}

interface DeviceDescriptor {
  domain: DeviceType;
  /** Top-level entity suffix, e.g. 'light_1' for 'light.ggs_light_1'. */
  topSuffix: string;
  /** Sub-device prefix patterns: each entry strips its prefix to form the slot key. */
  subPrefixes: { prefix: string; slotPrefix: string }[];
}

const DEVICES: DeviceDescriptor[] = [
  {
    domain: 'light',
    topSuffix: 'light_1',
    subPrefixes: [
      { prefix: 'light_1_schedule_mode_', slotPrefix: 'schedule_' },
      { prefix: 'light_1_ppfd_mode_', slotPrefix: 'ppfd_' },
    ],
  },
  // Light 2 is intentionally not surfaced in the GGS card — its
  // settings mirror Light 1's but the SF App's Light 2 panel has no
  // schedule/ppfd extras worth a tab. The standard HA light card
  // handles plain on/off + brightness for it.
  {
    domain: 'fan',
    topSuffix: 'fan_circulation',
    subPrefixes: [
      { prefix: 'fan_schedule_mode_', slotPrefix: 'schedule_' },
      { prefix: 'fan_cycle_mode_', slotPrefix: 'cycle_' },
      { prefix: 'fan_environment_mode_', slotPrefix: 'environment_' },
    ],
  },
  {
    domain: 'fan',
    topSuffix: 'fan_exhaust',
    subPrefixes: [
      { prefix: 'fan_exhaust_schedule_mode_', slotPrefix: 'schedule_' },
      { prefix: 'fan_exhaust_cycle_mode_', slotPrefix: 'cycle_' },
      { prefix: 'fan_exhaust_environment_mode_', slotPrefix: 'environment_' },
    ],
  },
];

/**
 * Auto-discover GGS devices and their settings entities from hass.states.
 * Filter by `deviceIdFilter` ('ggs_1', 'ggs_2', …) when set.
 *
 * v1 keys every device under 'ggs_1'; multi-controller setups will need the
 * filter wired through more carefully but currently all known entity_ids
 * use the single 'ggs_' prefix.
 */
export function discoverDevices(
  hass: HomeAssistant,
  deviceIdFilter?: string,
): DiscoveredDevice[] {
  if (deviceIdFilter && deviceIdFilter !== 'ggs_1') {
    return [];
  }

  const allIds = Object.keys(hass.states ?? {});
  const result: DiscoveredDevice[] = [];

  for (const desc of DEVICES) {
    const topId = `${desc.domain}.ggs_${desc.topSuffix}`;
    const topState = hass.states[topId];
    if (!topState) continue;

    const extras: Record<string, string> = {};
    for (const sub of desc.subPrefixes) {
      const fullPrefix = `ggs_${sub.prefix}`;
      for (const id of allIds) {
        const localPart = id.split('.')[1];
        if (!localPart || !localPart.startsWith(fullPrefix)) continue;
        const tail = localPart.slice(fullPrefix.length);
        if (!tail) continue;
        extras[`${sub.slotPrefix}${tail}`] = id;
      }
    }

    result.push({
      id: 'ggs_1',
      type: desc.domain,
      entity: topId,
      name: topState.attributes?.friendly_name ?? desc.topSuffix,
      extras,
    });
  }

  return result;
}
