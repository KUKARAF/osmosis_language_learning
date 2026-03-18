import { apiGet, apiPost, apiPatch, apiDelete } from './api.js';

let cards = [];
let currentIndex = 0;
let _devMode = false;

// State for the current card's review session
let _lastQuiz = null;       // grammar quiz data for evaluation
let _mediaRecorder = null;  // active MediaRecorder instance
let _audioChunks = [];
let _currentSpeakText = ''; // text for TTS
let _currentDoFlip = null;  // doFlip fn for current card (set in renderCard)

const GRAMMAR_TYPES = new Set(['conjugation', 'pattern', 'gender']);
const RATING_LABELS = { 1: 'again', 2: 'hard', 3: 'good', 4: 'easy' };

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

// ── Recording ────────────────────────────────────────────────────────────────

async function startRecording(card) {
  if (_mediaRecorder) return; // already recording

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    alert('Microphone access denied.');
    return;
  }

  _audioChunks = [];
  _mediaRecorder = new MediaRecorder(stream);
  _mediaRecorder.ondataavailable = e => { if (e.data.size > 0) _audioChunks.push(e.data); };
  _mediaRecorder.onstop = async () => {
    stream.getTracks().forEach(t => t.stop());
    const blob = new Blob(_audioChunks, { type: 'audio/webm' });
    _mediaRecorder = null;
    document.getElementById('mic-btn').textContent = '🎤';

    const fd = new FormData();
    fd.append('audio', blob, 'recording.webm');
    fd.append('language', card.language || 'en');

    const input = document.getElementById('answer-input');
    input.placeholder = 'transcribing...';
    try {
      const res = await fetch(`/api/srs/cards/${card.id}/transcribe`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: fd,
      });
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      input.value = data.text;
      input.placeholder = 'type your answer...';
      // Auto-flip after transcription
      if (_currentDoFlip) _currentDoFlip();
    } catch {
      input.placeholder = 'transcription failed';
    }
  };

  _mediaRecorder.start();
  document.getElementById('mic-btn').textContent = '🔴';

  // Auto-stop after 30s
  setTimeout(() => { if (_mediaRecorder) stopRecording(); }, 30000);
}

function stopRecording() {
  if (_mediaRecorder && _mediaRecorder.state !== 'inactive') {
    _mediaRecorder.stop();
  }
}

// ── TTS ──────────────────────────────────────────────────────────────────────

async function speakText(card, text) {
  if (!text) return;
  const btn = document.getElementById('speak-btn');
  btn.textContent = '⏳';
  btn.disabled = true;
  try {
    const resp = await fetch(`/api/srs/cards/${card.id}/speak`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });
    if (!resp.ok) throw new Error(resp.statusText);
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    await audio.play();
  } catch (err) {
    btn.textContent = '❌';
    setTimeout(() => { btn.textContent = '🔊'; }, 2000);
  } finally {
    btn.disabled = false;
  }
}

// ── Evaluation ───────────────────────────────────────────────────────────────

async function evaluateAnswer(card, userAnswer) {
  let cardPrompt, correctAnswer;

  if (isGrammarCard(card) && _lastQuiz) {
    cardPrompt = _lastQuiz.prompt || card.front;
    if (_lastQuiz.type === 'conjugation' && _lastQuiz.answer && typeof _lastQuiz.answer === 'object') {
      correctAnswer = Object.entries(_lastQuiz.answer)
        .map(([p, f]) => `${p}: ${f}`).join(', ');
    } else {
      correctAnswer = _lastQuiz.answer || '';
    }
  } else {
    cardPrompt = card.front;
    correctAnswer = card.back || '';
  }

  const panel = document.getElementById('eval-panel');
  const explEl = document.getElementById('eval-explanation');
  panel.hidden = false;
  explEl.textContent = 'evaluating...';

  try {
    const result = await apiPost(`/srs/cards/${card.id}/evaluate`, {
      user_answer: userAnswer,
      card_prompt: cardPrompt,
      correct_answer: correctAnswer,
    });

    explEl.textContent = result.explanation;
    panel.dataset.rating = result.rating;

    // Highlight suggested rating button
    document.querySelectorAll('.btn-rating').forEach(btn => {
      btn.classList.remove('btn-rating-suggested');
    });
    const suggested = document.querySelector(`.btn-rating[data-rating="${result.rating}"]`);
    if (suggested) suggested.classList.add('btn-rating-suggested');

  } catch {
    explEl.textContent = 'evaluation failed — rate manually';
  }
}

// ── Card rendering ────────────────────────────────────────────────────────────

