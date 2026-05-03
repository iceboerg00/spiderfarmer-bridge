import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';
import type { HomeAssistant } from '../lib/ha-types';
import '../components/switch';

@customElement('ggs-fan-schedule-settings')
export class FanScheduleSettings extends LitElement {
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
      input[type="number"], input[type="time"] {
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
      ha-switch { --mdc-theme-secondary: var(--ggs-fan-accent); }
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

  private _setText(slot: string, value: string) {
    const id = this.extras[slot];
    if (!id) return;
    this.hass.callService('text', 'set_value', { entity_id: id, value });
  }

  private _toggleSwitch(slot: string, on: boolean) {
    const id = this.extras[slot];
    if (!id) return;
    this.hass.callService('switch', on ? 'turn_on' : 'turn_off', { entity_id: id });
  }

  override render() {
    return html`
      ${this.extras.schedule_start_time
        ? html`<div class="row">
            <label>Start Time</label>
            <input type="time" .value=${this._state('schedule_start_time')}
              @change=${(e: Event) =>
                this._setText('schedule_start_time', (e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.schedule_end_time
        ? html`<div class="row">
            <label>End Time</label>
            <input type="time" .value=${this._state('schedule_end_time')}
              @change=${(e: Event) =>
                this._setText('schedule_end_time', (e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.schedule_speed
        ? html`<div class="row">
            <label>Speed (1-${this.speedMax})</label>
            <input type="number" min="1" max=${this.speedMax}
              .value=${this._state('schedule_speed')}
              @change=${(e: Event) =>
                this._setNum('schedule_speed', +(e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.schedule_standby_speed
        ? html`<div class="row">
            <label>Standby Speed (0-${this.speedMax})</label>
            <input type="number" min="0" max=${this.speedMax}
              .value=${this._state('schedule_standby_speed')}
              @change=${(e: Event) =>
                this._setNum('schedule_standby_speed', +(e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.schedule_oscillation
        ? html`<div class="row">
            <label>Oscillation (0-10)</label>
            <input type="number" min="0" max="10"
              .value=${this._state('schedule_oscillation')}
              @change=${(e: Event) =>
                this._setNum('schedule_oscillation', +(e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.schedule_natural_wind
        ? html`<div class="row">
            <label>Natural Wind</label>
            <ggs-switch
              .checked=${this._state('schedule_natural_wind') === 'on'}
              .label=${'Natural Wind'}
              @change=${(e: CustomEvent<boolean>) =>
                this._toggleSwitch('schedule_natural_wind', e.detail)}></ggs-switch>
          </div>`
        : null}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-fan-schedule-settings': FanScheduleSettings;
  }
}
