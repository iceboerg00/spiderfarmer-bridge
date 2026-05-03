import { describe, it, expect, beforeAll } from 'vitest';
import '../../src/components/mode-dropdown';
import type { ModeDropdown } from '../../src/components/mode-dropdown';

beforeAll(async () => {
  await customElements.whenDefined('ggs-mode-dropdown');
});

async function makeEl(value: string, options: string[]): Promise<ModeDropdown> {
  const el = document.createElement('ggs-mode-dropdown') as ModeDropdown;
  el.value = value;
  el.options = options;
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('<ggs-mode-dropdown>', () => {
  it('renders one <option> per provided option, with the current value selected', async () => {
    const el = await makeEl('Schedule', ['Manual', 'Schedule', 'PPFD']);
    const select = el.shadowRoot!.querySelector('select')!;
    expect(select.options).toHaveLength(3);
    expect(select.value).toBe('Schedule');
  });

  it('emits a "mode-change" event with the new value when the user picks one', async () => {
    const el = await makeEl('Manual', ['Manual', 'Schedule', 'PPFD']);
    const select = el.shadowRoot!.querySelector('select')!;
    let captured: string | null = null;
    el.addEventListener('mode-change', (e) => {
      captured = (e as CustomEvent<string>).detail;
    });
    select.value = 'Schedule';
    select.dispatchEvent(new Event('change'));
    expect(captured).toBe('Schedule');
  });

  it('renders a placeholder when value is not in the options list', async () => {
    const el = await makeEl('UnknownXYZ', ['Manual', 'Schedule']);
    const select = el.shadowRoot!.querySelector('select')!;
    expect(select.value).toBe('UnknownXYZ');
  });
});