function renderGrammarBack(back, quiz) {
  back.innerHTML = '';

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

function setPreFlipUI() {
  document.getElementById('answer-area').hidden = false;
  document.getElementById('preflip-actions').hidden = false;
  document.getElementById('rating-buttons').hidden = true;
  document.getElementById('card-actions').hidden = true;
  document.getElementById('eval-panel').hidden = true;
  document.getElementById('answer-input').value = '';
  document.getElementById('mic-btn').textContent = '🎤';

  // Reset suggested rating
  document.querySelectorAll('.btn-rating').forEach(btn => {
    btn.classList.remove('btn-rating-suggested');
    btn.disabled = false;
    btn.title = '';
  });
  _lastQuiz = null;
  _currentSpeakText = '';
}

function setPostFlipUI(hasAnswer) {
  document.getElementById('answer-area').hidden = true;
  document.getElementById('preflip-actions').hidden = true;
  document.getElementById('rating-buttons').hidden = false;
  document.getElementById('card-actions').hidden = false;

  // Easy is disabled unless the user provided an answer
  const easyBtn = document.getElementById('easy-postflip-btn');
  if (!hasAnswer) {
    easyBtn.disabled = true;
    easyBtn.title = 'type or say your answer to mark as easy';
    easyBtn.classList.add('btn-rating-disabled');
  } else {
    easyBtn.disabled = false;
    easyBtn.title = '';
    easyBtn.classList.remove('btn-rating-disabled');
  }
}

function renderCard(card) {
  const flashcard = document.getElementById('flashcard');
  const front = flashcard.querySelector('.flashcard-front');
  const back = flashcard.querySelector('.flashcard-back');
  const editForm = document.getElementById('edit-card-form');
  const noCards = document.getElementById('no-cards-message');

  flashcard.classList.remove('flipped');
  editForm.hidden = true;
  stopRecording();

  if (!card) {
    flashcard.hidden = true;
    noCards.hidden = false;
    document.getElementById('answer-area').hidden = true;
    document.getElementById('preflip-actions').hidden = true;
    document.getElementById('rating-buttons').hidden = true;
    document.getElementById('card-actions').hidden = true;
    document.getElementById('eval-panel').hidden = true;
    return;
  }

  flashcard.hidden = false;
  noCards.hidden = false;
  noCards.hidden = true;

  // Card-type chip on front for grammar cards
  let chipEl = front.querySelector('.card-type-chip');
  if (isGrammarCard(card)) {
    if (!chipEl) {
      chipEl = document.createElement('span');
      chipEl.className = 'card-type-chip';
      front.insertBefore(chipEl, front.querySelector('.card-word'));
    }
    chipEl.textContent = card.card_type;
    chipEl.hidden = false;
  } else if (chipEl) {
    chipEl.hidden = true;
  }

  front.querySelector('.card-word').textContent = card.front;
  front.querySelector('.card-context').textContent =
    card.context_sentence ? `"${card.context_sentence}"` : '';
  back.textContent = '';

  setPreFlipUI();

  // ── Flip logic ───────────────────────────────────────────────────────────
  async function doFlip() {
    _currentDoFlip = null; // prevent double-flip
    if (flashcard.classList.contains('flipped')) return; // already flipped
    stopRecording();

    const userAnswer = document.getElementById('answer-input').value.trim();
    flashcard.classList.add('flipped');
    setPostFlipUI(!!userAnswer);

    if (isGrammarCard(card)) {
      back.textContent = 'generating quiz...';
      try {
        const quiz = await apiPost(`/api/plugins/grammar/quiz/${card.id}`);
        _lastQuiz = quiz;
        front.querySelector('.card-word').textContent = quiz.prompt || card.front;
        renderGrammarBack(back, quiz);
        _currentSpeakText = quiz.example || quiz.answer || '';
      } catch {
        back.textContent = 'quiz generation failed';
        _currentSpeakText = '';
      }
    } else if (needsGeneration(card)) {
      back.textContent = 'translating...';
      try {
        const updated = await apiPost(`/srs/cards/${card.id}/generate-back`);
        cards[currentIndex] = updated;
        back.textContent = updated.back;
        _currentSpeakText = card.front; // speak the target-language word
      } catch {
        back.textContent = 'translation failed';
        _currentSpeakText = '';
      }
    } else {
      back.textContent = card.back;
      _currentSpeakText = card.front; // speak the target-language word
    }

    if (userAnswer) {
      await evaluateAnswer(card, userAnswer);
    }
  }

  _currentDoFlip = doFlip;
  flashcard.onclick = doFlip;
  document.getElementById('flip-btn').onclick = doFlip;
}

// ── Rating & navigation ───────────────────────────────────────────────────────

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
  document.getElementById('flashcard').classList.add('flipped');
  setPostFlipUI(false);
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

  // Enter key on answer input triggers flip
  document.getElementById('answer-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); if (_currentDoFlip) _currentDoFlip(); }
  });

  // Rating buttons (post-flip)
  document.querySelectorAll('.btn-rating[data-rating]').forEach(btn => {
    btn.onclick = () => {
      if (btn.disabled) return;
      submitRating(Number(btn.dataset.rating));
    };
  });

  // Mic button
  document.getElementById('mic-btn').onclick = () => {
    const card = cards[currentIndex];
    if (!card) return;
    if (_mediaRecorder) {
      stopRecording();
    } else {
      startRecording(card);
    }
  };

  document.getElementById('speak-btn').onclick = () => {
    const card = cards[currentIndex];
    if (card && _currentSpeakText) speakText(card, _currentSpeakText);
  };
  document.getElementById('delete-card-btn').onclick = deleteCard;
  document.getElementById('edit-card-btn').onclick = showEditForm;
  document.getElementById('edit-card-form').onsubmit = submitEdit;
  document.getElementById('edit-cancel-btn').onclick = () => {
    document.getElementById('edit-card-form').hidden = true;
  };
  document.getElementById('delete-all-btn').onclick = deleteAllCards;

  if (_devMode) {
    document.getElementById('delete-all-btn').hidden = false;
  }
}
