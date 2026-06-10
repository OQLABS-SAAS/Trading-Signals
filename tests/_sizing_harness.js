var window = {
  _forexUsdRates: {
    USDCAD:1.35, USDCHF:0.90, USDJPY:150, USDINR:83,
    USDCNH:7.2,  USDMXN:17,   EURUSD:1.08, GBPUSD:1.27,
    AUDUSD:0.67, NZDUSD:0.61
  },
  _todayLeverage: 100
};
var _todayLeverageReal = false;
function _szBrokerLeverageValue(){ return 100; }
function _szNormalizeAssetType(assetType){
  var a = String(assetType || '').toLowerCase();
  if(a === 'equity' || a === 'stocks' || a === 'shares' || a === 'auto') return 'stock';
  if(a === 'fx' || a === 'forex' || a === 'currency' || a === 'currencies') return 'forex';
  if(a === 'indices') return 'index';
  if(a === 'macro') return 'commodity';
  return a || 'stock';
}
function _szMarginDivisor(assetType, instrumentLev){
  assetType = _szNormalizeAssetType(assetType);
  var broker = _szBrokerLeverageValue();
  if(assetType === 'stock') return 1;
  if(assetType === 'crypto' || assetType === 'index'){
    var inst = parseFloat(instrumentLev) || broker;
    return Math.max(1, Math.min(inst, broker));
  }
  return Math.max(1, broker);
}
function _szUsdPerPriceUnit(assetType, sym){
  assetType = _szNormalizeAssetType(assetType);
  if(assetType !== 'forex') return 1;
  var s = String(sym || '').toUpperCase().replace(/[\/\-]/g,'');
  var quote = s.length >= 6 ? s.slice(3,6) : 'USD';
  return (typeof _forexUsdRate === 'function') ? _forexUsdRate(quote) : 1;
}
function _szUsdPositionValue(assetType, sym, units, price){
  return (parseFloat(units)||0) * (parseFloat(price)||0) * _szUsdPerPriceUnit(assetType, sym);
}
function _szExecQtyDisplay(lots, assetType){
  var n = parseFloat(lots);
  if(!(n > 0)) return '';
  assetType = _szNormalizeAssetType(assetType);
  var trim = function(v){ return String(v).replace(/(\.\d*?[1-9])0+$/,'$1').replace(/\.0+$/,''); };
  if(assetType === 'stock') return String(Math.max(1, Math.round(n)));
  if(assetType === 'crypto') return trim(n.toFixed(6));
  if(assetType === 'forex') return trim(n.toFixed(4));
  return trim(n.toFixed(4));
}
function _szCalcQuantityRaw(calc){
  calc = calc || window._szLastCalc || {};
  var lots = parseFloat(calc.lots);
  if(lots > 0) return lots;
  var posSize = parseFloat(calc.posSize);
  return posSize > 0 ? posSize : 0;
}
function _szContractSize(assetType, sym, forexContractSize){
  assetType = _szNormalizeAssetType(assetType);
  if(assetType === 'forex') return parseFloat(forexContractSize) || 100000;
  if(typeof _todayContractSize === 'function') return _todayContractSize({asset:assetType, sym:sym});
  if(assetType === 'commodity'){
    var s = String(sym || '').toUpperCase();
    // Silver: Yahoo ticker SI=F or broker symbol XAGUSD
    if(/XAG/.test(s) || s === 'SI=F' || s === 'SILVER') return 5000;
    // Gold: Yahoo ticker GC=F or broker symbol XAUUSD
    if(/XAU/.test(s) || s === 'GC=F' || s === 'GOLD') return 100;
    // Crude oil: CL=F, WTI, USOIL, UKOIL, BRENT
    if(/(WTI|USOIL|UKOIL|BRENT)/.test(s) || s === 'CL=F') return 1000;
    // Natural gas: NG=F, NGAS, NATGAS
    if(/(NATGAS|NGAS)/.test(s) || s === 'NG=F' || /^NG/.test(s)) return 10000;
    // Copper: HG=F or COPPER
    if(s === 'COPPER' || s === 'HG=F' || /^HG/.test(s)) return 25000;
    // Platinum / Palladium (100 oz/lot on standard MT5 spot CFD)
    if(/XPT/.test(s) || /PLATINUM/.test(s)) return 100;
    if(/XPD/.test(s) || /PALLADIUM/.test(s)) return 100;
    // Unknown commodity/futures ticker — return null so callers treat as non-tradeable.
    // Do NOT silently return 100; an unverified contract size on a real-money order is unsafe.
    if(/=F$/.test(s) || s.length > 0) return null;
    return null;
  }
  return 1;
}
function _szBrokerLotUnits(assetType, sym){
  assetType = _szNormalizeAssetType(assetType);
  return assetType === 'forex' ? 100000 : _szContractSize(assetType, sym, 100000);
}
function _szNativeLotsFromUnits(units, assetType, sym){
  units = parseFloat(units) || 0;
  assetType = _szNormalizeAssetType(assetType);
  if(assetType === 'stock' || assetType === 'crypto') return units;
  var cs = _szBrokerLotUnits(assetType, sym);
  // cs===null means unknown commodity contract size — return 0 so the caller
  // treats this as non-tradeable rather than silently using contract_size=1
  // (which would oversize a real-money order by up to 5,000×).
  if(cs === null || cs === undefined) return 0;
  return units / cs;
}
function _szFormatNativeSize(units, assetType, sym){
  units = parseFloat(units) || 0;
  assetType = _szNormalizeAssetType(assetType);
  var trim = function(v){ return String(v).replace(/(\.\d*?[1-9])0+$/,'$1').replace(/\.0+$/,''); };
  if(assetType === 'forex'){
    var fxLots = _szNativeLotsFromUnits(units, assetType, sym);
    return trim(fxLots.toFixed(fxLots < 0.01 ? 4 : 2)) + ' lots';
  }
  if(assetType === 'crypto') return (units >= 1 ? trim(units.toFixed(4)) : trim(units.toFixed(6))) + ' units';
  if(assetType === 'index') return trim(_szNativeLotsFromUnits(units, assetType, sym).toFixed(2)) + ' contracts';
  if(assetType === 'commodity') return trim(_szNativeLotsFromUnits(units, assetType, sym).toFixed(4)) + ' lots';
  var sh = Math.max(1, Math.round(units));
  return sh.toLocaleString() + (sh === 1 ? ' share' : ' shares');
}
function _szHasCalculatedQuantity(calc){
  return _szCalcQuantityRaw(calc) > 0;
}

