import { apiGet, apiPatch } from './api.js';
import { logout } from './auth.js';

async function loadProfile() {
  const user = await apiGet('/users/me');
  document.getElementById('settings-name').value = user.name || '';
  document.getElementById('settings-known-langs').value =
    Array.isArray(user.known_languages) ? user.known_languages.join(', ') : (user.known_languages || '');
  document.getElementById('settings-target-lang').value = user.target_language || '';
}

async function saveProfile() {
  const status = document.getElementById('settings-status');
  const name = document.getElementById('settings-name').value.trim();
  const knownRaw = document.getElementById('settings-known-langs').value;
  const known_languages = knownRaw.split(',').map(s => s.trim()).filter(Boolean);
  const target_language = document.getElementById('settings-target-lang').value.trim();

  try {
    await apiPatch('/users/me', { name, known_languages, target_language });
    status.textContent = 'saved!';
    status.style.color = 'var(--success)';
  } catch (err) {
    status.textContent = `error: ${err.message}`;
    status.style.color = 'var(--danger)';
  }

  setTimeout(() => { status.textContent = ''; }, 3000);
}

export async function initSettings() {
  try {
    await loadProfile();
  } catch { /* will show empty form */ }

  document.getElementById('settings-save').onclick = saveProfile;
  document.getElementById('logout-btn').onclick = logout;
}
