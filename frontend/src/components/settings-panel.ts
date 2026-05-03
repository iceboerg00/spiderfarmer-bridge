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
    `,
  ];

  override render() {
    if (this.mode === 'Manual') {
      // Light has no settings in Manual mode. Fan still exposes the
      // hardware-level controls (oscillation + natural_wind) that don't
      // belong to a specific mode.
      if (this.deviceType === 'fan') {
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
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-settings-panel': SettingsPanel;
  }
}
