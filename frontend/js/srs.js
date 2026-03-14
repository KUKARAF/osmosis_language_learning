import { apiGet, apiPost, apiPatch, apiDelete } from './api.js';

let cards = [];
let currentIndex = 0;
let _devMode = false;

function needsGeneration(card) {
  return !card.back || /^\[.+\]$/.test(card.back);
}

function renderStats(stats) {
  const el = document.getElementById('review-stats-text');
  el.textContent = `cards learned: ${stats.total_reviews || 0} · streak: ${stats.streak_days || 0}d`;
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

  const context = card.context_sentence ? `\n\n"${card.context_sentence}"` : '';
  front.textContent = card.front + context;
  back.textContent = card.back;

  flashcard.onclick = async () => {
    const flipping = flashcard.classList.toggle('flipped');
    ratingBtns.hidden = !flipping;
    cardActions.hidden = !flipping;
    if (!flipping) editForm.hidden = true;

    if (flipping && needsGeneration(card)) {
      back.textContent = 'translating...';
      try {
        const updated = await apiPost(`/srs/cards/${card.id}/generate-back`);
        cards[currentIndex] = updated;
        back.textContent = updated.back;
      } catch {
        back.textContent = 'translation failed';
      }
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
