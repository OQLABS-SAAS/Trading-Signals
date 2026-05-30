#!/usr/bin/env python3
"""Replace mock data sections in Agent tab with real API calls."""
import re

path = '/Users/oq/Documents/trading-signals-saas/static/index-v2-prototype.html'

with open(path, 'r') as f:
    content = f.read()

original_len = len(content)

# ── 1. Delete mock data arrays (_agentClientData, _agentPositions, _agentHistory) ──
old_mock = '''var _agentOpenCount = 0;

// Agent data — mock client accounts for demo
var _agentClientData = {'''

new_mock = '''var _agentOpenCount = 0;

// Agent data — runtime cache populated from API
var _agentClientData = {};'''

# Find the mock data section: from "var _agentOpenCount = 0;" through the end of _agentHistory array
mock_start = content.find('var _agentOpenCount = 0;')
if mock_start == -1:
    print("ERROR: Could not find _agentOpenCount")
    exit(1)

# Find the end of _agentHistory array (the '];' after the last entry)
# Search for "// Agent SVG helpers" which comes right after
svg_helpers_marker = '// Agent SVG helpers'
svg_idx = content.find(svg_helpers_marker, mock_start)
if svg_idx == -1:
    print("ERROR: Could not find SVG helpers marker")
    exit(1)

# Find the last '];' before the SVG helpers marker
history_end = content.rfind('];', mock_start, svg_idx)
if history_end == -1:
    print("ERROR: Could not find end of _agentHistory")
    exit(1)

# Replace from _agentOpenCount through end of history array
old_section = content[mock_start:history_end+2]
new_section = '''var _agentOpenCount = 0;

// Agent data — runtime cache populated from API
var _agentClientData = {};

// Agent SVG helpers'''

content = content.replace(old_section, new_section, 1)
print("Step 1: Deleted mock data arrays")

# ── 2. Replace positions section ──
old_positions = '''  if(name === 'positions'){
    var rows = _agentPositions.map(function(p){
      var c = _agentClientData[p.client] || {name:p.client,initials:'??'};
      var pnlStr = _agentPnlStr(p.pnl), pnlColor = _agentPnlColor(p.pnl);
      return '<tr data-client="'+p.client+'">'
        + '<td data-label="Client"><span class="agent-client-badge">'+c.initials+'</span> '+c.name+'</td>'
        + '<td data-label="Symbol" style="font-family:var(--mono);">'+p.symbol+'</td>'
        + '<td data-label="Side"><span class="agent-side-badge agent-'+(p.side.toLowerCase())+'">'+p.side+'</span></td>'
        + '<td data-label="Entry" style="font-family:var(--mono);">'+p.entry+'</td>'
        + '<td data-label="Current" style="font-family:var(--mono);">'+p.current+'</td>'
        + '<td data-label="P&amp;L" data-tip="'+(p.pnl>0?'Profit of $'+p.pnl.toFixed(2)+'. This trade is profitable.':p.pnl<0?'Loss of $'+Math.abs(p.pnl).toFixed(2)+'. This trade is losing.':'Break even.')+'" style="font-family:var(--mono);color:'+pnlColor+';">'+pnlStr+'</td>'
        + '<td data-label="Duration" data-tip="This trade has been open for '+p.dur+'.">'+p.dur+'</td>'
        + '</tr>';
    }).join('');
    panel.innerHTML = '<div class="agent-table-wrap"><table class="agent-data-table"><thead><tr>'
      + '<th data-tip="The client who owns this position">Client</th>'
      + '<th data-tip="Trading instrument ticker">Symbol</th>'
      + '<th data-tip="Buy (long) or Sell (short)">Side</th>'
      + '<th data-tip="Price at which the trade was opened">Entry</th>'
      + '<th data-tip="Current market price">Current</th>'
      + '<th data-tip="Profit &amp; Loss. Green = profitable, red = losing">P&amp;L</th>'
      + '<th data-tip="How long the trade has been open">Duration</th>'
      + '</tr></thead><tbody>'+rows+'</tbody></table></div>';
  }'''

