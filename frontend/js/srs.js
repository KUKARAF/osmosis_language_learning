import { apiGet, apiPost } from './api.js';

let cards = [];
let currentIndex = 0;

function renderStats(stats) {
  const el = document.getElementById('review-stats');
  el.textContent = `cards learned: ${stats.total_reviews || 0} · streak: ${stats.streak_days || 0}d`;
}

function renderCard(card) {
  const flashcard = document.getElementById('flashcard');
  const front = flashcard.querySelector('.flashcard-front');
  const back = flashcard.querySelector('.flashcard-back');
  const ratingBtns = document.getElementById('rating-buttons');
  const noCards = document.getElementById('no-cards-message');

  flashcard.classList.remove('flipped');
  ratingBtns.hidden = true;

  if (!card) {
    flashcard.hidden = true;
    noCards.hidden = false;
    return;
  }

  flashcard.hidden = false;
  noCards.hidden = true;

  const context = card.context_sentence ? `\n\n"${card.context_sentence}"` : '';
  front.textContent = card.front + context;
  back.textContent = `${card.back}\n\n(${card.card_type || 'vocabulary'})`;

  flashcard.onclick = () => {
    flashcard.classList.add('flipped');
    ratingBtns.hidden = false;
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
    // Refresh stats after completing session
    try {
      const stats = await apiGet('/srs/stats');
      renderStats(stats);
    } catch { /* ignore */ }
  }
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
}
