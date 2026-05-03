import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';
import type { HomeAssistant } from '../lib/ha-types';

@customElement('ggs-light-schedule-settings')
export class LightScheduleSettings extends LitElement {
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
    `,
  ];

  private _setNumber(slot: string, value: number) {
    const entity = this.extras[slot];
    if (!entity) return;
    this.hass.callService('number', 'set_value', { entity_id: entity, value });
  }

  private _setText(slot: string, value: string) {
    const entity = this.extras[slot];
    if (!entity) return;
    this.hass.callService('text', 'set_value', { entity_id: entity, value });
  }

  private _stateNum(slot: string): string {
    const id = this.extras[slot];
    if (!id) return '';
    return this.hass.states[id]?.state ?? '';
  }

  private _stateText(slot: string): string {
    return this._stateNum(slot);
  }

  override render() {
    return html`
      ${this.extras.schedule_brightness
        ? html`<div class="row">
            <label>Brightness (%)</label>
            <input type="number" min="0" max="100"
              .value=${this._stateNum('schedule_brightness')}
              @change=${(e: Event) =>
                this._setNumber('schedule_brightness', +(e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.schedule_start_time
        ? html`<div class="row">
            <label>Start Time</label>
            <input type="time"
              .value=${this._stateText('schedule_start_time')}
              @change=${(e: Event) =>
                this._setText('schedule_start_time', (e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.schedule_end_time
        ? html`<div class="row">
            <label>End Time</label>
            <input type="time"
              .value=${this._stateText('schedule_end_time')}
              @change=${(e: Event) =>
                this._setText('schedule_end_time', (e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${this.extras.schedule_fade_time
        ? html`<div class="row">
            <label>Fade Time (min)</label>
            <input type="number" min="0" max="240"
              .value=${this._stateNum('schedule_fade_time')}
              @change=${(e: Event) =>
                this._setNumber('schedule_fade_time', +(e.target as HTMLInputElement).value)} />
          </div>`
        : null}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-light-schedule-settings': LightScheduleSettings;
  }
}
