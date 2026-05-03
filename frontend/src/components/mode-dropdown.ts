import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { themeVariables } from '../styles/theme';

@customElement('ggs-mode-dropdown')
export class ModeDropdown extends LitElement {
  @property({ type: String }) value = '';
  @property({ type: Array }) options: string[] = [];

  static override styles = [
    themeVariables,
    css`
      select {
        width: 100%;
        background: var(--ggs-divider);
        color: var(--ggs-fg);
        border: 1px solid transparent;
        border-radius: var(--ggs-radius-sm);
        padding: 10px 12px;
        font: inherit;
        appearance: none;
        cursor: pointer;
      }
      select:focus {
        outline: none;
        border-color: var(--ggs-tab-active);
      }
      .wrapper {
        position: relative;
      }
      .wrapper::after {
        content: '▾';
        position: absolute;
        right: 12px;
        top: 50%;
        transform: translateY(-50%);
        color: var(--ggs-tab-active);
        pointer-events: none;
      }
    `,
  ];

  private _onChange = (e: Event) => {
    const target = e.target as HTMLSelectElement;
    this.dispatchEvent(
      new CustomEvent<string>('mode-change', {
        detail: target.value,
        bubbles: true,
        composed: true,
      }),
    );
  };

  override render() {
    const inOptions = this.options.includes(this.value);
    return html`
      <div class="wrapper">
        <select @change=${this._onChange}>
          ${!inOptions && this.value
            ? html`<option value=${this.value} selected>${this.value}</option>`
            : null}
          ${this.options.map(
            (opt) =>
              html`<option value=${opt} ?selected=${opt === this.value}>${opt}</option>`,
          )}
        </select>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'ggs-mode-dropdown': ModeDropdown;
  }
}
