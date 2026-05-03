import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';
import { LIGHT_MODES, FAN_PRESET_MODES } from '../lib/modes';
import type { HomeAssistant, HassEntity } from '../lib/ha-types';
import type { DeviceType } from '../lib/discovery';
import './mode-dropdown';
import './settings-panel';

@customElement('ggs-device-tab')
export class DeviceTab extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: String }) entity = '';
  @property({ type: String }) deviceType: DeviceType = 'light';
  @property({ attribute: false }) extras: Record<string, string> = {};
  @property({ type: Number }) speedMax = 10;

  static override styles = [
    themeVariables,
    css`
      :host { display: block; }
      .header {
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-bottom: var(--ggs-spacing);
      }
      .name { font-size: 18px; font-weight: 600; color: var(--ggs-fg); }
      .sub { color: var(--ggs-fg-muted); font-size: 13px; }
      .slider-row {
        display: flex; align-items: center; gap: var(--ggs-spacing);
        background: var(--ggs-bg); border-radius: var(--ggs-radius);
        padding: var(--ggs-spacing); margin-bottom: var(--ggs-spacing);
      }
      input[type="range"] { flex: 1; accent-color: var(--accent); }
      .value {
        min-width: 56px; text-align: right;
        color: var(--ggs-fg); font-variant-numeric: tabular-nums;
      }
      .mode-row {
        margin-bottom: var(--ggs-spacing);
      }
      .label {
        font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
        color: var(--ggs-fg-muted); margin-bottom: 4px;
      }
      .temp-protection {
        margin-top: var(--ggs-spacing);
        background: var(--ggs-bg); border-radius: var(--ggs-radius);
        padding: var(--ggs-spacing);
      }
      .temp-protection h3 {
        margin: 0 0 var(--ggs-spacing) 0; font-size: 14px; font-weight: 600;
      }
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
        background: var(--ggs-divider); color: var(--ggs-fg);
        border: 1px solid transparent; border-radius: var(--ggs-radius-sm);
        padding: 6px 10px; text-align: right; width: 100px; font: inherit;
      }
    `,
  ];

  private get _state(): HassEntity | undefined {
    return this.hass?.states[this.entity];
  }

  private get _accent(): string {
    return this.deviceType === 'light' ? 'var(--ggs-light-accent)' : 'var(--ggs-fan-accent)';
  }

  private get _modeOptions(): string[] {
    return this.deviceType === 'light' ? [...LIGHT_MODES] : [...FAN_PRESET_MODES];
  }

  private get _currentMode(): string {
    const s = this._state;
    if (!s) return '';
    if (this.deviceType === 'light') {
      return (s.attributes?.effect as string) ?? 'Manual';
    }
    return (s.attributes?.preset_mode as string) ?? 'Manual';
  }

  private get _level(): number {
    const s = this._state;
    if (!s) return 0;
    if (this.deviceType === 'light') {
      const b = (s.attributes?.brightness as number) ?? 0;
      return Math.round((b / 255) * 100);
    }
    return (s.attributes?.percentage as number) ?? 0;
  }

  private get _onOff(): string {
    return this._state?.state === 'on' ? 'ON' : 'OFF';
  }

  private _onSliderInput = (e: Event) => {
    const value = +(e.target as HTMLInputElement).value;
    if (this.deviceType === 'light') {
      this.hass.callService('light', 'turn_on', {
        entity_id: this.entity,
        brightness_pct: value,
      });
    } else {
      this.hass.callService('fan', 'set_percentage', {
        entity_id: this.entity,
        percentage: value,
      });
    }
  };

  private _onModeChange = (e: CustomEvent<string>) => {
    const mode = e.detail;
    if (this.deviceType === 'light') {
      this.hass.callService('light', 'turn_on', { entity_id: this.entity, effect: mode });
    } else {
      this.hass.callService('fan', 'set_preset_mode', {
        entity_id: this.entity,
        preset_mode: mode,
      });
    }
  };

  private _setNum(slot: string, value: number) {
    const id = this.extras[slot];
    if (!id) return;
    this.hass.callService('number', 'set_value', { entity_id: id, value });
  }

  private _stateOf(slot: string): string {
    const id = this.extras[slot];
    return id ? (this.hass.states[id]?.state ?? '') : '';
  }

  private _renderTempProtection() {
    if (this.deviceType !== 'light') return null;
    if (!this.extras.schedule_dim_threshold && !this.extras.schedule_off_threshold) {
      return null;
    }
    return html`
      <div class="temp-protection">
        <h3>Temperature Protection</h3>
        ${this.extras.schedule_dim_threshold
          ? html`<div class="row">
              <label>Dim Threshold (°C)</label>
              <input type="number" min="0" max="50" step="0.1"
                .value=${this._stateOf('schedule_dim_threshold')}
                @change=${(e: Event) =>
                  this._setNum('schedule_dim_threshold',
                    +(e.target as HTMLInputElement).value)} />
            </div>`
          : null}
        ${this.extras.schedule_off_threshold
          ? html`<div class="row">
              <label>Off Threshold (°C)</label>
              <input type="number" min="0" max="50" step="0.1"
                .value=${this._stateOf('schedule_off_threshold')}
                @change=${(e: Event) =>
                  this._setNum('schedule_off_threshold',
                    +(e.target as HTMLInputElement).value)} />
            </div>`
          : null}
      </div>
    `;
  }

  override render() {
    if (!this._state) {
      return html`<div class="sub">Waiting for ${this.entity}…</div>`;
    }
    const name = this._state.attributes?.friendly_name ?? this.entity;
    const unit = this.deviceType === 'light' ? '%' : '%';
    return html`
      <style>:host { --accent: ${this._accent}; }</style>
      <div class="header">
        <div class="name">${name}</div>
        <div class="sub">${this._onOff} · ${this._currentMode}</div>
      </div>
      <div class="slider-row">
        <input type="range" min="0" max="100" step="1"
          .value=${String(this._level)}
          @change=${this._onSliderInput} />
        <div class="value">${this._level}${unit}</div>
      </div>
      <div class="mode-row">
        <div class="label">Mode</div>
        <ggs-mode-dropdown
          .value=${this._currentMode}
          .options=${this._modeOptions}
          @mode-change=${this._onModeChange}></ggs-mode-dropdown>
      </div>
      <ggs-settings-panel
        .hass=${this.hass}
        .deviceType=${this.deviceType}
        .mode=${this._currentMode}
        .extras=${this.extras}
        .speedMax=${this.speedMax}></ggs-settings-panel>
      ${this._renderTempProtection()}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-device-tab': DeviceTab;
  }
}
