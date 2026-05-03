import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';
import type { HomeAssistant } from '../lib/ha-types';

@customElement('ggs-light-ppfd-settings')
export class LightPpfdSettings extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) extras: Record<string, string> = {};

  static override styles = [
    themeVariables,
    css`
      .row {
        display: grid;
        grid-template-columns: 1fr auto;
        align-items: center;
        gap: var(--ggs-spacing);
        padding: 8px 0;
        border-bottom: 1px solid var(--ggs-divider);
      }
      .row:last-child { border-bottom: none; }
      label { color: var(--ggs-fg-muted); font-size: 13px; }
      input {
        background: var(--ggs-divider);
        color: var(--ggs-fg);
        border: 1px solid transparent;
        border-radius: var(--ggs-radius-sm);
        padding: 6px 10px;
        font: inherit;
        text-align: right;
        width: 100px;
      }
      input:focus { outline: none; border-color: var(--ggs-tab-active); }
    `,
  ];

  private _num(slot: string): string {
    const id = this.extras[slot];
    return id ? (this.hass.states[id]?.state ?? '') : '';
  }

  private _setNum(slot: string, value: number) {
    const id = this.extras[slot];
    if (!id) return;
    this.hass.callService('number', 'set_value', { entity_id: id, value });
  }

  private _setText(slot: string, value: string) {
    const id = this.extras[slot];
    if (!id) return;
    this.hass.callService('text', 'set_value', { entity_id: id, value });
  }

  private _row(
    slot: string,
    label: string,
    type: 'number' | 'time',
    extra: { min?: number; max?: number } = {},
  ) {
    if (!this.extras[slot]) return null;
    if (type === 'time') {
      return html`<div class="row">
        <label>${label}</label>
        <input type="time"
          .value=${this._num(slot)}
          @change=${(e: Event) =>
            this._setText(slot, (e.target as HTMLInputElement).value)} />
      </div>`;
    }
    return html`<div class="row">
      <label>${label}</label>
      <input type="number"
        min=${extra.min ?? 0}
        max=${extra.max ?? 1000}
        .value=${this._num(slot)}
        @change=${(e: Event) =>
          this._setNum(slot, +(e.target as HTMLInputElement).value)} />
    </div>`;
  }

  override render() {
    return html`
      ${this._row('ppfd_target_ppfd', 'Target PPFD (µmol/m²/s)', 'number', { max: 1000 })}
      ${this._row('ppfd_start_time', 'Start Time', 'time')}
      ${this._row('ppfd_end_time', 'End Time', 'time')}
      ${this._row('ppfd_fade_time', 'Fade Time (min)', 'number', { max: 240 })}
      ${this._row('ppfd_min_brightness', 'Min Brightness (%)', 'number', { max: 100 })}
      ${this._row('ppfd_max_brightness', 'Max Brightness (%)', 'number', { max: 100 })}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-light-ppfd-settings': LightPpfdSettings;
  }
}