new_positions = r"""  if(name === 'positions'){
    panel.innerHTML = '<div class="agent-greet-card" style="display:flex;align-items:center;justify-content:center;min-height:160px;"><div style="text-align:center;"><div class="agent-loading-spinner" style="width:32px;height:32px;border:3px solid var(--s2);border-top-color:var(--gold);border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px;"></div><p style="color:var(--t2);">Loading positions&hellip;</p></div></div>';
    var data = await dvFetch('/api/trading-agent/positions');
    if(!data){
      panel.innerHTML = '<div class="agent-greet-card"><h2>Could not load positions</h2><p>Check your connection and try again.</p><button class="agent-connect-btn" onclick="_agentSwitchSubtab(\'positions\')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0115.36-6.36L21 8M3 22v-6h6M21 12a9 9 0 01-15.36 6.36L3 16"/></svg> Retry</button></div>';
      _dvToast('Failed to load positions');
      return;
    }
    var positions = (data.positions && Array.isArray(data.positions)) ? data.positions : [];
    if(positions.length === 0){
      panel.innerHTML = '<div class="agent-greet-card"><h2>No open positions</h2><p>There are no open positions across your connected accounts right now.</p><button class="agent-connect-btn" onclick="_agentSwitchSubtab(\'accounts\')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> Manage Accounts</button></div>';
      return;
    }
    var rows = positions.map(function(p){
      var pnlStr = _agentPnlStr(p.pnl), pnlColor = _agentPnlColor(p.pnl);
      var clientName = p.client_name || p.client || 'Unknown';
      var clientInit = p.client_initials || (clientName.split(' ').map(function(w){return w[0];}).join('').substring(0,2).toUpperCase());
      return '<tr data-client="'+(p.client||'')+'">'
        + '<td data-label="Client"><span class="agent-client-badge">'+clientInit+'</span> '+clientName+'</td>'
        + '<td data-label="Symbol" style="font-family:var(--mono);">'+p.symbol+'</td>'
        + '<td data-label="Side"><span class="agent-side-badge agent-'+((p.side||'').toLowerCase())+'">'+(p.side||'')+'</span></td>'
        + '<td data-label="Entry" style="font-family:var(--mono);">'+(p.entry||'')+'</td>'
        + '<td data-label="Current" style="font-family:var(--mono);">'+(p.current||'')+'</td>'
        + '<td data-label="P&amp;L" data-tip="'+(p.pnl>0?'Profit of $'+p.pnl.toFixed(2)+'. This trade is profitable.':p.pnl<0?'Loss of $'+Math.abs(p.pnl).toFixed(2)+'. This trade is losing.':'Break even.')+'" style="font-family:var(--mono);color:'+pnlColor+';">'+pnlStr+'</td>'
        + '<td data-label="Duration" data-tip="This trade has been open for '+(p.dur||p.duration||'')+'.">'+(p.dur||p.duration||'')+'</td>'
        + '</tr>';
    }).join('');
    panel.innerHTML = '<div class="agent-table-wrap"><table class="agent-data-table"><thead><tr>'
      + '<th data-tip="The client who owns this position">Client</th>'
      + '<th data-tip="Trading instrument ticker">Symbol</th>'
      + '<th data-tip="Buy (long) or Sell (short)">Side</th>'
      + '<th data-tip="Price at which the trade was opened">Entry</th>'
      + '<th data-tip="Current market price">Current</th>'
      + '<th data-tip="Profit &amp; Loss. Green = profitable, red = losing">P&amp;L</th>'
      + '<th data-tip="How long the trade has been open">Duration</th>'
      + '</tr></thead><tbody>'+rows+'</tbody></table></div>';
  }"""

if old_positions in content:
    content = content.replace(old_positions, new_positions, 1)
    print("Step 2: Replaced positions section")
else:
    print("ERROR: Could not find positions section")
    # Try to find partial match for debugging
    idx = content.find("if(name === 'positions')")
    print(f"  Nearest match at offset {idx}")

# ── 3. Replace history section ──
old_history = '''  else if(name === 'history'){
    var hrows = _agentHistory.map(function(h){
      var c = _agentClientData[h.client] || {name:h.client};
      var pnlStr = _agentPnlStr(h.pnl), pnlColor = _agentPnlColor(h.pnl);
      var rrDisplay = h.rr > 0 ? h.rr.toFixed(1) : '\\u2014';
      return '<tr data-account="'+c.name+'" data-symbol="'+h.symbol+'" data-outcome="'+h.outcome+'" data-date="'+h.date+'">'
        + '<td data-label="Date">'+h.date+'</td>'
        + '<td data-label="Client">'+c.name+'</td>'
        + '<td data-label="Symbol" style="font-family:var(--mono);">'+h.symbol+'</td>'
        + '<td data-label="Side"><span class="agent-side-badge agent-'+(h.side.toLowerCase())+'">'+h.side+'</span></td>'
        + '<td data-label="Entry" style="font-family:var(--mono);">'+h.entry+'</td>'
        + '<td data-label="Exit" style="font-family:var(--mono);">'+h.exit+'</td>'
        + '<td data-label="P&amp;L" data-tip="'+(h.pnl>0?'Profit of $'+h.pnl.toFixed(2):h.pnl<0?'Loss of $'+Math.abs(h.pnl).toFixed(2):'Break even')+'" style="font-family:var(--mono);color:'+pnlColor+';">'+pnlStr+'</td>'
        + '<td data-label="R:R" data-tip="Risk-to-Reward: '+rrDisplay+'. '+(h.rr>=2?'Excellent.':h.rr>=1.5?'Good.':h.rr>0?'Below target.':'Trade closed at a loss.')+'" style="font-family:var(--mono);">'+rrDisplay+'</td>'
        + '<td data-label="Outcome" data-tip="'+(h.outcome==='win'?'WIN \\u2014 This trade closed at a profit.':h.outcome==='loss'?'LOSS \\u2014 This trade closed at a loss.':'BREAK EVEN \\u2014 No meaningful gain or loss.')+'" style="text-align:center;">'+_agentOutcomeSvg(h.outcome)+'</td>'
        + '</tr>';
    }).join('');
    var hSymbols = Array.from(new Set(_agentHistory.map(function(h){return h.symbol;}))).sort();
    panel.innerHTML = '<div class="agent-filter-bar">'
      + '<select class="agent-filter-select" id="agentHistAcct" onchange="_agentApplyHistFilters()"><option value="all">All Accounts</option>'
      + clients.map(function(c){return '<option value="'+c.name+'">'+c.name+'</option>';}).join('')
      + '</select>'
      + '<select class="agent-filter-select" id="agentHistDate" onchange="_agentApplyHistFilters()"><option value="all">All Time</option><option value="week">This Week</option><option value="month">This Month</option><option value="3months">Last 3 Months</option></select>'
      + '<select class="agent-filter-select" id="agentHistSym" onchange="_agentApplyHistFilters()"><option value="all">All Symbols</option>'
      + hSymbols.map(function(s){return '<option value="'+s+'">'+s+'</option>';}).join('')
      + '</select>'
      + '<select class="agent-filter-select" id="agentHistOut" onchange="_agentApplyHistFilters()"><option value="all">All Outcomes</option><option value="win">Win</option><option value="loss">Loss</option><option value="be">Break Even</option></select>'
      + '<button class="agent-export-btn" onclick="_agentExportCSV()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg> Export CSV</button>'
      + '</div>'
      + '<div class="agent-table-wrap"><table class="agent-data-table" id="agentHistTable"><thead><tr>'
      + '<th data-tip="Date the trade was closed">Date</th>'
      + '<th data-tip="Client account that executed the trade">Client</th>'
      + '<th data-tip="Trading instrument">Symbol</th>'
      + '<th data-tip="Direction of the trade">Side</th>'
      + '<th data-tip="Entry price when trade was opened">Entry</th>'
      + '<th data-tip="Exit price when trade was closed">Exit</th>'
      + '<th data-tip="Profit &amp; Loss. Green = profitable trade.">P&amp;L</th>'
      + '<th data-tip="Risk-to-Reward ratio. For every $1 risked, you made $X. Above 1.5 is good.">R:R</th>'
      + '<th data-tip="Trade result">Outcome</th>'
      + '</tr></thead><tbody>'+hrows+'</tbody></table></div>';
  }'''

