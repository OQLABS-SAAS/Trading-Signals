/**
 * @returns {void}
 */
export function updateFlowBadge() {
  const sig = window._activeSignal;
  const badge = document.getElementById('szFlowBadge');

  if (!sig || !badge) {
    if (badge) badge.style.display = 'none';
    return;
  }

  const buyPct = window._ofBuyPct != null
    ? window._ofBuyPct
    : Math.round(((sig.bullCount || 0) / ((sig.bullCount || 0) + (sig.bearCount || 1))) * 100);

  const vr = sig.volRatio || 1;
  const confLbl = (sig.confLbl || '').toUpperCase();

  const base = confLbl === 'CONFIRMED' || confLbl === 'HIGH'
    ? 1.0
    : confLbl === 'LIKELY' || confLbl === 'MEDIUM'
      ? 0.75
      : 0.5;

  let mult = base;

  if (vr > 1.5) mult += 0.25;
  else if (vr > 1.2) mult += 0.10;

  if (buyPct > 65) mult += 0.10;
  else if (buyPct < 35) mult -= 0.15;

  mult = Math.min(1.5, Math.max(0.25, mult));
  mult = Math.round(mult / 0.25) * 0.25;

  window._flowMult = mult;

  const parts = [confLbl || 'MEDIUM'];

  if (vr > 1.5) parts.push('very high volume +0.25');
  else if (vr > 1.2) parts.push('high volume +0.10');

  if (buyPct > 65) parts.push('strong buy pressure +0.10');
  else if (buyPct < 35) parts.push('weak buy pressure −0.15');

  const multEl = document.getElementById('szFlowMult');
  const reasonEl = document.getElementById('szFlowReason');

  if (multEl) multEl.textContent = mult.toFixed(2) + '×';
  if (reasonEl) reasonEl.textContent = parts.join(' · ');

  badge.style.display = 'block';
}

/**
 * @returns {void}
 */
export function applyFlowMult() {
  const inp = document.getElementById('szRisk');
  if (!inp) return;

  const cur = parseFloat(inp.value) || 1;
  const m = window._flowMult || 1;
  const nv = Math.min(10, Math.round(cur * m * 100) / 100);

  inp.value = nv;

  if (typeof szCalc === 'function') szCalc();
}
