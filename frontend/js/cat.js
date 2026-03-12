import { apiGet, apiPost } from './api.js';

const FACES = {
  happy: '=^.^=',
  hangry: '=>.<=',
  hospitalized: 'x_x',
};

let cachedCat = null;

export function getCatState() {
  return cachedCat;
}

function renderCat(cat) {
  cachedCat = cat;
  const face = FACES[cat.state] || FACES.happy;
  const display = document.getElementById('cat-display');
  const mini = document.getElementById('cat-status-mini');
  const groomBtn = document.getElementById('groom-btn');

  display.textContent = face;
  mini.textContent = face;

  if (cat.state === 'hospitalized') {
    groomBtn.textContent = 'heal';
    groomBtn.hidden = false;
  } else if (cat.state === 'hangry') {
    groomBtn.textContent = 'groom';
    groomBtn.hidden = false;
  } else {
    groomBtn.hidden = true;
  }
}

async function handleGroom() {
  if (!cachedCat) return;
  const endpoint = cachedCat.state === 'hospitalized' ? '/cats/active/heal' : '/cats/active/groom';
  const result = await apiPost(endpoint);
  if (result && result.cat) {
    renderCat(result.cat);
  } else {
    await initCat();
  }
}

export async function initCat() {
  try {
    const cat = await apiGet('/cats/active');
    renderCat(cat);
  } catch {
    document.getElementById('cat-display').textContent = FACES.happy;
    document.getElementById('cat-status-mini').textContent = FACES.happy;
    document.getElementById('groom-btn').hidden = true;
  }

  document.getElementById('groom-btn').onclick = handleGroom;
}
