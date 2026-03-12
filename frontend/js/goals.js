import { apiGet } from './api.js';

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function renderGoals(goals) {
  const list = document.getElementById('goals-list');
  const noGoals = document.getElementById('no-goals');

  if (goals.length === 0) {
    list.innerHTML = '';
    noGoals.hidden = false;
    return;
  }

  noGoals.hidden = true;
  list.innerHTML = goals.map(g => {
    const pct = g.total_words ? Math.round((g.known_words / g.total_words) * 100) : 0;
    return `
      <div class="goal-card">
        <div class="goal-title">${esc(g.title)}</div>
        <div class="goal-meta">${esc(g.language)} · ${esc(g.media_type || 'other')} · ${g.status}</div>
        <div class="goal-progress">
          <div class="goal-progress-bar" style="width:${pct}%"></div>
        </div>
      </div>
    `;
  }).join('');
}

export async function initGoals() {
  try {
    const goals = await apiGet('/goals');
    renderGoals(goals);
  } catch {
    renderGoals([]);
  }
}
