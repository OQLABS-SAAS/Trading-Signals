function _s(id, v) {
  const e = document.getElementById(id);
  if (e) e.textContent = v;
}

function _c(id, v) {
  const e = document.getElementById(id);
  if (e) e.style.color = v;
}

function _w(id, p) {
  const e = document.getElementById(id);
  if (e) e.style.width = Math.min(100, Math.max(0, p)) + '%';
}

/**
 * @param {object} sig
 */
export function renderOrderFlow(sig) {
  if (!sig) return;

  let cvdText = 'Neutral →';
  let cvdColor = 'rgba(148,175,220,.8)';

  if (sig.emaTrend === 'bullish' && (sig.macdHist || 0) > 0) {
    cvdText = 'Accumulating ↑';
    cvdColor = 'rgba(61,190,108,.9)';
  } else if (sig.emaTrend === 'bearish' && (sig.macdHist || 0) < 0) {
    cvdText = 'Distributing ↓';
    cvdColor = 'rgba(224,85,85,.9)';
  }

  _s('ofCvd', cvdText);
  _c('ofCvd', cvdColor);

  const bull = sig.bullCount || 0;
  const bear = sig.bearCount || 1;
  const buyPct = Math.round((bull / (bull + bear)) * 100);
  const sellPct = 100 - buyPct;

  _w('ofBuyBar', buyPct);
  _s('ofBuyPct', buyPct + '%');
  _w('ofSellBar', sellPct);
  _s('ofSellPct', sellPct + '%');

  const vr = sig.volRatio || 1;
  let volColor = 'rgba(148,175,220,.8)';
  if (vr > 1.2) volColor = 'rgba(61,190,108,.9)';
  else if (vr < 0.8) volColor = 'rgba(224,85,85,.9)';

  _s('ofVol', vr.toFixed(2) + '×');
  _c('ofVol', volColor);

  const atrVal = sig.atr ? Number(sig.atr).toPrecision(4) : '—';
  _s('ofAtr', atrVal);

  window._ofBuyPct = buyPct;
}
