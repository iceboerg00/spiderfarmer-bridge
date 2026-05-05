import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';
import { LIGHT_MODES, FAN_PRESET_MODES } from '../lib/modes';
import type { HomeAssistant, HassEntity } from '../lib/ha-types';
import type { DeviceType } from '../lib/discovery';
import './mode-dropdown';
import './settings-panel';
import './switch';

@customElement('ggs-device-tab')
export class DeviceTab extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: String }) entity = '';
  @property({ type: String }) deviceType: DeviceType = 'light';
  @property({ attribute: false }) extras: Record<string, string> = {};
  @property({ type: Number }) speedMax = 10;
  @property({ type: Number }) sliderMin = 0;
  /** Live value while the user drags the slider; null when not dragging. */
  @state() private _draggingLevel: number | null = null;

  static override styles = [
    themeVariables,
    css`
      :host { display: block; }
      .header {
        display: flex;
        align-items: center;
        gap: var(--ggs-spacing);
        margin-bottom: var(--ggs-spacing);
      }
      .header-text {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
        min-width: 0;
      }
      .name { font-size: 18px; font-weight: 600; color: var(--ggs-fg); }
      .sub { color: var(--ggs-fg-muted); font-size: 13px; }
      .slider-row {
        display: flex; align-items: center; gap: var(--ggs-spacing);
        background: var(--ggs-bg); border-radius: var(--ggs-radius);
        padding: 18px var(--ggs-spacing);
        margin-bottom: var(--ggs-spacing);
      }
      .slider {
        flex: 1;
        -webkit-appearance: none;
        appearance: none;
        height: 28px;
        background: transparent;
        cursor: pointer;
        margin: 0;
        padding: 0;
        outline: none;
      }
      /* WebKit / Chromium / Edge / Safari */
      .slider::-webkit-slider-runnable-track {
        height: 8px;
        border-radius: 999px;
        background:
          linear-gradient(
            to right,
            var(--accent) 0%,
            var(--accent) calc(var(--ggs-fill, 0) * 1%),
            var(--ggs-divider) calc(var(--ggs-fill, 0) * 1%),
            var(--ggs-divider) 100%
          );
      }
      .slider::-webkit-slider-thumb {
        -webkit-appearance: none;
        appearance: none;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: #ffffff;
        border: 3px solid var(--accent);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
        margin-top: -7px;
        transition: transform 0.15s ease;
      }
      .slider:hover::-webkit-slider-thumb { transform: scale(1.1); }
      .slider:active::-webkit-slider-thumb { transform: scale(1.18); }
      /* Firefox */
      .slider::-moz-range-track {
        height: 8px;
        border-radius: 999px;
        background: var(--ggs-divider);
      }
      .slider::-moz-range-progress {
        height: 8px;
        border-radius: 999px;
        background: var(--accent);
      }
      .slider::-moz-range-thumb {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: #ffffff;
        border: 3px solid var(--accent);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
        transition: transform 0.15s ease;
      }
      .slider:hover::-moz-range-thumb { transform: scale(1.1); }
      .slider:active::-moz-range-thumb { transform: scale(1.18); }
      .value {
        min-width: 56px; text-align: right;
        color: var(--ggs-fg); font-variant-numeric: tabular-nums;
        font-size: 16px; font-weight: 600;
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
    // Don't fall back to 'Manual' — when the bridge omits effect/preset_mode
    // (e.g. during a schedule off-phase before the modeType cache is seeded)
    // we'd render the Manual placeholder and hide all schedule settings.
    // An empty string surfaces 'Unknown mode' in the settings panel instead,
    // which preserves the user's ability to re-pick a mode from the dropdown.
    const attr = this.deviceType === 'light'
      ? (s.attributes?.effect as string | undefined)
      : (s.attributes?.preset_mode as string | undefined);
    return attr ?? '';
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

  private _onToggle = () => {
    // Mirror the SF App: any manual toggle flips the device into Manual
    // mode. Without forcing Manual here the card keeps showing the
    // previous mode (e.g. Schedule) while the controller has already
    // switched, so subsequent edits in the Schedule sub-panel silently
    // no-op because the device is no longer in that mode.
    const turningOn = this._onOff !== 'ON';
    if (this.deviceType === 'light') {
      if (turningOn) {
        // Combine on + Manual into a single command so the bridge
        // publishes {state: ON, effect: Manual} in one frame.
        this.hass.callService('light', 'turn_on', {
          entity_id: this.entity,
          effect: 'Manual',
        });
      } else {
        // Set Manual first while still on, then turn off — brief
        // overlap is fine, the schedule was about to stop driving
        // brightness anyway.
        this.hass.callService('light', 'turn_on', {
          entity_id: this.entity,
          effect: 'Manual',
        });
        this.hass.callService('light', 'turn_off', { entity_id: this.entity });
      }
    } else {
      this.hass.callService('fan', 'toggle', { entity_id: this.entity });
      // set_preset_mode is independent of on/off, so we can fire it
      // unconditionally without re-toggling state.
      this.hass.callService('fan', 'set_preset_mode', {
        entity_id: this.entity,
        preset_mode: 'Manual',
      });
    }
  };

  /** Fires continuously while dragging — keep state in sync, do NOT call HA. */
  private _onSliderDrag = (e: Event) => {
    this._draggingLevel = +(e.target as HTMLInputElement).value;
  };

  /** Fires on release — commit to HA and clear the draft. */
  private _onSliderCommit = (e: Event) => {
    const value = +(e.target as HTMLInputElement).value;
    this._draggingLevel = null;
    // Same SF App behavior as _onToggle: any manual brightness/speed
    // change kicks the device out of Schedule/Cycle/Environment into
    // Manual. Force Manual here so the card stays in sync.
    if (this.deviceType === 'light') {
      this.hass.callService('light', 'turn_on', {
        entity_id: this.entity,
        brightness_pct: value,
        effect: 'Manual',
      });
    } else {
      this.hass.callService('fan', 'set_percentage', {
        entity_id: this.entity,
        percentage: value,
      });
      this.hass.callService('fan', 'set_preset_mode', {
        entity_id: this.entity,
        preset_mode: 'Manual',
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

  override updated() {
    this.style.setProperty('--accent', this._accent);
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
    const unit = '%';
    const displayLevel = this._draggingLevel ?? this._level;
    // Light is smooth (0-100); fans have N speed levels mapped onto 0-100 %
    // so the slider should snap to whole levels — step = 100 / speedMax.
    // Fan Circulation (10 levels) → step 10, Fan Exhaust (100 levels) → step 1.
    const sliderStep = this.deviceType === 'light'
      ? 1
      : Math.max(1, Math.round(100 / this.speedMax));
    // Track fill is the thumb's position as a fraction of the visible
    // range (sliderMin → 100), not the raw value — otherwise a sliderMin
    // of 25 would draw the fill past the thumb.
    const range = Math.max(1, 100 - this.sliderMin);
    const fillPct = Math.max(
      0,
      Math.min(100, ((displayLevel - this.sliderMin) / range) * 100),
    );
    return html`
      <div class="header">
        <div class="header-text">
          <div class="name">${name}</div>
          <div class="sub">${this._onOff} · ${this._currentMode}</div>
        </div>
        <ggs-switch
          .checked=${this._onOff === 'ON'}
          .label=${'Toggle ' + name}
          @change=${this._onToggle}></ggs-switch>
      </div>
      <div class="slider-row">
        <input type="range" class="slider"
          min=${this.sliderMin} max="100" step=${sliderStep}
          .value=${String(displayLevel)}
          style="--ggs-fill: ${fillPct}"
          @input=${this._onSliderDrag}
          @change=${this._onSliderCommit} />
        <div class="value">${displayLevel}${unit}</div>
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
