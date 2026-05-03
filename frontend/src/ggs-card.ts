import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { themeVariables } from './styles/theme';
import { discoverDevices, type DiscoveredDevice } from './lib/discovery';
import type { HomeAssistant, LovelaceCardConfig } from './lib/ha-types';
import './components/device-tab';

interface GgsCardConfig extends LovelaceCardConfig {
  device_id?: string;
}

@customElement('ggs-card')
export class GgsCard extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;
  @state() private _config?: GgsCardConfig;
  @state() private _activeEntity?: string;

  static override styles = [
    themeVariables,
    css`
      :host {
        display: block;
        background: var(--ha-card-background, var(--card-background-color, #1c1c1e));
        border-radius: var(--ha-card-border-radius, var(--ggs-radius));
        padding: 16px;
        box-shadow: var(--ha-card-box-shadow, none);
      }
      .tabs {
        display: flex;
        gap: 4px;
        margin-bottom: 14px;
        border-bottom: 1px solid var(--ggs-divider);
        padding-bottom: 8px;
        overflow-x: auto;
      }
      .tab {
        padding: 6px 12px;
        color: var(--ggs-fg-muted);
        font-size: 13px;
        border-radius: var(--ggs-radius-sm);
        cursor: pointer;
        white-space: nowrap;
        background: transparent;
        border: none;
        font: inherit;
      }
      .tab:hover { color: var(--ggs-fg); }
      .tab.active {
        color: var(--ggs-tab-active);
        background: rgba(0, 217, 255, 0.1);
      }
      .empty {
        text-align: center;
        color: var(--ggs-fg-muted);
        padding: 24px 12px;
      }
    `,
  ];

  setConfig(config: GgsCardConfig): void {
    this._config = config ?? {};
  }

  static getStubConfig(): GgsCardConfig {
    return { type: 'custom:ggs-card' };
  }

  getCardSize(): number {
    return 6;
  }

  private _devices(): DiscoveredDevice[] {
    if (!this.hass) return [];
    return discoverDevices(this.hass, this._config?.device_id);
  }

  private _activeDevice(devices: DiscoveredDevice[]): DiscoveredDevice | undefined {
    if (!devices.length) return undefined;
    if (this._activeEntity) {
      const m = devices.find((d) => d.entity === this._activeEntity);
      if (m) return m;
    }
    return devices[0];
  }

  override render() {
    if (!this.hass) return nothing;
    const devices = this._devices();

    if (this._config?.device_id && devices.length === 0) {
      return html`<div class="empty">
        Device '${this._config.device_id}' not found in this Home Assistant.
      </div>`;
    }

    if (devices.length === 0) {
      return html`<div class="empty">
        No GGS devices found. Make sure the SpiderBridge addon is running and
        the controller has been discovered.
      </div>`;
    }

    const active = this._activeDevice(devices)!;
    const speedMax = active.entity === 'fan.ggs_fan_exhaust' ? 100 : 10;

    return html`
      <div class="tabs" role="tablist">
        ${devices.map(
          (d) => html`<button
            class=${'tab' + (d.entity === active.entity ? ' active' : '')}
            role="tab"
            aria-selected=${d.entity === active.entity}
            @click=${() => (this._activeEntity = d.entity)}>
            ${d.name}
          </button>`,
        )}
      </div>
      <ggs-device-tab
        .hass=${this.hass}
        .entity=${active.entity}
        .deviceType=${active.type}
        .extras=${active.extras}
        .speedMax=${speedMax}></ggs-device-tab>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-card': GgsCard;
  }
  interface Window {
    customCards?: Array<{
      type: string;
      name: string;
      description: string;
    }>;
  }
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'ggs-card',
  name: 'Spider Farmer GGS',
  description: 'Control the SpiderBridge GGS controller — light + fan + settings.',
});
