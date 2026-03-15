import { apiGet, apiPost, apiPatch, apiDelete } from './api.js';

let cards = [];
let currentIndex = 0;
let _devMode = false;

const GRAMMAR_TYPES = new Set(['conjugation', 'pattern', 'gender']);

function isGrammarCard(card) {
  return GRAMMAR_TYPES.has(card.card_type);
}

function needsGeneration(card) {
  return !card.back || /^\[.+\]$/.test(card.back);
}

function renderStats(stats) {
  const el = document.getElementById('review-stats-text');
  el.textContent = `cards learned: ${stats.total_reviews || 0} · streak: ${stats.streak_days || 0}d`;
}

function renderGrammarBack(back, quiz) {
  back.innerHTML = '';

  const chip = document.createElement('span');
  chip.className = 'card-type-chip';
  chip.textContent = quiz.type || 'grammar';
  back.appendChild(chip);

  if (quiz.type === 'conjugation' && quiz.answer && typeof quiz.answer === 'object') {
    const table = document.createElement('table');
    table.className = 'conjugation-table';
    for (const [person, form] of Object.entries(quiz.answer)) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="person">${person}</td><td class="form">${form}</td>`;
      table.appendChild(tr);
    }
    back.appendChild(table);
  } else {
    const answer = document.createElement('div');
    answer.className = 'grammar-answer';
    answer.textContent = quiz.answer || '';
    back.appendChild(answer);
  }

  if (quiz.rule) {
    const rule = document.createElement('div');
    rule.className = 'grammar-rule';
    rule.textContent = quiz.rule;
    back.appendChild(rule);
  }

  if (quiz.example) {
    const ex = document.createElement('div');
    ex.className = 'grammar-example';
    ex.textContent = quiz.example;
    back.appendChild(ex);
  }
}

function renderCard(card) {
  const flashcard = document.getElementById('flashcard');
  const front = flashcard.querySelector('.flashcard-front');
  const back = flashcard.querySelector('.flashcard-back');
  const ratingBtns = document.getElementById('rating-buttons');
  const cardActions = document.getElementById('card-actions');
  const editForm = document.getElementById('edit-card-form');
  const noCards = document.getElementById('no-cards-message');

  flashcard.classList.remove('flipped');
  ratingBtns.hidden = true;
  cardActions.hidden = true;
  editForm.hidden = true;

  if (!card) {
    flashcard.hidden = true;
    noCards.hidden = false;
    return;
  }

  flashcard.hidden = false;
  noCards.hidden = true;

  // Front face
  const wordEl = front.querySelector('.card-word');
  const ctxEl = front.querySelector('.card-context');

  // Show card type chip on front for grammar cards
  let chipEl = front.querySelector('.card-type-chip');
  if (isGrammarCard(card)) {
    if (!chipEl) {
      chipEl = document.createElement('span');
      chipEl.className = 'card-type-chip';
      front.insertBefore(chipEl, wordEl);
    }
    chipEl.textContent = card.card_type;
    chipEl.hidden = false;
  } else if (chipEl) {
    chipEl.hidden = true;
  }

  wordEl.textContent = card.front;
  ctxEl.textContent = card.context_sentence ? `"${card.context_sentence}"` : '';

  // Back face — clear for fresh render
  back.textContent = '';

  flashcard.onclick = async () => {
    const flipping = flashcard.classList.toggle('flipped');
    ratingBtns.hidden = !flipping;
    cardActions.hidden = !flipping;
    if (!flipping) editForm.hidden = true;

    if (!flipping) return;

    if (isGrammarCard(card)) {
      back.textContent = 'generating quiz...';
      try {
        const quiz = await apiPost(`/api/plugins/grammar/quiz/${card.id}`);
        // Show quiz prompt on front, answer on back
        wordEl.textContent = quiz.prompt || card.front;
        renderGrammarBack(back, quiz);
      } catch {
        back.textContent = 'quiz generation failed';
      }
    } else if (needsGeneration(card)) {
      back.textContent = 'translating...';
      try {
        const updated = await apiPost(`/srs/cards/${card.id}/generate-back`);
        cards[currentIndex] = updated;
        back.textContent = updated.back;
      } catch {
        back.textContent = 'translation failed';
      }
    } else {
      back.textContent = card.back;
    }
  };
}

async function submitRating(rating) {
  const card = cards[currentIndex];
  if (!card) return;

  await apiPost(`/srs/cards/${card.id}/review`, { rating });

  currentIndex++;
  if (currentIndex < cards.length) {
    renderCard(cards[currentIndex]);
  } else {
    renderCard(null);
    try {
      const stats = await apiGet('/srs/stats');
      renderStats(stats);
    } catch { /* ignore */ }
  }
}

async function deleteCard() {
  const card = cards[currentIndex];
  if (!card) return;

  await apiDelete(`/srs/cards/${card.id}`);

  cards.splice(currentIndex, 1);
  if (currentIndex < cards.length) {
    renderCard(cards[currentIndex]);
  } else {
    renderCard(null);
    try {
      const stats = await apiGet('/srs/stats');
      renderStats(stats);
    } catch { /* ignore */ }
  }
}

function showEditForm() {
  const card = cards[currentIndex];
  if (!card) return;

  document.getElementById('edit-front').value = card.front || '';
  document.getElementById('edit-back').value = card.back || '';
  document.getElementById('edit-context').value = card.context_sentence || '';
  document.getElementById('edit-card-form').hidden = false;
}

async function submitEdit(e) {
  e.preventDefault();
  const card = cards[currentIndex];
  if (!card) return;

  const body = {
    front: document.getElementById('edit-front').value,
    back: document.getElementById('edit-back').value,
    context_sentence: document.getElementById('edit-context').value,
  };

  const updated = await apiPatch(`/srs/cards/${card.id}`, body);
  cards[currentIndex] = updated;
  document.getElementById('edit-card-form').hidden = true;
  renderCard(updated);
  // Re-flip to show updated back
  document.getElementById('flashcard').classList.add('flipped');
  document.getElementById('rating-buttons').hidden = false;
  document.getElementById('card-actions').hidden = false;
}

async function deleteAllCards() {
  if (!confirm('Delete ALL cards? This cannot be undone.')) return;

  await apiDelete('/srs/cards');
  cards = [];
  currentIndex = 0;
  renderCard(null);
  try {
    const stats = await apiGet('/srs/stats');
    renderStats(stats);
  } catch { /* ignore */ }
}

export function setDevMode(enabled) {
  _devMode = enabled;
  const btn = document.getElementById('delete-all-btn');
  if (btn) btn.hidden = !enabled;
}

export async function initReview() {
  currentIndex = 0;

  const [stats, dueCards] = await Promise.all([
    apiGet('/srs/stats').catch(() => ({})),
    apiGet('/srs/cards/due').catch(() => []),
  ]);

  renderStats(stats);
  cards = dueCards;

  if (cards.length > 0) {
    renderCard(cards[0]);
  } else {
    renderCard(null);
  }

  document.querySelectorAll('.btn-rating').forEach(btn => {
    btn.onclick = () => submitRating(Number(btn.dataset.rating));
  });

  document.getElementById('delete-card-btn').onclick = deleteCard;
  document.getElementById('edit-card-btn').onclick = showEditForm;
  document.getElementById('edit-card-form').onsubmit = submitEdit;
  document.getElementById('edit-cancel-btn').onclick = () => {
    document.getElementById('edit-card-form').hidden = true;
  };
  document.getElementById('delete-all-btn').onclick = deleteAllCards;

  // Restore dev mode visibility
  if (_devMode) {
    document.getElementById('delete-all-btn').hidden = false;
  }
}