new_history = r"""  else if(name === 'history'){
    panel.innerHTML = '<div class="agent-greet-card" style="display:flex;align-items:center;justify-content:center;min-height:160px;"><div style="text-align:center;"><div class="agent-loading-spinner" style="width:32px;height:32px;border:3px solid var(--s2);border-top-color:var(--gold);border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px;"></div><p style="color:var(--t2);">Loading trade history&hellip;</p></div></div>';
    var histData = await dvFetch('/api/trading-agent/trades');
    if(!histData){
      panel.innerHTML = '<div class="agent-greet-card"><h2>Could not load trade history</h2><p>Check your connection and try again.</p><button class="agent-connect-btn" onclick="_agentSwitchSubtab(\'history\')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0115.36-6.36L21 8M3 22v-6h6M21 12a9 9 0 01-15.36 6.36L3 16"/></svg> Retry</button></div>';
      _dvToast('Failed to load trade history');
      return;
    }
    var trades = (histData.trades && Array.isArray(histData.trades)) ? histData.trades : [];
    if(trades.length === 0){
      panel.innerHTML = '<div class="agent-greet-card"><h2>No trade history yet</h2><p>Closed trades will appear here once positions are closed.</p><button class="agent-connect-btn" onclick="_agentSwitchSubtab(\'positions\')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> View Open Positions</button></div>';
      return;
    }
    var hrows = trades.map(function(h){
      var clientName = h.client_name || h.client || 'Unknown';
      var pnlStr = _agentPnlStr(h.pnl), pnlColor = _agentPnlColor(h.pnl);
      var rrDisplay = h.rr > 0 ? h.rr.toFixed(1) : '\u2014';
      return '<tr data-account="'+clientName+'" data-symbol="'+h.symbol+'" data-outcome="'+h.outcome+'" data-date="'+h.date+'">'
        + '<td data-label="Date">'+h.date+'</td>'
        + '<td data-label="Client">'+clientName+'</td>'
        + '<td data-label="Symbol" style="font-family:var(--mono);">'+h.symbol+'</td>'
        + '<td data-label="Side"><span class="agent-side-badge agent-'+((h.side||'').toLowerCase())+'">'+(h.side||'')+'</span></td>'
        + '<td data-label="Entry" style="font-family:var(--mono);">'+(h.entry||'')+'</td>'
        + '<td data-label="Exit" style="font-family:var(--mono);">'+(h.exit||'')+'</td>'
        + '<td data-label="P&amp;L" data-tip="'+(h.pnl>0?'Profit of $'+h.pnl.toFixed(2):h.pnl<0?'Loss of $'+Math.abs(h.pnl).toFixed(2):'Break even')+'" style="font-family:var(--mono);color:'+pnlColor+';">'+pnlStr+'</td>'
        + '<td data-label="R:R" data-tip="Risk-to-Reward: '+rrDisplay+'. '+(h.rr>=2?'Excellent.':h.rr>=1.5?'Good.':h.rr>0?'Below target.':'Trade closed at a loss.')+'" style="font-family:var(--mono);">'+rrDisplay+'</td>'
        + '<td data-label="Outcome" data-tip="'+(h.outcome==='win'?'WIN \u2014 This trade closed at a profit.':h.outcome==='loss'?'LOSS \u2014 This trade closed at a loss.':'BREAK EVEN \u2014 No meaningful gain or loss.')+'" style="text-align:center;">'+_agentOutcomeSvg(h.outcome)+'</td>'
        + '</tr>';
    }).join('');
    var hSymbols = Array.from(new Set(trades.map(function(h){return h.symbol;}))).sort();
    var hAccounts = Array.from(new Set(trades.map(function(h){return h.client_name || h.client || 'Unknown';}))).sort();
    panel.innerHTML = '<div class="agent-filter-bar">'
      + '<select class="agent-filter-select" id="agentHistAcct" onchange="_agentApplyHistFilters()"><option value="all">All Accounts</option>'
      + hAccounts.map(function(c){return '<option value="'+c+'">'+c+'</option>';}).join('')
      + '</select>'
      + '<select class="agent-filter-select" id="agentHistDate" onchange="_agentApplyHistFilters()"><option value="all">All Time</option><option value="week">This Week</option><option value="month">This Month</option><option value="3months">Last 3 Months</option></select>'
      + '<select class="agent-filter-select" id="agentHistSym" onchange="_agentApplyHistFilters()"><option value="all">All Symbols</option>'
      + hSymbols.map(function(s){return '<option value="'+s+'">'+s+'</option>';}).join('')
      + '</select>'
      + '<select class="agent-filter-select" id="agentHistOut" onchange="_agentApplyHistFilters()"><option value="all">All Outcomes</option><option value="win">Win</option><option value="loss">Loss</option><option value="be">Break Even</option></select>'
      + '<button class="agent-export-btn" onclick="_agentExportCSV()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg> Export CSV</button>'
      + '</div>'
      + '<div class="agent-table-wrap"><table class="agent-data-table" id="agentHistTable"><thead><tr>'
      + '<th data-tip="Date the trade was closed">Date</th>'
      + '<th data-tip="Client account that executed the trade">Client</th>'
      + '<th data-tip="Trading instrument">Symbol</th>'
      + '<th data-tip="Direction of the trade">Side</th>'
      + '<th data-tip="Entry price when trade was opened">Entry</th>'
      + '<th data-tip="Exit price when trade was closed">Exit</th>'
      + '<th data-tip="Profit &amp; Loss. Green = profitable trade.">P&amp;L</th>'
      + '<th data-tip="Risk-to-Reward ratio. For every $1 risked, you made $X. Above 1.5 is good.">R:R</th>'
      + '<th data-tip="Trade result">Outcome</th>'
      + '</tr></thead><tbody>'+hrows+'</tbody></table></div>';
  }"""

