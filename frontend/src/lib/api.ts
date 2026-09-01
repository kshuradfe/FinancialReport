import type {
  JobConfig,
  JobSummary,
  Meta,
  RowsPage,
  SearchItem,
  UniverseItem,
} from './types';

// Vite proxies /api to the FastAPI process in dev; same-origin when served
// from the built bundle.
const BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    ...init,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  meta: () => request<Meta>('/meta'),

  search: (q: string, signal?: AbortSignal) =>
    request<{ items: SearchItem[] }>(`/search?q=${encodeURIComponent(q)}`, { signal }),

  previewUniverse: (body: Partial<JobConfig>, signal?: AbortSignal) =>
    request<{ items: UniverseItem[]; totals: Record<string, number>; count: number }>(
      '/universe/preview',
      { method: 'POST', body: JSON.stringify(body), signal },
    ),

  createJob: (config: JobConfig) =>
    request<JobSummary>('/jobs', { method: 'POST', body: JSON.stringify(config) }),

  job: (id: string) => request<JobSummary & { columns: string[] }>(`/jobs/${id}`),

  cancelJob: (id: string) => request<{ ok: boolean }>(`/jobs/${id}/cancel`, { method: 'POST' }),

  rows: (
    id: string,
    opts: { offset?: number; limit?: number; sort?: string; desc?: boolean; q?: string } = {},
  ) => {
    const p = new URLSearchParams();
    if (opts.offset) p.set('offset', String(opts.offset));
    if (opts.limit) p.set('limit', String(opts.limit));
    if (opts.sort) p.set('sort', opts.sort);
    if (opts.sort) p.set('desc', String(opts.desc ?? true));
    if (opts.q) p.set('q', opts.q);
    return request<RowsPage>(`/jobs/${id}/rows?${p.toString()}`);
  },

  exportUrl: (id: string, format: 'csv' | 'xlsx' | 'json', lang: 'zh' | 'en' | 'key') =>
    `${BASE}/jobs/${id}/export?format=${format}&lang=${lang}`,

  eventsUrl: (id: string) => `${BASE}/jobs/${id}/events`,
};
