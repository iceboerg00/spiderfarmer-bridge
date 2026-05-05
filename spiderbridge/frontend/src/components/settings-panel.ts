import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';
import { isEnvironmentMode } from '../lib/modes';
import type { HomeAssistant } from '../lib/ha-types';
import type { DeviceType } from '../lib/discovery';

import '../settings/light-schedule';
import '../settings/light-ppfd';
import '../settings/fan-schedule';
import '../settings/fan-cycle';
import '../settings/fan-environment';
import '../settings/fan-manual';

@customElement('ggs-settings-panel')
export class SettingsPanel extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: String }) deviceType: DeviceType = 'light';
  @property({ type: String }) mode = '';
  @property({ attribute: false }) extras: Record<string, string> = {};
  @property({ type: Number }) speedMax = 10;

  static override styles = [
    themeVariables,
    css`
      :host {
        display: block;
        background: var(--ggs-bg);
        border-radius: var(--ggs-radius);
        padding: var(--ggs-spacing);
        margin-top: var(--ggs-spacing);
      }
      .placeholder {
        color: var(--ggs-fg-muted);
        font-style: italic;
        text-align: center;
        padding: 16px 0;
      }
      .save-row {
        display: flex;
        justify-content: flex-end;
        margin-top: var(--ggs-spacing);
        padding-top: var(--ggs-spacing);
        border-top: 1px solid var(--ggs-divider);
      }
      .save {
        background: var(--accent, var(--ggs-tab-active));
        color: #ffffff;
        border: none;
        border-radius: var(--ggs-radius-sm);
        padding: 10px 20px;
        font: inherit;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.15s ease;
      }
      .save:hover { opacity: 0.85; }
      .save:active { opacity: 0.7; }
    `,
  ];

  private _onSave = () => {
    // Bubble up so device-tab can re-apply the current mode. Some
    // controllers treat per-field setConfigField writes as preview-only
    // and only commit when a full block (with modeType) lands — this
    // mirrors the "save" button in the SF App.
    this.dispatchEvent(
      new CustomEvent('save-mode', { bubbles: true, composed: true }),
    );
  };

  private _renderBody() {
    if (this.mode === 'Manual') {
      // Light has no settings in Manual mode. Fan exposes oscillation +
      // natural_wind only when those entities are actually present
      // (Fan Circulation has both; Fan Exhaust/blower has neither, so
      // the panel falls back to the placeholder).
      const hasFanManualExtras =
        this.deviceType === 'fan' &&
        Object.keys(this.extras).some(
          (k) => k.endsWith('_oscillation') || k.endsWith('_natural_wind'),
        );
      if (hasFanManualExtras) {
        return html`<ggs-fan-manual-settings
          .hass=${this.hass} .extras=${this.extras}></ggs-fan-manual-settings>`;
      }
      return html`<div class="placeholder">No mode-specific settings.</div>`;
    }

    if (this.deviceType === 'light') {
      if (this.mode === 'Schedule') {
        return html`<ggs-light-schedule-settings
          .hass=${this.hass} .extras=${this.extras}></ggs-light-schedule-settings>`;
      }
      if (this.mode === 'PPFD') {
        return html`<ggs-light-ppfd-settings
          .hass=${this.hass} .extras=${this.extras}></ggs-light-ppfd-settings>`;
      }
    }

    if (this.deviceType === 'fan') {
      if (this.mode === 'Schedule') {
        return html`<ggs-fan-schedule-settings
          .hass=${this.hass} .extras=${this.extras}
          .speedMax=${this.speedMax}></ggs-fan-schedule-settings>`;
      }
      if (this.mode === 'Cycle') {
        return html`<ggs-fan-cycle-settings
          .hass=${this.hass} .extras=${this.extras}
          .speedMax=${this.speedMax}></ggs-fan-cycle-settings>`;
      }
      if (isEnvironmentMode(this.mode)) {
        return html`<ggs-fan-environment-settings
          .hass=${this.hass} .extras=${this.extras}
          .speedMax=${this.speedMax}></ggs-fan-environment-settings>`;
      }
    }

    return html`<div class="placeholder">Unknown mode: ${this.mode}</div>`;
  }

  override render() {
    // Save button stays visible for every mode (incl. Manual) — pressing
    // it re-applies the current mode, which the SF controller treats as
    // a commit of any pending sub-field edits (schedule times, cycle
    // intervals, etc.).
    const body = this._renderBody();
    return html`
      <div class="body">${body}</div>
      <div class="save-row">
        <button class="save" @click=${this._onSave}>Save</button>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-settings-panel': SettingsPanel;
  }
}