if old_history in content:
    content = content.replace(old_history, new_history, 1)
    print("Step 3: Replaced history section")
else:
    print("ERROR: Could not find history section")
    idx = content.find("else if(name === 'history')")
    print(f"  Nearest match at offset {idx}")

# ── 4. Replace reports section ──
old_reports = '''  else if(name === 'reports'){
    panel.innerHTML = '<div class="agent-report-controls">'
      + '<div><label>Client</label><select class="agent-report-select" id="agentReportClient">'
      + '<option value="all">All Clients</option>'
      + clients.map(function(c){return '<option value="'+c.id+'">'+c.name+'</option>';}).join('')
      + '</select></div>'
      + '<div><label>Month</label><select class="agent-report-select" id="agentReportMonth">'
      + '<option value="2026-05" selected>May 2026</option><option value="2026-04">April 2026</option><option value="2026-03">March 2026</option>'
      + '</select></div>'
      + '<button class="agent-generate-btn" onclick="_agentGenerateReport()">Generate</button></div>'
      + '<div class="agent-metrics-grid" id="agentMetricsGrid"></div>'
      + '<button class="agent-download-btn" id="agentDownloadBtn" onclick="_agentDownloadReport()">'
      + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg> Download CSV</button>';
  }'''

new_reports = r"""  else if(name === 'reports'){
    panel.innerHTML = '<div class="agent-greet-card" style="display:flex;align-items:center;justify-content:center;min-height:160px;"><div style="text-align:center;"><div class="agent-loading-spinner" style="width:32px;height:32px;border:3px solid var(--s2);border-top-color:var(--gold);border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px;"></div><p style="color:var(--t2);">Loading analytics&hellip;</p></div></div>';
    var reportData = await dvFetch('/api/trading-agent/analytics');
    if(!reportData){
      panel.innerHTML = '<div class="agent-greet-card"><h2>Could not load analytics</h2><p>Check your connection and try again.</p><button class="agent-connect-btn" onclick="_agentSwitchSubtab(\'reports\')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0115.36-6.36L21 8M3 22v-6h6M21 12a9 9 0 01-15.36 6.36L3 16"/></svg> Retry</button></div>';
      _dvToast('Failed to load analytics');
      return;
    }
    var hasData = reportData && (reportData.trade_count || reportData.tradeCount || reportData.win_rate || reportData.winRate || reportData.total_return || reportData.totalReturn);
    if(!hasData){
      panel.innerHTML = '<div class="agent-greet-card"><h2>No data available yet</h2><p>Performance metrics and analytics will appear here once trading activity is recorded.</p><button class="agent-connect-btn" onclick="_agentSwitchSubtab(\'positions\')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> Take a Trade</button></div>';
      return;
    }
    _agentReportData = reportData;
    var base = {
      openingBalance: reportData.opening_balance || reportData.openingBalance || 0,
      closingBalance: reportData.closing_balance || reportData.closingBalance || 0,
      totalReturn: reportData.total_return || reportData.totalReturn || 0,
      totalReturnPct: reportData.total_return_pct || reportData.totalReturnPct || 0,
      tradeCount: reportData.trade_count || reportData.tradeCount || 0,
      wins: reportData.wins || 0,
      losses: reportData.losses || 0,
      be: reportData.be || 0,
      winRate: reportData.win_rate || reportData.winRate || 0,
      profitFactor: reportData.profit_factor || reportData.profitFactor || 0,
      avgRR: reportData.avg_rr || reportData.avgRR || 0,
      sharpe: reportData.sharpe || reportData.sharpe_ratio || 0
    };
    var sign = base.totalReturn >= 0 ? '+' : '';
    var returnColor = base.totalReturn >= 0 ? 'var(--grn)' : 'var(--red)';
    var metricsHtml = [
      {l:'Opening Balance',v:'$'+base.openingBalance.toLocaleString(),s:'Start of period',t:'The account balance at the beginning of the reporting period'},
      {l:'Closing Balance',v:'$'+base.closingBalance.toLocaleString(),s:'End of period',t:'The account balance at the end of the reporting period'},
      {l:'Total Return',v:sign+'$'+Math.abs(base.totalReturn).toLocaleString(),s:sign+base.totalReturnPct.toFixed(2)+'%',t:'Absolute and percentage return over the reporting period',c:returnColor},
      {l:'Trade Count',v:''+base.tradeCount,s:base.wins+'W / '+base.losses+'L / '+base.be+'BE',t:'Total number of trades closed during this period'},
      {l:'Win Rate',v:base.winRate.toFixed(1)+'%',s:base.wins+' of '+base.tradeCount+' trades',t:'Percentage of trades that closed in profit'},
      {l:'Profit Factor',v:base.profitFactor.toFixed(2),s:'Gross profit / gross loss',t:'Ratio of gross profit to gross loss. Above 1.5 is good'},
      {l:'Avg R:R',v:base.avgRR.toFixed(2),s:'Avg reward per $1 risk',t:'Average Risk-to-Reward ratio. Above 1.5 is considered good'},
      {l:'Sharpe Ratio',v:base.sharpe.toFixed(2),s:'Risk-adjusted return',t:'Sharpe Ratio measures return per unit of risk. Above 2.0 is very good'}
    ].map(function(m){
      return '<div class="agent-metric-card" data-tip="'+m.t+'"><div class="agent-label">'+m.l+'</div><div class="agent-value" style="'+(m.c||'')+'">'+m.v+'</div><div class="agent-sub">'+m.s+'</div></div>';
    }).join('');
    panel.innerHTML = '<div class="agent-metrics-grid agent-show" style="display:grid;">'+metricsHtml+'</div>'
      + '<button class="agent-download-btn agent-show" onclick="_agentDownloadReport()">'
      + '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg> Download CSV</button>';
  }"""

