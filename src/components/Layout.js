/**
 * @param {string} id
 * @returns {void}
 */
export function setNav(id) {
  document.querySelectorAll('.nav-item,.npp').forEach(el => {
    el.classList.toggle('active', el.dataset.nav === id);
  });
  document.querySelectorAll('[data-nav]').forEach(el => {
    el.classList.toggle('active', el.dataset.nav === id);
  });
}

const pageMap = {
  market:      'showMarket',
  signals:     'showSignalFeed',
  understand:  'showUnderstand',
  size:        'showSize',
  act:         'showAct',
  portfolio:   'showPortfolio',
  risk:        'showRisk',
  performance: 'showPerformance',
  alerts:      'showAlerts',
  settings:    'showSettings'
};

/**
 * @param {string} page
 * @returns {void}
 */
export function navigateTo(page) {
  setNav(page);
  const fn = window[pageMap[page]];
  if (typeof fn === 'function') fn();
}
