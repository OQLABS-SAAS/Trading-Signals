/**
 * @param {number} rsi
 * @returns {void}
 */
export function rsiGaugeUpdate(rsi) {
  const val = Math.min(100, Math.max(0, Number(rsi) || 50));
  const deg = (val / 100 * 180) - 90;

  const needle = document.getElementById('rsiNeedle');
  const disp = document.getElementById('rsiGaugeVal');
  const lbl = document.getElementById('rsiArcLabel');
  const arc = document.getElementById('rsiActivePath');

  const color = val < 30
    ? 'rgba(224,85,85,.9)'
    : val > 70
      ? 'rgba(61,190,108,.9)'
      : 'rgba(148,175,220,.9)';

  if (needle) needle.style.transform = 'rotate(' + deg + 'deg)';
  if (disp) {
    disp.textContent = Math.round(val);
    disp.style.color = color;
  }
  if (lbl) {
    lbl.textContent = 'RSI ' + Math.round(val);
    lbl.setAttribute('fill', color);
  }
  if (arc) {
    const cx = 110, cy = 105, r = 95;
    const sr = (-90) * Math.PI / 180;
    const er = deg * Math.PI / 180;
    const sx = cx + r * Math.cos(sr);
    const sy = cy + r * Math.sin(sr);
    const ex = cx + r * Math.cos(er);
    const ey = cy + r * Math.sin(er);

    arc.setAttribute('d', 'M' + sx.toFixed(1) + ' ' + sy.toFixed(1) +
      ' A' + r + ' ' + r + ' 0 ' + (val > 50 ? 1 : 0) + ' 1 ' + ex.toFixed(1) + ' ' + ey.toFixed(1));
    arc.setAttribute('stroke', color);
  }
}

/**
 * @param {number} conf
 * @returns {string}
 */
export function buildConfRing(conf) {
  const c = Math.round(conf) || 0;
  const r = 18;
  const circ = 2 * Math.PI * r;
  const offset = circ - (c / 100) * circ;

  const color = c >= 75
    ? 'rgba(61,190,108,.9)'
    : c >= 55
      ? '#d4b87a'
      : 'rgba(224,85,85,.9)';

  return '<svg width="44" height="44" viewBox="0 0 44 44" style="vertical-align:middle;margin-right:4px">' +
    '<circle cx="22" cy="22" r="' + r + '" fill="none" stroke="rgba(148,175,220,.12)" stroke-width="4"/>' +
    '<circle cx="22" cy="22" r="' + r + '" fill="none" stroke="' + color + '" stroke-width="4"' +
    ' stroke-dasharray="' + circ + '" stroke-dashoffset="' + offset + '"' +
    ' transform="rotate(-90 22 22)" stroke-linecap="round"/>' +
    '<text x="22" y="22" text-anchor="middle" dominant-baseline="central"' +
    ' fill="' + color + '" font-size="12" font-weight="bold" font-family="monospace">' + c + '</text>' +
    '</svg>';
}
