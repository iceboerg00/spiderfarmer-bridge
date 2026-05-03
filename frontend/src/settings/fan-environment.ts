import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';
import { FAN_ENV_SUBMODES } from '../lib/modes';
import type { HomeAssistant } from '../lib/ha-types';

@customElement('ggs-fan-environment-settings')
export class FanEnvironmentSettings extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ attribute: false }) extras: Record<string, string> = {};
  @property({ type: Number }) speedMax = 10;

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
      input[type="number"], select {
        background: var(--ggs-divider);
        color: var(--ggs-fg);
        border: 1px solid transparent;
        border-radius: var(--ggs-radius-sm);
        padding: 6px 10px;
        font: inherit;
      }
      input[type="number"] { text-align: right; width: 100px; }
      select { width: 220px; }
      input:focus, select:focus { outline: none; border-color: var(--ggs-tab-active); }
    `,
  ];

  private _state(slot: string): string {
    const id = this.extras[slot];
    return id ? (this.hass.states[id]?.state ?? '') : '';
  }

  private _setNum(slot: string, value: number) {
    const id = this.extras[slot];
    if (!id) return;
    this.hass.callService('number', 'set_value', { entity_id: id, value });
  }

  private _setSelect(slot: string, value: string) {
    const id = this.extras[slot];
    if (!id) return;
    this.hass.callService('select', 'select_option', { entity_id: id, option: value });
  }

  private _toggleSwitch(slot: string, on: boolean) {
    const id = this.extras[slot];
    if (!id) return;
    this.hass.callService('switch', on ? 'turn_on' : 'turn_off', { entity_id: id });
  }

  override render() {
    return html`
      ${this.extras.environment_submode
        ? html`<div class="row">
            <label>Submode</label>
            <select .value=${this._state('environment_submode')}
              @change=${(e: Event) =>
                this._setSelect('environment_submode', (e.target as HTMLSelectElement).value)}>
              ${FAN_ENV_SUBMODES.map(
                (m) => html`<option value=${m}>${m}</option>`,
              )}
            </select>
          </div>`
        : null}
      ${this.extras.environment_speed
        ? html`<div class="row">
            <label>Speed (1-${this.speedMax})</label>
            <input type="number" min="1" max=${this.speedMax}
              .value=${this._state('environment_speed')}
              @change=${(e: Event) =>
                this._setNum('environment_speed', +(e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.environment_standby_speed
        ? html`<div class="row">
            <label>Standby Speed (0-${this.speedMax})</label>
            <input type="number" min="0" max=${this.speedMax}
              .value=${this._state('environment_standby_speed')}
              @change=${(e: Event) =>
                this._setNum('environment_standby_speed', +(e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.environment_oscillation
        ? html`<div class="row">
            <label>Oscillation (0-10)</label>
            <input type="number" min="0" max="10"
              .value=${this._state('environment_oscillation')}
              @change=${(e: Event) =>
                this._setNum('environment_oscillation', +(e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.environment_natural_wind
        ? html`<div class="row">
            <label>Natural Wind</label>
            <input type="checkbox"
              .checked=${this._state('environment_natural_wind') === 'on'}
              @change=${(e: Event) =>
                this._toggleSwitch('environment_natural_wind', (e.target as HTMLInputElement).checked)} />
          </div>`
        : null}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-fan-environment-settings': FanEnvironmentSettings;
  }
}
