import { checkAuth, redirectToLogin } from './auth.js';
import { initNotifications } from './notifications.js';
import { initChat, teardownChat, setDevMode } from './chat.js';
import { initReview, setDevMode as setSrsDevMode } from './srs.js';
import { initGoals } from './goals.js';
import { initSettings } from './settings.js';

const routes = {
  '/': { page: 'chat', init: initChat, teardown: teardownChat },
  '/review': { page: 'review', init: initReview },
  '/goals': { page: 'goals', init: initGoals },
  '/settings': { page: 'settings', init: initSettings },
};

let currentRoute = null;

function getHash() {
  return window.location.hash.slice(1) || '/';
}

async function navigate() {
  const hash = getHash();
  const route = routes[hash] || routes['/'];

  // Teardown previous page
  if (currentRoute && currentRoute.teardown) {
    currentRoute.teardown();
  }

  // Switch active page
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById(`page-${route.page}`).classList.add('active');

  // Update nav links
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.getAttribute('href') === `#${hash}`);
  });

  currentRoute = route;

  // Init new page
  if (route.init) {
    await route.init();
  }
}

async function boot() {
  const user = await checkAuth();
  if (!user) {
    redirectToLogin();
    return;
  }
  if (user.dev_mode) {
    setDevMode(true);
    setSrsDevMode(true);
  }

  await initNotifications();
  window.addEventListener('hashchange', navigate);
  await navigate();
}

boot();
