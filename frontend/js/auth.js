import { apiGet, apiPost } from './api.js';

export async function checkAuth() {
  try {
    return await apiGet('/auth/me');
  } catch {
    return null;
  }
}

export function redirectToLogin() {
  window.location.href = '/api/auth/login';
}

export async function logout() {
  await apiPost('/auth/logout');
  window.location.reload();
}