if old_reports in content:
    content = content.replace(old_reports, new_reports, 1)
    print("Step 4: Replaced reports section")
else:
    print("ERROR: Could not find reports section")
    idx = content.find("else if(name === 'reports')")
    print(f"  Nearest match at offset {idx}")

# ── 5. Replace accounts section ──
old_accounts_start = '''  else if(name === 'accounts'){
    var accts = clients.map(function(a){
      return '<div class="agent-acct-card" data-tip="'+a.name+' \\u2014 Balance: '+a.balance+' | Status: '+(a.status.charAt(0).toUpperCase()+a.status.slice(1))+' | Broker: '+a.broker+'">'
        + '<div class="agent-acct-header"><div class="agent-acct-av">'+a.initials+'</div><div class="agent-acct-name">'+a.name+'</div>'+(a.status==='online'?'<svg width="8" height="8"><circle cx="4" cy="4" r="4" fill="#c9a84c"/></svg>':a.status==='offline'?'<svg width="8" height="8"><circle cx="4" cy="4" r="4" fill="#e8706e"/></svg>':'<svg width="8" height="8"><circle cx="4" cy="4" r="4" fill="#d4a843"/></svg>')+'</div>''
        + '<div class="agent-acct-details">''
        + '<div class="agent-acct-row"><span class="agent-acct-label">Broker</span><span class="agent-acct-value">'+a.broker+'</span></div>''
        + '<div class="agent-acct-row"><span class="agent-acct-label">Server</span><span class="agent-acct-value">'+a.server+'</span></div>''
        + '<div class="agent-acct-row"><span class="agent-acct-label">Login</span><span class="agent-acct-value agent-mono">'+a.login+'</span></div>''
        + '<div class="agent-acct-row"><span class="agent-acct-label">Balance</span><span class="agent-acct-value agent-mono">'+a.balance+'</span></div>''
        + '<div class="agent-acct-row"><span class="agent-acct-label">Equity</span><span class="agent-acct-value agent-mono">'+a.equity+'</span></div>''
        + '<div class="agent-acct-row"><span class="agent-acct-label">Leverage</span><span class="agent-acct-value">'+a.leverage+'</span></div>''
        + '</div>''
        + '<div class="agent-acct-actions">''
        + '<button class="agent-acct-btn agent-edit" onclick="_agentToggleEdit(this,\\''+a.id+'\\'')"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Edit</button>''
        + '<button class="agent-acct-btn agent-sync" onclick="_agentSyncAcct(this,\\''+a.id+'\\'')"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0115.36-6.36L21 8M3 22v-6h6M21 12a9 9 0 01-15.36 6.36L3 16"/></svg> Sync</button>''
        + '<button class="agent-acct-btn agent-disconnect" onclick="_agentConfirmDisc(this,\\''+a.id+'\\'')"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.68 13.31a6 6 0 003.41-2.25M14 6.33A7.98 7.98 0 002 12a7.98 7.98 0 004.07 7.1"/><path d="M16 17.67A7.98 7.98 0 0022 12a7.98 7.98 0 00-4-6.91"/><line x1="2" y1="2" x2="22" y2="22"/></svg> Disconnect</button>''
        + '</div>''
        + '<div class="agent-inline-edit"><label>Client Name</label><input type="text" value="'+a.name+'"><label>Login</label><input type="text" value="'+a.login+'"><label>Server</label><input type="text" value="'+a.server+'"><div class="agent-inline-row"><button class="agent-acct-btn agent-sync" onclick="_agentSaveEdit(this,\\''+a.id+'\\'')">Save</button><button class="agent-acct-btn agent-edit" onclick="_agentCancelEdit(this)">Cancel</button></div></div>''
        + '<div class="agent-confirm-disc">Disconnect this account?<div class="agent-confirm-row"><button class="agent-confirm-btn agent-confirm" onclick="_agentDoDisc(this,\\''+a.id+'\\'')">Confirm</button><button class="agent-confirm-btn agent-cancel" onclick="_agentCancelDisc(this)">Cancel</button></div></div>''
        + '</div>';'''

