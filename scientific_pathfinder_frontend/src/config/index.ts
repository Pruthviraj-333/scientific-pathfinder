/**
 * Application configuration.
 * Reads API URLs from environment variables with sensible defaults.
 */

// In Vite, env vars must be prefixed with VITE_ to be exposed to client code.
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Derive WebSocket URL from API URL
function getWsUrl(apiUrl: string): string {
  const url = new URL(apiUrl);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString().replace(/\/$/, '');
}

export const config = {
  /** Base URL for REST API calls */
  apiUrl: API_BASE_URL,

  /** Base URL for WebSocket connections */
  wsUrl: getWsUrl(API_BASE_URL),

  /** API version prefix */
  apiPrefix: '/api/v1',

  /** Full API base (apiUrl + prefix) */
  get apiBase(): string {
    return `${this.apiUrl}${this.apiPrefix}`;
  },

  /** Build a full API URL for a given path */
  api(path: string): string {
    return `${this.apiBase}${path}`;
  },

  /** Build a WebSocket URL for a given path */
  ws(path: string): string {
    return `${this.wsUrl}${path}`;
  },
} as const;

export default config;
