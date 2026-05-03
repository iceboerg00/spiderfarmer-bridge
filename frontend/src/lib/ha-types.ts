// Single import path for HA frontend types — swap the underlying source
// here if custom-card-helpers stops being maintained.
export type { HomeAssistant, LovelaceCardConfig } from 'custom-card-helpers';
export type { HassEntity } from 'home-assistant-js-websocket';
