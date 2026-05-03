import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { themeVariables } from './styles/theme';
import { discoverDevices, type DiscoveredDevice } from './lib/discovery';
import type { HomeAssistant, LovelaceCardConfig } from './lib/ha-types';
import './components/device-tab';

interface SliderMinConfig {
  light?: number;
  fan_circulation?: number;
  fan_exhaust?: number;
}

interface LayoutOptionsConfig {
  grid_columns?: number;
  grid_rows?: number;
  grid_min_columns?: number;
  grid_min_rows?: number;
  grid_max_columns?: number;
  grid_max_rows?: number;
}

interface GgsCardConfig extends LovelaceCardConfig {
  device_id?: string;
  /**
   * Per-device-type minimum value the slider can drag to (0-100).
   * Useful when the controller has a hardware floor (e.g. fan exhaust
   * physically refuses to spin below 25 %, light won't dim below 11 %).
   * Setting it makes the slider start visually at the floor instead of 0.
   */
  slider_min?: SliderMinConfig;
  /**
   * HA section-view layout overrides. Re-declared here so HA's YAML
   * editor type-checks the user's overrides; they're consumed by HA,
   * not by this card directly.
   */
  layout_options?: LayoutOptionsConfig;
}

const SLIDER_MIN_KEY: Record<string, keyof SliderMinConfig> = {
  'light.ggs_light_1': 'light',
  'light.ggs_light_2': 'light',
  'fan.ggs_fan_circulation': 'fan_circulation',
  'fan.ggs_fan_exhaust': 'fan_exhaust',
};

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
        height: 100%;
      }
      ha-card {
        display: flex;
        flex-direction: column;
        height: 100%;
        overflow: hidden;
      }
      .content {
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
        padding: 16px;
        box-sizing: border-box;
      }
      ggs-device-tab {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
      }
      .tabs {
        display: flex;
        gap: 4px;
        margin-bottom: 14px;
        border-bottom: 1px solid var(--ggs-divider);
        padding-bottom: 8px;
        overflow-x: auto;
        flex-shrink: 0;
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

  /**
   * Default YAML inserted into the dashboard when the user adds the card
   * via "+ Add Card". HA shows this to the user, who can adjust before
   * saving. Pre-populating layout_options + slider_min saves the user a
   * round-trip to the docs for the typical SF GGS hardware floors.
   */
  static getStubConfig(): GgsCardConfig {
    return {
      type: 'custom:ggs-card',
      layout_options: {
        grid_columns: 48,
        grid_rows: 12,
      },
      slider_min: {
        light: 11,
        fan_circulation: 10,
        fan_exhaust: 25,
      },
    };
  }

  getCardSize(): number {
    return 6;
  }

  /**
   * HA's section view uses this to know which sizes the card supports
   * when the user drags the resize handle. The keys here are the
   * documented public API (grid_rows/grid_columns + grid_min/max_*),
   * NOT the older `columns`/`rows`/`min_columns`/etc. names — those
   * silently no-op in newer HA versions.
   *
   * No grid_max_* set: HA caps to whatever the section's column-count
   * allows (12 by default, up to 48 in wider sections). Setting our
   * own max here would clamp the card before HA's natural cap.
   */
  getLayoutOptions() {
    return {
      grid_rows: 6,
      grid_columns: 12,
      grid_min_rows: 3,
      grid_min_columns: 4,
    };
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
      return html`<ha-card><div class="empty">
        Device '${this._config.device_id}' not found in this Home Assistant.
      </div></ha-card>`;
    }

    if (devices.length === 0) {
      return html`<ha-card><div class="empty">
        No GGS devices found. Make sure the SpiderBridge addon is running and
        the controller has been discovered.
      </div></ha-card>`;
    }

    const active = this._activeDevice(devices)!;
    const speedMax = active.entity === 'fan.ggs_fan_exhaust' ? 100 : 10;
    const sliderMinKey = SLIDER_MIN_KEY[active.entity];
    const sliderMin =
      (sliderMinKey && this._config?.slider_min?.[sliderMinKey]) ?? 0;

    return html`
      <ha-card>
        <div class="content">
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
            .speedMax=${speedMax}
            .sliderMin=${sliderMin}></ggs-device-tab>
        </div>
      </ha-card>
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