# Find accounts section start
acct_start_idx = content.find('else if(name === \'accounts\'){')
if acct_start_idx == -1:
    print("ERROR: Could not find accounts section")
else:
    # Find the closing of _agentRenderPanel: "}\n\n// Agent client selection"
    acct_close_marker = '}\n\n// Agent client selection\nfunction _agentSelectClient(clientId){'
    acct_close_idx = content.find(acct_close_marker, acct_start_idx)
    if acct_close_idx == -1:
        print("ERROR: Could not find accounts section end")
    else:
        old_accounts_full = content[acct_start_idx:acct_close_idx + len('}')]
        
        new_accounts = r"""  else if(name === 'accounts'){
    panel.innerHTML = '<div class="agent-greet-card" style="display:flex;align-items:center;justify-content:center;min-height:160px;"><div style="text-align:center;"><div class="agent-loading-spinner" style="width:32px;height:32px;border:3px solid var(--s2);border-top-color:var(--gold);border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 12px;"></div><p style="color:var(--t2);">Loading accounts&hellip;</p></div></div>';
    var acctData = await dvFetch('/api/trading-agent/accounts');
    if(!acctData){
      panel.innerHTML = '<div class="agent-greet-card"><h2>Could not load accounts</h2><p>Check your connection and try again.</p><button class="agent-connect-btn" onclick="_agentSwitchSubtab(\'accounts\')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0115.36-6.36L21 8M3 22v-6h6M21 12a9 9 0 01-15.36 6.36L3 16"/></svg> Retry</button></div>';
      _dvToast('Failed to load accounts');
      return;
    }
    var accounts = (acctData.accounts && Array.isArray(acctData.accounts)) ? acctData.accounts : [];
    if(accounts.length > 0){
      accounts.forEach(function(a){
        _agentClientData[a.id] = a;
      });
    }
    var connectFormHtml = '<div class="agent-connect-form" id="agentConnectForm"><h3>Connect New Account</h3><div class="agent-form-grid">'
      + '<div><label>Client Name</label><input type="text" id="agentNewName" placeholder="e.g. Orion Capital"></div>'
      + '<div><label>Broker</label><select id="agentNewBroker"><option>MetaTrader 5</option><option>cTrader</option></select></div>'
      + '<div><label>Server</label><input type="text" id="agentNewServer" placeholder="e.g. ICMarkets-Live"></div>'
      + '<div><label>Login</label><input type="text" id="agentNewLogin" placeholder="Account number"></div>'
      + '<div><label>Password</label><input type="password" id="agentNewPass" placeholder="Password"></div>'
      + '<div><label>Leverage</label><select id="agentNewLev"><option>1:100</option><option>1:200</option><option>1:500</option></select></div>'
      + '</div><div class="agent-form-actions"><button class="agent-acct-btn agent-edit" onclick="_agentCancelConnect()">Cancel</button><button class="agent-generate-btn" onclick="_agentAddAccount()">Connect</button></div></div>';
    if(accounts.length === 0){
      panel.innerHTML = '<div class="agent-greet-card"><h2>Connect your first MT5 account</h2><p>Link a MetaTrader 5 account to start managing positions, tracking trades, and generating reports.</p><button class="agent-connect-btn" onclick="_agentShowConnect()"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> Connect New Account</button></div>' + connectFormHtml;
      return;
    }
    var accts = accounts.map(function(a){
      return '<div class="agent-acct-card" data-tip="'+a.name+' \u2014 Balance: '+(a.balance||'N/A')+' | Status: '+((a.status||'online').charAt(0).toUpperCase()+(a.status||'online').slice(1))+' | Broker: '+(a.broker||'N/A')+'">'
        + '<div class="agent-acct-header"><div class="agent-acct-av">'+(a.initials||'??')+'</div><div class="agent-acct-name">'+a.name+'</div>'+(a.status==='online'?'<svg width="8" height="8"><circle cx="4" cy="4" r="4" fill="#c9a84c"/></svg>':a.status==='offline'?'<svg width="8" height="8"><circle cx="4" cy="4" r="4" fill="#e8706e"/></svg>':'<svg width="8" height="8"><circle cx="4" cy="4" r="4" fill="#d4a843"/></svg>')+'</div>'
        + '<div class="agent-acct-details">'
        + '<div class="agent-acct-row"><span class="agent-acct-label">Broker</span><span class="agent-acct-value">'+(a.broker||'N/A')+'</span></div>'
        + '<div class="agent-acct-row"><span class="agent-acct-label">Server</span><span class="agent-acct-value">'+(a.server||'N/A')+'</span></div>'
        + '<div class="agent-acct-row"><span class="agent-acct-label">Login</span><span class="agent-acct-value agent-mono">'+(a.login||'N/A')+'</span></div>'
        + '<div class="agent-acct-row"><span class="agent-acct-label">Balance</span><span class="agent-acct-value agent-mono">'+(a.balance||'N/A')+'</span></div>'
        + '<div class="agent-acct-row"><span class="agent-acct-label">Equity</span><span class="agent-acct-value agent-mono">'+(a.equity||a.balance||'N/A')+'</span></div>'
        + '<div class="agent-acct-row"><span class="agent-acct-label">Leverage</span><span class="agent-acct-value">'+(a.leverage||'N/A')+'</span></div>'
        + '</div>'
        + '<div class="agent-acct-actions">'
        + '<button class="agent-acct-btn agent-edit" onclick="_agentToggleEdit(this,\''+a.id+'\')"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg> Edit</button>'
        + '<button class="agent-acct-btn agent-sync" onclick="_agentSyncAcct(this,\''+a.id+'\')"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0115.36-6.36L21 8M3 22v-6h6M21 12a9 9 0 01-15.36 6.36L3 16"/></svg> Sync</button>'
        + '<button class="agent-acct-btn agent-disconnect" onclick="_agentConfirmDisc(this,\''+a.id+'\')"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.68 13.31a6 6 0 003.41-2.25M14 6.33A7.98 7.98 0 002 12a7.98 7.98 0 004.07 7.1"/><path d="M16 17.67A7.98 7.98 0 0022 12a7.98 7.98 0 00-4-6.91"/><line x1="2" y1="2" x2="22" y2="22"/></svg> Disconnect</button>'
        + '</div>'
        + '<div class="agent-inline-edit"><label>Client Name</label><input type="text" value="'+a.name+'"><label>Login</label><input type="text" value="'+(a.login||'')+'"><label>Server</label><input type="text" value="'+(a.server||'')+'"><div class="agent-inline-row"><button class="agent-acct-btn agent-sync" onclick="_agentSaveEdit(this,\''+a.id+'\')">Save</button><button class="agent-acct-btn agent-edit" onclick="_agentCancelEdit(this)">Cancel</button></div></div>'
        + '<div class="agent-confirm-disc">Disconnect this account?<div class="agent-confirm-row"><button class="agent-confirm-btn agent-confirm" onclick="_agentDoDisc(this,\''+a.id+'\')">Confirm</button><button class="agent-confirm-btn agent-cancel" onclick="_agentCancelDisc(this)">Cancel</button></div></div>'
        + '</div>';
    }).join('');
    panel.innerHTML = '<div class="agent-account-grid">'+accts+'</div>'
      + '<button class="agent-connect-btn" onclick="_agentShowConnect()"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> Connect New Account</button>'
      + connectFormHtml;
  }"""

        content = content.replace(old_accounts_full, new_accounts, 1)
        print("Step 5: Replaced accounts section")

