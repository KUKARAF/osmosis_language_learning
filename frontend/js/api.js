/**
 * Fetch wrapper for /api endpoints.
 * Handles credentials, JSON parsing, and 401 → login redirect.
 */

export async function apiFetch(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    credentials: 'same-origin',
    ...opts,
    headers: {
      ...(opts.body && !(opts.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...opts.headers,
    },
  });

  if (res.status === 401) {
    window.location.href = '/api/auth/login';
    return;
  }

  if (opts.raw) return res;

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }

  if (res.status === 204) return null;
  return res.json();
}

export function apiGet(path) {
  return apiFetch(path);
}

export function apiPost(path, body) {
  return apiFetch(path, {
    method: 'POST',
    body: body != null ? JSON.stringify(body) : undefined,
  });
}

export function apiPatch(path, body) {
  return apiFetch(path, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}
