import { css } from 'lit';

/**
 * Hybrid theme: HA's CSS variables for backgrounds + text (so user themes
 * propagate), plus a set of accent colors that give the GGS card its own
 * recognizable identity (cyan for active tabs, orange for light slider,
 * blue for fan slider).
 */
export const themeVariables = css`
  :host {
    --ggs-bg: var(--card-background-color, #1c1c1e);
    --ggs-fg: var(--primary-text-color, #ffffff);
    --ggs-fg-muted: var(--secondary-text-color, #8e8e93);
    --ggs-divider: var(--divider-color, #2c2c2e);
    --ggs-tab-active: #00d9ff;
    --ggs-light-accent: #ff9f0a;
    --ggs-fan-accent: #4a90e2;
    --ggs-radius: 12px;
    --ggs-radius-sm: 6px;
    --ggs-spacing: 12px;
    --ggs-spacing-sm: 6px;
    color: var(--ggs-fg);
    font-family: var(--paper-font-body1_-_font-family, sans-serif);
  }
`;