# ── 6. Fix _agentGenerateReport to use stored data ──
# The old _agentGenerateReport uses hardcoded mock data. Update it.
old_gen_report = """function _agentGenerateReport(){
  var grid = document.getElementById('agentMetricsGrid');
  if(!grid) return;
  var base = {openingBalance:487200,closingBalance:512450,totalReturn:25250,totalReturnPct:5.18,tradeCount:47,wins:31,losses:12,be:4,winRate:66.0,profitFactor:2.14,avgRR:1.84,sharpe:1.72};
  var sign = base.totalReturn >= 0 ? '+' : '';
  grid.innerHTML = [
    {l:'Opening Balance',v:'$'+base.openingBalance.toLocaleString(),s:'Start of period',t:'The account balance at the beginning of the reporting period'},
    {l:'Closing Balance',v:'$'+base.closingBalance.toLocaleString(),s:'End of period',t:'The account balance at the end of the reporting period'},
    {l:'Total Return',v:sign+'$'+base.totalReturn.toLocaleString(),s:sign+base.totalReturnPct.toFixed(2)+'%',t:'Absolute and percentage return over the reporting period',c:'var(--grn)'},
    {l:'Trade Count',v:''+base.tradeCount,s:base.wins+'W / '+base.losses+'L / '+base.be+'BE',t:'Total number of trades closed during this period'},
    {l:'Win Rate',v:base.winRate.toFixed(1)+'%',s:base.wins+' of '+base.tradeCount+' trades',t:'Percentage of trades that closed in profit'},
    {l:'Profit Factor',v:base.profitFactor.toFixed(2),s:'Gross profit / gross loss',t:'Ratio of gross profit to gross loss. Above 1.5 is good'},
    {l:'Avg R:R',v:base.avgRR.toFixed(2),s:'Avg reward per $1 risk',t:'Average Risk-to-Reward ratio. Above 1.5 is considered good'},
    {l:'Sharpe Ratio',v:base.sharpe.toFixed(2),s:'Risk-adjusted return',t:'Sharpe Ratio measures return per unit of risk. Above 2.0 is very good'}
  ].map(function(m){
    return '<div class="agent-metric-card" data-tip="'+m.t+'"><div class="agent-label">'+m.l+'</div><div class="agent-value" style="'+(m.c||'')+'">'+m.v+'</div><div class="agent-sub">'+m.s+'</div></div>';
  }).join('');
  grid.style.display = 'grid';
  grid.classList.add('agent-show');
  var btn = document.getElementById('agentDownloadBtn');
  if(btn) btn.classList.add('agent-show');
  _agentReportData = base;
}"""

