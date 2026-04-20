import { apiGet, apiPost, apiDelete, apiFetch } from './api.js';

function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function renderActions(goal) {
  if (!goal.actions || goal.actions.length === 0) return '';
  return `<div class="goal-actions">${
    goal.actions.map(a =>
      `<button class="btn btn-small btn-action" data-goal-id="${esc(goal.id)}" data-action="${esc(a.id)}" data-media-type="${esc(goal.media_type || '')}">${esc(a.label)}</button>`
    ).join('')
  }</div>`;
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
      <div class="goal-card" data-id="${esc(g.id)}">
        <div class="goal-header">
          <div class="goal-title">${esc(g.title)}</div>
          <button class="goal-delete-btn" data-id="${esc(g.id)}" title="Delete goal">×</button>
        </div>
        <div class="goal-meta">${esc(g.language)} · ${esc(g.media_type || 'other')} · ${g.status}${g.total_words ? ` · ${g.total_words} words` : ''}</div>
        <div class="goal-progress">
          <div class="goal-progress-bar" style="width:${pct}%"></div>
        </div>
        ${renderActions(g)}
        <div class="goal-import-result" data-goal-id="${esc(g.id)}" hidden></div>
      </div>
    `;
  }).join('');

  list.querySelectorAll('.goal-delete-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      try {
        await apiDelete(`/goals/${id}`);
        btn.closest('.goal-card').remove();
        if (!list.querySelector('.goal-card')) {
          document.getElementById('no-goals').hidden = false;
        }
      } catch (e) {
        alert(`Could not delete goal: ${e.message}`);
      }
    });
  });

  list.querySelectorAll('.btn-action').forEach(btn => {
    btn.addEventListener('click', () => handleAction(btn));
  });
}

async function handleAction(btn) {
  const goalId = btn.dataset.goalId;
  const action = btn.dataset.action;
  const mediaType = btn.dataset.mediaType;

  if (action === 'upload_subtitles') {
    let input = card.querySelector('.srt-file-input');
    if (input) { input.click(); return; }
    input = document.createElement('input');
    input.type = 'file';
    input.accept = '.srt,.ass,.ssa,.sub,.vtt,.txt';
    input.className = 'srt-file-input';
    input.hidden = true;
    card.appendChild(input);
    input.addEventListener('change', async () => {
      if (!input.files.length) return;
      btn.disabled = true;
      btn.textContent = 'uploading...';
      const form = new FormData();
      form.append('file', input.files[0]);
      try {
        const res = await apiFetch(`/goals/${goalId}/upload-srt`, { method: 'POST', body: form });
        showResult(resultEl, res);
      } catch (e) {
        showResult(resultEl, null, e.message);
      } finally {
        btn.disabled = false;
        btn.textContent = 'Upload SRT';
        input.value = '';
      }
    });
    input.click();
    return;
  }

  if (action !== 'import_subtitles') return;

  const card = btn.closest('.goal-card');
  const resultEl = card.querySelector('.goal-import-result');

  if (mediaType === 'movie') {
    btn.disabled = true;
    btn.textContent = 'importing...';
    try {
      const res = await apiPost(`/goals/${goalId}/auto-import`);
      showResult(resultEl, res);
    } catch (e) {
      showResult(resultEl, null, e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Import Vocab';
    }
  } else {
    // series — show inline season/episode form
    let form = card.querySelector('.import-form');
    if (form) {
      form.hidden = !form.hidden;
      return;
    }
    form = document.createElement('div');
    form.className = 'import-form';
    form.innerHTML = `
      <input type="number" class="import-season" placeholder="Season" min="1">
      <input type="number" class="import-episode" placeholder="Episode" min="1">
      <button class="btn btn-small import-submit">Import</button>
    `;
    resultEl.before(form);

    form.querySelector('.import-submit').addEventListener('click', async () => {
      const season = parseInt(form.querySelector('.import-season').value) || undefined;
      const episode = parseInt(form.querySelector('.import-episode').value) || undefined;
      const submitBtn = form.querySelector('.import-submit');
      submitBtn.disabled = true;
      submitBtn.textContent = 'importing...';
      try {
        const res = await apiPost(`/goals/${goalId}/auto-import`, { season, episode });
        showResult(resultEl, res);
      } catch (e) {
        showResult(resultEl, null, e.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Import';
      }
    });
  }
}

function showResult(el, res, error) {
  el.hidden = false;
  if (error) {
    el.textContent = error;
    el.className = 'goal-import-result goal-import-error';
  } else {
    el.textContent = `${res.new_cards} new cards added`;
    el.className = 'goal-import-result goal-import-success';
  }
}

async function loadMediaTypes() {
  const select = document.getElementById('add-goal-type');
  select.innerHTML = '';
  try {
    const types = await apiGet('/goals/media-types');
    for (const t of types) {
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t;
      select.appendChild(opt);
    }
  } catch { /* leave empty */ }
}

export async function initGoals() {
  loadMediaTypes();

  document.getElementById('add-goal-form').onsubmit = async (e) => {
    e.preventDefault();
    const titleInput = document.getElementById('add-goal-title');
    const typeSelect = document.getElementById('add-goal-type');
    const title = titleInput.value.trim();
    if (!title) return;

    try {
      await apiPost('/goals', {
        title,
        media_type: typeSelect.value || null,
      });
      titleInput.value = '';
      const goals = await apiGet('/goals');
      renderGoals(goals);
    } catch (err) {
      alert(`Could not add goal: ${err.message}`);
    }
  };

  try {
    const goals = await apiGet('/goals');
    renderGoals(goals);
  } catch {
    renderGoals([]);
  }
}
