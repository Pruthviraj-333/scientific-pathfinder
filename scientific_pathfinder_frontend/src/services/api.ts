/**
 * Centralized API service layer.
 * All API calls go through here for consistent error handling and typing.
 */

import config from '../config';

/** Standard API response envelope from the backend */
interface APIResponse<T = any> {
  success: boolean;
  data: T | null;
  error: string | null;
  timestamp: string;
}

class APIError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = config.api(path);
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  const body: APIResponse<T> = await response.json();

  if (!response.ok || !body.success) {
    throw new APIError(response.status, body.error || 'Unknown error');
  }

  return body.data as T;
}

/** Start a new research session */
export async function startResearch(topic: string, maxPapers: number) {
  return request<{ session_id: string; status: string; message: string }>(
    '/research/start',
    { method: 'POST', body: JSON.stringify({ topic, max_papers: maxPapers }) }
  );
}

/** Get research session status */
export async function getResearchStatus(sessionId: string) {
  return request(`/research/${sessionId}`);
}

/** Get graph visualization data */
export async function getGraphData(sessionId: string) {
  return request(`/graph/${sessionId}`);
}

/** Clear the Neo4j graph */
export async function clearGraph() {
  return request('/graph/clear', { method: 'POST' });
}

/** Check API health */
export async function checkHealth() {
  return request('/health');
}

export { APIError };
export default { startResearch, getResearchStatus, getGraphData, clearGraph, checkHealth };