new_gen_report = """function _agentGenerateReport(){
  // Now handled directly in _agentRenderPanel via API
  _agentSwitchSubtab('reports');
}"""

if old_gen_report in content:
    content = content.replace(old_gen_report, new_gen_report, 1)
    print("Step 6: Updated _agentGenerateReport")
else:
    print("WARNING: Could not find _agentGenerateReport - may already be handled")

# ── 7. Fix showAgent default client ──
old_show_agent = "_agentActiveClient = _agentActiveClient || 'williams-capital';"
new_show_agent = "_agentActiveClient = _agentActiveClient || '';"
if old_show_agent in content:
    content = content.replace(old_show_agent, new_show_agent, 1)
    print("Step 7: Fixed showAgent default client")
else:
    print("WARNING: Could not find showAgent default client line")

# ── 8. Fix _agentAddAccount to use API instead of mock ──
old_add_account = """async function _agentAddAccount(){
  var name = (document.getElementById('agentNewName')||{}).value;
  if(!name||!name.trim()) return;
  name = name.trim();
  var initials = name.split(' ').map(function(w){return w[0];}).join('').substring(0,2).toUpperCase();
  var id = name.toLowerCase().replace(/\\s+/g,'-');
  var bal = '$'+Math.floor(Math.random()*900000+100000).toLocaleString();
  _agentClientData[id] = {id:id,initials:initials,name:name,balance:bal,drawdown:'-'+((Math.random()*10).toFixed(1))+'%',status:'online',broker:(document.getElementById('agentNewBroker')||{}).value||'MetaTrader 5',server:(document.getElementById('agentNewServer')||{}).value||'Live',login:(document.getElementById('agentNewLogin')||{}).value||'9000000',equity:bal,leverage:(document.getElementById('agentNewLev')||{}).value||'1:200'};
  _agentOpenCount++;
  _agentCancelConnect();
  await _agentRenderPanel('accounts', document.getElementById('agentPanel'));
  _agentBuildDropdown();
}"""

new_add_account = r"""async function _agentAddAccount(){
  var name = (document.getElementById('agentNewName')||{}).value;
  if(!name||!name.trim()) return;
  name = name.trim();
  var form = document.getElementById('agentConnectForm');
  var btn = form ? form.querySelector('.agent-generate-btn') : null;
  if(btn){ btn.disabled = true; btn.textContent = 'Connecting...'; }
  var payload = {
    name: name,
    broker: (document.getElementById('agentNewBroker')||{}).value||'MetaTrader 5',
    server: (document.getElementById('agentNewServer')||{}).value||'Live',
    login: (document.getElementById('agentNewLogin')||{}).value||'',
    password: (document.getElementById('agentNewPass')||{}).value||'',
    leverage: (document.getElementById('agentNewLev')||{}).value||'1:200'
  };
  var result = await dvFetch('/api/trading-agent/accounts/connect', {method:'POST',body:JSON.stringify(payload)});
  if(result && result.success){
    _dvToast('Account connected successfully');
    _agentOpenCount++;
    _agentCancelConnect();
    await _agentRenderPanel('accounts', document.getElementById('agentPanel'));
    _agentBuildDropdown();
    // Refresh overview too
    setTimeout(function(){ _agentSwitchSubtab('overview'); }, 100);
  } else {
    _dvToast(result && result.error ? result.error : 'Failed to connect account');
  }
  if(btn){ btn.disabled = false; btn.textContent = 'Connect'; }
}"""

if old_add_account in content:
    content = content.replace(old_add_account, new_add_account, 1)
    print("Step 8: Updated _agentAddAccount to use API")
else:
    print("WARNING: Could not find _agentAddAccount")

# ── Write back ──
with open(path, 'w') as f:
    f.write(content)

new_len = len(content)
print(f"Done. File size: {original_len} -> {new_len} bytes ({new_len - original_len:+d})")
print(f"Line count estimate: {content.count(chr(10))}")
