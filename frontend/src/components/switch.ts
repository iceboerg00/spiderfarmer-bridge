import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';

/**
 * Material-style track + thumb toggle, used for the per-device on/off
 * button on `<ggs-device-tab>` and for natural_wind / boolean settings.
 *
 * Reads its colour from the CSS custom property `--accent`. Parent
 * components set that to the device's accent (orange for light, blue
 * for fan) — `<ggs-fan-*-settings>` defaults to fan-accent.
 *
 * Emits a `change` event with `detail = !checked` on click. Consumers
 * read `e.detail` as the new desired state.
 */
@customElement('ggs-switch')
export class GgsSwitch extends LitElement {
  @property({ type: Boolean }) checked = false;
  // 'label' rather than 'ariaLabel' because the latter collides with
  // the inherited Element.ariaLabel reflected property.
  @property({ type: String }) label = '';

  static override styles = [
    themeVariables,
    css`
      :host {
        display: inline-block;
        --switch-accent: var(--accent, var(--ggs-fan-accent));
      }
      button {
        --track-w: 44px;
        --track-h: 24px;
        --thumb: 18px;
        position: relative;
        display: block;
        width: var(--track-w);
        height: var(--track-h);
        border-radius: 999px;
        border: none;
        padding: 0;
        cursor: pointer;
        background: var(--ggs-divider);
        transition: background 0.2s;
        outline: none;
      }
      button::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 3px;
        width: var(--thumb);
        height: var(--thumb);
        border-radius: 50%;
        background: #fff;
        transform: translateY(-50%);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        transition: left 0.2s;
      }
      button.on { background: var(--switch-accent); }
      button.on::after { left: calc(var(--track-w) - var(--thumb) - 3px); }
      button:focus-visible {
        box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.4);
      }
    `,
  ];

  private _onClick = () => {
    this.dispatchEvent(
      new CustomEvent<boolean>('change', {
        detail: !this.checked,
        bubbles: true,
        composed: true,
      }),
    );
  };

  override render() {
    return html`<button
      class=${this.checked ? 'on' : ''}
      role="switch"
      aria-checked=${this.checked}
      aria-label=${this.label}
      @click=${this._onClick}></button>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-switch': GgsSwitch;
  }
}
