import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';
import type { HomeAssistant } from '../lib/ha-types';

/**
 * Settings that still apply when the fan is in Manual mode — oscillation
 * level (the head-shake) and the natural-wind program. Speed/standby_speed
 * are intentionally omitted because Manual mode drives the fan from the
 * tab's main slider; standby_speed has no meaning when the fan is always
 * running at the slider value.
 *
 * Each row renders only when the matching aliased entity exists in the
 * extras map (e.g. blower has neither oscillation nor natural_wind, so
 * the panel ends up empty for blower + Manual — the dispatcher falls
 * back to the "no settings" placeholder in that case).
 */
@customElement('ggs-fan-manual-settings')
export class FanManualSettings extends LitElement {
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
      input[type="number"] {
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

  /**
   * Manual-mode controls and the controller's oscillation/natural_wind
   * fields are wired through the same MQTT topics the per-mode panels
   * use — so we look at any of the schedule_/cycle_/environment_ aliases
   * in extras and pick whichever the controller has populated. Because
   * the bridge publishes all aliases simultaneously, schedule_ is a
   * stable choice.
   */
  private _slot(field: 'oscillation' | 'natural_wind'): string | undefined {
    return (
      this.extras[`schedule_${field}`] ??
      this.extras[`cycle_${field}`] ??
      this.extras[`environment_${field}`]
    );
  }

  private _state(slot: string): string {
    return this.hass.states[slot]?.state ?? '';
  }

  private _setNum(slot: string, value: number) {
    this.hass.callService('number', 'set_value', { entity_id: slot, value });
  }

  private _toggleSwitch(slot: string, on: boolean) {
    this.hass.callService('switch', on ? 'turn_on' : 'turn_off', { entity_id: slot });
  }

  override render() {
    const oscEntity = this._slot('oscillation');
    const windEntity = this._slot('natural_wind');
    return html`
      ${oscEntity
        ? html`<div class="row">
            <label>Oscillation (0-10)</label>
            <input type="number" min="0" max="10"
              .value=${this._state(oscEntity)}
              @change=${(e: Event) =>
                this._setNum(oscEntity, +(e.target as HTMLInputElement).value)} />
          </div>`
        : null}
      ${windEntity
        ? html`<div class="row">
            <label>Natural Wind</label>
            <input type="checkbox"
              .checked=${this._state(windEntity) === 'on'}
              @change=${(e: Event) =>
                this._toggleSwitch(windEntity, (e.target as HTMLInputElement).checked)} />
          </div>`
        : null}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-fan-manual-settings': FanManualSettings;
  }
}
