import { apiGet, apiPost } from './api.js';

let notifications = [];

function render() {
  const list = document.getElementById('notif-list');
  const badge = document.getElementById('notif-count');
  const unread = notifications.filter(n => !n.read);

  if (unread.length > 0) {
    badge.textContent = unread.length;
    badge.hidden = false;
  } else {
    badge.hidden = true;
  }

  if (notifications.length === 0) {
    list.innerHTML = '<div class="notif-item" style="color:var(--text-dim)">no notifications</div>';
    return;
  }

  list.innerHTML = notifications.map(n => `
    <div class="notif-item ${n.read ? '' : 'unread'}" data-id="${n.id}">
      <div class="notif-item-title">${esc(n.title)}</div>
      ${n.body ? `<div class="notif-item-body">${esc(n.body)}</div>` : ''}
    </div>
  `).join('');

  list.querySelectorAll('.notif-item.unread').forEach(el => {
    el.addEventListener('click', () => markRead(el.dataset.id));
  });
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

async function markRead(id) {
  await apiPost(`/notifications/${id}/read`);
  const n = notifications.find(x => x.id === id);
  if (n) n.read = true;
  render();
}

async function markAllRead() {
  await apiPost('/notifications/read-all');
  notifications.forEach(n => n.read = true);
  render();
}

export async function initNotifications() {
  try {
    notifications = await apiGet('/notifications');
  } catch {
    notifications = [];
  }
  render();

  const bell = document.getElementById('notification-bell');
  const panel = document.getElementById('notif-panel');

  bell.addEventListener('click', (e) => {
    e.stopPropagation();
    panel.hidden = !panel.hidden;
  });

  document.addEventListener('click', (e) => {
    if (!panel.contains(e.target) && e.target !== bell) {
      panel.hidden = true;
    }
  });

  document.getElementById('notif-read-all').addEventListener('click', markAllRead);
}
