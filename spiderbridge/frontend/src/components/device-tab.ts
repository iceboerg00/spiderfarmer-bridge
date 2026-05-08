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
  /** Last non-empty effect/preset_mode we observed. Used as fallback
   *  when HA briefly clears the attribute mid-transition (e.g. schedule
   *  off-phase) so the dropdown doesn't flash to empty + the settings
   *  panel doesn't render the "Unknown mode" placeholder. */
  @state() private _stickyMode = '';

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
      /* Save button — same pill silhouette as ggs-switch (24px tall,
         pill-shaped, accent fill), only with text instead of a toggle
         thumb so it reads as a one-shot action. */
      .save {
        height: 24px;
        padding: 0 14px;
        border-radius: 999px;
        border: none;
        background: var(--accent, var(--ggs-fan-accent));
        color: #ffffff;
        font: inherit;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.4px;
        text-transform: uppercase;
        cursor: pointer;
        transition: opacity 0.15s ease;
      }
      .save:hover { opacity: 0.85; }
      .save:active { opacity: 0.7; }
      .save:focus-visible {
        outline: none;
        box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.4);
      }
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
    const attr = this.deviceType === 'light'
      ? (s.attributes?.effect as string | undefined)
      : (s.attributes?.preset_mode as string | undefined);
    // Fall back to the last observed non-empty mode when HA momentarily
    // clears the attribute (e.g. schedule off-phase). Without the
    // sticky cache the dropdown empties and the settings panel renders
    // the "Unknown mode" placeholder for a few seconds.
    return attr || this._stickyMode;
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
    // Toggle ON forces Manual mode so subsequent settings edits stick;
    // toggle OFF just turns off without a Manual flip — firing
    // turn_on {effect: Manual} before turn_off would clobber the
    // bridge's last_nonzero_level cache (no brightness in the cmd
    // means it falls back to a default), losing the user's previous
    // brightness for the next ON. Manual will be re-asserted whenever
    // the user actually changes something via slider or dropdown.
    const turningOn = this._onOff !== 'ON';
    if (this.deviceType === 'light') {
      if (turningOn) {
        this.hass.callService('light', 'turn_on', {
          entity_id: this.entity,
          effect: 'Manual',
        });
      } else {
        this.hass.callService('light', 'turn_off', { entity_id: this.entity });
      }
    } else {
      this.hass.callService('fan', 'toggle', { entity_id: this.entity });
      // set_preset_mode is independent of on/off, so it's safe both
      // ways. Skip on turn-OFF for symmetry with the light path so the
      // controller's cached schedule/cycle isn't silently overwritten.
      if (turningOn) {
        this.hass.callService('fan', 'set_preset_mode', {
          entity_id: this.entity,
          preset_mode: 'Manual',
        });
      }
    }
  };

  /** Fires continuously while dragging — keep state in sync, do NOT call HA. */
  private _onSliderDrag = (e: Event) => {
    this._draggingLevel = +(e.target as HTMLInputElement).value;
  };

  /** Fires on release — commit to HA and pin the displayed value
   *  until HA echoes back the matching state, otherwise the slider
   *  briefly snaps to the stale `_level` between release and the
   *  state update. updated() clears _draggingLevel once they match.
   */
  private _onSliderCommit = (e: Event) => {
    const value = +(e.target as HTMLInputElement).value;
    this._draggingLevel = value;
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

  private _onSaveMode = () => {
    // Re-fire the current mode to push a fresh setConfigField with
    // modeType — the SF controller commits any sub-field edits (schedule
    // times, cycle intervals, etc.) made since the last mode change.
    // Without this, per-field writes are sometimes treated as preview
    // state and never take effect until the user presses save in the
    // SF App.
    const mode = this._currentMode;
    if (!mode) return;
    if (this.deviceType === 'light') {
      this.hass.callService('light', 'turn_on', {
        entity_id: this.entity,
        effect: mode,
      });
    } else {
      this.hass.callService('fan', 'set_preset_mode', {
        entity_id: this.entity,
        preset_mode: mode,
      });
    }
  };

  private _setNum(slot: string, e: Event) {
    const id = this.extras[slot];
    if (!id) return;
    const input = e.target as HTMLInputElement;
    const raw = input.value.trim();
    // Skip empty input + NaN — sending 0 silently would surprise the
    // user. The HTML min/max attributes are advisory, so clamp here.
    if (raw === '') return;
    const n = Number(raw);
    if (!Number.isFinite(n)) return;
    const min = input.min !== '' ? Number(input.min) : -Infinity;
    const max = input.max !== '' ? Number(input.max) : Infinity;
    const value = Math.max(min, Math.min(max, n));
    this.hass.callService('number', 'set_value', { entity_id: id, value });
  }

  private _stateOf(slot: string): string {
    const id = this.extras[slot];
    return id ? (this.hass.states[id]?.state ?? '') : '';
  }

  override updated() {
    this.style.setProperty('--accent', this._accent);
    // Clear the post-commit override once HA's state catches up.
    // _onSliderCommit pins _draggingLevel to the committed value to
    // bridge the gap between user release and HA's echoed state.
    if (this._draggingLevel !== null && this._level === this._draggingLevel) {
      this._draggingLevel = null;
    }
    // Capture the latest non-empty mode for the sticky fallback.
    const s = this._state;
    if (s) {
      const live = this.deviceType === 'light'
        ? (s.attributes?.effect as string | undefined)
        : (s.attributes?.preset_mode as string | undefined);
      if (live && live !== this._stickyMode) {
        this._stickyMode = live;
      }
    }
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
                @change=${(e: Event) => this._setNum('schedule_dim_threshold', e)} />
            </div>`
          : null}
        ${this.extras.schedule_off_threshold
          ? html`<div class="row">
              <label>Off Threshold (°C)</label>
              <input type="number" min="0" max="50" step="0.1"
                .value=${this._stateOf('schedule_off_threshold')}
                @change=${(e: Event) => this._setNum('schedule_off_threshold', e)} />
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
    const rawDisplayLevel = this._draggingLevel ?? this._level;
    // Clamp to [sliderMin, 100] before render — HA can briefly report
    // a value below sliderMin (e.g. brightness=0 mid-fade) and the
    // <input type=range> ignores .value below its min, but our fillPct
    // calc would produce a negative percent for one frame.
    const displayLevel = Math.max(this.sliderMin, Math.min(100, rawDisplayLevel));
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
        <button class="save" @click=${this._onSaveMode}
          title="Re-apply current mode to commit pending edits">Save</button>
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
