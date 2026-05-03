import { describe, it, expect, beforeAll } from 'vitest';
import '../../src/components/settings-panel';
import type { SettingsPanel } from '../../src/components/settings-panel';

beforeAll(async () => {
  await customElements.whenDefined('ggs-settings-panel');
});

async function makeEl(props: Partial<SettingsPanel>): Promise<SettingsPanel> {
  const el = document.createElement('ggs-settings-panel') as SettingsPanel;
  Object.assign(el, props);
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

const fakeHass = { states: {}, callService: () => Promise.resolve() } as any;

describe('<ggs-settings-panel>', () => {
  it('renders <ggs-light-schedule-settings> for light + Schedule', async () => {
    const el = await makeEl({
      hass: fakeHass,
      deviceType: 'light',
      mode: 'Schedule',
      extras: {},
    });
    expect(el.shadowRoot!.querySelector('ggs-light-schedule-settings')).toBeTruthy();
  });

  it('renders <ggs-light-ppfd-settings> for light + PPFD', async () => {
    const el = await makeEl({
      hass: fakeHass,
      deviceType: 'light',
      mode: 'PPFD',
      extras: {},
    });
    expect(el.shadowRoot!.querySelector('ggs-light-ppfd-settings')).toBeTruthy();
  });

  it('renders <ggs-fan-schedule-settings> for fan + Schedule', async () => {
    const el = await makeEl({
      hass: fakeHass,
      deviceType: 'fan',
      mode: 'Schedule',
      extras: {},
    });
    expect(el.shadowRoot!.querySelector('ggs-fan-schedule-settings')).toBeTruthy();
  });

  it('renders <ggs-fan-cycle-settings> for fan + Cycle', async () => {
    const el = await makeEl({
      hass: fakeHass,
      deviceType: 'fan',
      mode: 'Cycle',
      extras: {},
    });
    expect(el.shadowRoot!.querySelector('ggs-fan-cycle-settings')).toBeTruthy();
  });

  it('renders <ggs-fan-environment-settings> for any Environment mode', async () => {
    for (const mode of [
      'Environment: Prioritize temperature',
      'Environment: Prioritize humidity',
      'Environment: Temperature & humidity',
    ]) {
      const el = await makeEl({
        hass: fakeHass,
        deviceType: 'fan',
        mode,
        extras: {},
      });
      expect(
        el.shadowRoot!.querySelector('ggs-fan-environment-settings'),
        `mode=${mode}`,
      ).toBeTruthy();
      el.remove();
    }
  });

  it('renders the "no mode-specific settings" placeholder for light + Manual', async () => {
    const el = await makeEl({
      hass: fakeHass,
      deviceType: 'light',
      mode: 'Manual',
      extras: {},
    });
    const text = el.shadowRoot!.textContent ?? '';
    expect(text).toContain('No mode-specific settings');
  });

  it('renders <ggs-fan-manual-settings> for fan + Manual when oscillation/natural_wind extras exist', async () => {
    const el = await makeEl({
      hass: fakeHass,
      deviceType: 'fan',
      mode: 'Manual',
      extras: { schedule_oscillation: 'number.fan_oscillation' },
    });
    expect(el.shadowRoot!.querySelector('ggs-fan-manual-settings')).toBeTruthy();
  });

  it('falls back to placeholder for fan + Manual with no oscillation/natural_wind extras (Fan Exhaust)', async () => {
    const el = await makeEl({
      hass: fakeHass,
      deviceType: 'fan',
      mode: 'Manual',
      extras: { schedule_speed: 'number.fan_exhaust_speed' },
    });
    expect(el.shadowRoot!.querySelector('ggs-fan-manual-settings')).toBeNull();
    expect(el.shadowRoot!.textContent ?? '').toContain('No mode-specific settings');
  });

  it('renders an "Unknown mode" placeholder for unrecognized labels', async () => {
    const el = await makeEl({
      hass: fakeHass,
      deviceType: 'fan',
      mode: 'Bogus',
      extras: {},
    });
    expect(el.shadowRoot!.textContent ?? '').toContain('Unknown mode: Bogus');
  });
});