function _todayToggleClass(id, btn){
  var c=window._todayCfg, i=c.classes.indexOf(id);
  if(i>=0) c.classes.splice(i,1); else c.classes.push(id);
  if(typeof _todaySaveCfg==='function') _todaySaveCfg();
  if(btn){ var on=c.classes.indexOf(id)>=0;
    btn.style.borderColor=on?'rgba(201,168,76,.5)':'rgba(237,232,216,.15)';
    btn.style.background=on?'rgba(201,168,76,.12)':'transparent';
    btn.style.color=on?'var(--gold)':'rgba(237,232,216,.4)'; }
}
// Lot specs per asset class: step = tradeable increment, min = broker minimum.
// Broker lot specs in LOTS, plus the CONTRACT SIZE (instrument units per 1.0 lot).
// units = lots × contractSize. This is the fix for the dangerous sizing bug: "1.8 lots
// of silver" is 1.8 × 5,000 = 9,000 oz, NOT 1.8 oz. Without contract sizes the app
// sized commodities/indices as single units and then sent that number to MT5 as LOTS —
// a ~5,000× oversize. Now everything sizes and orders in real lots.
var _TODAY_LOTSPEC = {
  forex:     {lotMin:0.01,  lotStep:0.01 },
  crypto:    {lotMin:0.001, lotStep:0.001},   // 1 lot = 1 coin
  stock:     {lotMin:1,     lotStep:1    },   // 1 lot = 1 share
  index:     {lotMin:0.1,   lotStep:0.1  },
  commodity: {lotMin:0.01,  lotStep:0.01 }
};
function _todayContractSize(o){
  var a=o&&o.asset, s=((o&&o.sym)||'').toUpperCase();
  if(a==='forex') return 100000;                 // 1 lot = 100,000 base units
  if(a==='commodity'){
    // Silver: Yahoo ticker SI=F or broker symbol XAGUSD
    if(/XAG/.test(s) || s === 'SI=F' || s === 'SILVER') return 5000;  // 5,000 oz / lot
    // Gold: Yahoo ticker GC=F or broker symbol XAUUSD
    if(/XAU/.test(s) || s === 'GC=F' || s === 'GOLD') return 100;     // 100 oz / lot
    // Crude oil: CL=F, WTI, USOIL, UKOIL, BRENT
    if(/(WTI|USOIL|UKOIL|BRENT)/.test(s) || s === 'CL=F') return 1000;     // 1,000 bbl / lot
    // Natural gas: NG=F, NGAS, NATGAS
    if(/(NATGAS|NGAS)/.test(s) || s === 'NG=F' || /^NG/.test(s)) return 10000; // 10,000 MMBtu / lot
    // Copper: HG=F or COPPER
    if(s === 'COPPER' || s === 'HG=F' || /^HG/.test(s)) return 25000;  // 25,000 lbs / lot
    // Platinum / Palladium (100 oz/lot on standard MT5 spot CFD)
    if(/XPT/.test(s) || /PLATINUM/.test(s)) return 100;
    if(/XPD/.test(s) || /PALLADIUM/.test(s)) return 100;
    // Unknown commodity/futures ticker — return null so callers treat as non-tradeable.
    // Do NOT silently return 100; an unverified contract size on a real-money order is unsafe.
    return null;
  }
  return 1;                                      // crypto (coin), stock (share), index (unit / $1-pt)
}
// Broker minimum / step expressed in INSTRUMENT UNITS = lots × contract size.
// When cs is null (unknown commodity) return nullCs:true so _todaySizeTrade can
// flag the item as non-tradeable rather than computing NaN/Infinity lots.
function _todayLotUnits(o){
  var sp=_TODAY_LOTSPEC[o.asset]||{lotMin:0.01,lotStep:0.01}, cs=_todayContractSize(o);
  if(cs===null || cs===undefined){
    return {cs:null, stepUnits:0, minUnits:0, nullCs:true};
  }
  return {cs:cs, stepUnits:sp.lotStep*cs, minUnits:sp.lotMin*cs};
}
// Back-compat shim: a few call sites still read _TODAY_LOT[asset].{step,min} in units.
var _TODAY_LOT = {
  forex:     {step:1000,   min:1000  },
  crypto:    {step:0.001,  min:0.001 },
  stock:     {step:1,      min:1     },
  index:     {step:0.1,    min:0.1   },
  commodity: {step:0.01,   min:0.01  }
};
// RISK-DRIVEN sizing: the loss you control sets the size, so every trade risks
// the SAME % and positions are meaningful & tradeable across all instruments.
// Rounds to the broker lot step and flags positions too small for the account.
// Every figure is NET of spread + fees + estimated slippage.
// USD value of 1 unit of an instrument's QUOTE currency. Non-forex assets are USD-quoted
// (BTCUSD, NVDA, XAUUSD, SPX…) → 1. Forex: convert the quote ccy to USD using the live
// rate cache (window._forexUsdRates), with safe fallbacks so we're never ~150x off.
function _todayUsdPerQuote(o){
  if(!o || o.asset!=='forex') return 1;
  var sym=(o.sym||'').toUpperCase().replace(/[\/\-]/g,'');
  if(sym.length<6) return 1;
  var quote=sym.slice(3,6);
  if(quote==='USD') return 1;
  var R=window._forexUsdRates||{};
  if(R[quote+'USD']>0) return R[quote+'USD'];      // GBPUSD, AUDUSD, EURUSD, NZDUSD …
  if(R['USD'+quote]>0) return 1/R['USD'+quote];    // USDJPY, USDCAD, USDCHF …
  var def={JPY:1/155, CAD:1/1.37, CHF:1/0.90, AUD:0.66, NZD:0.60, GBP:1.27, EUR:1.08, INR:1/83, CNH:1/7.2, MXN:1/17};
  return def[quote]!=null?def[quote]:1;
}
function _todayRiskModel(o){
  var entry=parseFloat(o&&o.entry)||0, sl=parseFloat(o&&o.sl)||0;
  var slDist=Math.abs(entry-sl)||0;
  var fx=_todayUsdPerQuote(o);
  var spreadFrac = {crypto:0.0005, stock:0.0005, forex:0.0001, commodity:0.0005, index:0.0005}[(o&&o.asset)||'']||0.0005;
  var spreadUnits = (o&&o.spreadCost!=null && o.spreadCost>0) ? o.spreadCost : entry*spreadFrac;
  var feeRate = (o&&o.asset)==='crypto'?0.001 : (o&&o.asset)==='stock'?0.0005 : 0.00003;
  var slipFrac = (o&&o.asset)==='forex'?0.00007:0.0004;
  var riskPerUnit = (slDist + spreadUnits + (entry*feeRate) + (entry*slipFrac)) * fx;
  return {entry:entry, slDist:slDist, fx:fx, spreadUnits:spreadUnits, feeRate:feeRate, slipFrac:slipFrac, riskPerUnit:riskPerUnit};
}
function _todaySizeTrade(o, acct, riskPct){
  var entry=parseFloat(o.entry)||0, sl=parseFloat(o.sl)||0, tp1=parseFloat(o.tp)||0;
  var rm=_todayRiskModel(o), slDist=rm.slDist;
  var fx=rm.fx;                                 // USD per 1 unit of quote currency
  var riskD=(acct||0)*((riskPct||1)/100);       // USD the trader risks
  var unitsRaw = (rm.riskPerUnit>0) ? riskD/rm.riskPerUnit : 0; // instrument units whose FINAL loss incl costs fits riskD
  var LOT = _todayLotUnits(o);             // {cs, stepUnits, minUnits} — broker step/min in units
  // ── SAFETY GUARD: unknown commodity contract size ──────────────────────────
  // When LOT.nullCs is true the contract size is unknown (null).  Computing
  // lots = units / null = Infinity and tradeable = units>=0 = true would allow
  // the trade to be queued and sent to MT5 at a catastrophically wrong size.
  // Return early with tradeable:false and a clear reason instead.
  if(LOT.nullCs){
    return { units:0, lots:0, contractSize:null, notional:0, tradeable:false,
             minLot:0, riskPctReq:(riskPct||1), netLoss:0, netTP1:0,
             grossRisk:0, rr:0, leveraged:true, lev:1, levReal:false, marginReq:0,
             riskPctOfAcct:0, notionalPctOfAcct:0, spreadD:0, feeD:0, slipD:0, costD:0,
             unitLabel:'—', sizeReason:'contract size unknown — cannot size safely' };
  }
  // Round DOWN to the broker lot step (in units) so actual risk never EXCEEDS the target.
  // Epsilon guards floating-point boundaries (e.g. 999.9999 that should be 1000).
  var units = LOT.stepUnits>0 ? Math.floor(unitsRaw/LOT.stepUnits + 1e-9)*LOT.stepUnits : unitsRaw;
  units = parseFloat(Math.max(0,units).toFixed(8));
  var lots = units/LOT.cs;                  // real broker lots (this is what MT5 receives)
  var tradeable = units>0 && units>=LOT.minUnits;
  var notional = units*entry*fx;           // USD position value
  // Broker costs
  var spreadD = rm.spreadUnits*units*fx;   // all costs in USD (fx converts quote→USD)
  var feeD = notional*rm.feeRate;          // notional already USD
  var slipD = entry*rm.slipFrac*units*fx;
  var costD = spreadD+feeD+slipD;
  var grossRisk = units*slDist*fx;         // USD risk after lot rounding
  var netLoss = grossRisk+costD;
  var grossTP1 = tp1?Math.abs(tp1-entry)*units*fx:0;   // USD
  var netTP1 = grossTP1-costD;
  var rr = netLoss>0 ? netTP1/netLoss : 0;
  var unitLabel;
  if(o.asset==='forex'){ unitLabel=lots.toFixed(2)+' lots'; }
  else if(o.asset==='crypto'){ unitLabel=(units>=1?units.toFixed(4):units.toFixed(6))+' units'; }
  else if(o.asset==='index'){ unitLabel=lots.toFixed(2)+' contracts'; }
  else if(o.asset==='commodity'){ unitLabel=lots.toFixed(2)+' lots'; }
  else { var sh=Math.round(units); unitLabel=sh.toLocaleString()+(sh===1?' share':' shares'); }
  // Cash actually committed: stocks are unlevered; MT5-style crypto/forex/index/
  // commodity products use the selected broker leverage for margin. Max loss is
  // still controlled only by the stop and position size, not by leverage.
  var leveraged = o.asset!=='stock';
  var lev = leveraged ? (window._todayLeverage||100) : 1;
  var marginReq = notional/lev;
  return { units:units, lots:lots, contractSize:LOT.cs, notional:notional, tradeable:tradeable, minLot:LOT.minUnits, riskPctReq:(riskPct||1),
           netLoss:netLoss, netTP1:netTP1, grossRisk:grossRisk, rr:rr,
           leveraged:leveraged, lev:lev, levReal:!!window._todayLeverageReal, marginReq:marginReq,
           riskPctOfAcct: acct>0?(netLoss/acct*100):0,   /* net of costs — matches the $ max-loss & the plan totals */
           notionalPctOfAcct: acct>0?(notional/acct*100):0,
           spreadD:spreadD, feeD:feeD, slipD:slipD, costD:costD, unitLabel:unitLabel };
}
function _forexUsdRate(counter){
  // Returns the multiplier to convert pip value from counter currency to USD.
  // For counter=JPY: 1 pip = 0.01 JPY * 100k = 1000 JPY. USD value = 1000 / USDJPY
  // For counter=GBP: 1 pip = 0.0001 GBP * 100k = 10 GBP. USD value = 10 * GBPUSD
  // Returns null for unknown quote currencies (ZAR, TRY, NOK, SEK, DKK, HKD, SGD …)
  // so callers can refuse to size rather than silently using rate=1 (10–32× off).
  var r=window._forexUsdRates||{};
  switch(counter){
    case 'USD': return 1;
    case 'JPY': return r.USDJPY ? 1/r.USDJPY : 1/150;
    case 'GBP': return r.GBPUSD || 1.27;
    case 'EUR': return r.EURUSD || 1.08;
    case 'CHF': return r.USDCHF ? 1/r.USDCHF : 1/0.9;
    case 'AUD': return r.AUDUSD || 0.67;
    case 'NZD': return r.NZDUSD || 0.61;
    case 'CAD': return r.USDCAD ? 1/r.USDCAD : 1/1.35;
    case 'INR': return r.USDINR ? 1/r.USDINR : 1/83;
    case 'CNH': return r.USDCNH ? 1/r.USDCNH : 1/7.2;
    case 'MXN': return r.USDMXN ? 1/r.USDMXN : 1/17;
    default: return null; // unknown quote currency — caller must refuse to size
  }
}