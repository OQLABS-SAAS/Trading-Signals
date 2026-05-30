/* Extract only my new functions and check them */
var _agentData = null;
var _agentTrades = null;
var _agentAccounts = null;
var _agentSub = 'dashboard';

function showAgent(sub){
  _agentSub = sub || 'dashboard';
  console.log('showAgent:', _agentSub);
}

function _agentFetchDash(){ console.log('fetch dash'); }
function _agentPopDash(d){ console.log('pop dash'); }
function _agentSubmitTrade(){ console.log('submit'); }
function _agentFetchTrades(filters){ console.log('fetch trades'); }
function _agentFilterTrades(){ console.log('filter'); }
function _agentRenderTrades(trades){ console.log('render'); }
function _agentTradeSortField(field){ console.log('sort'); }
function _agentToggleTradeDetail(idx){ console.log('toggle'); }
function _agentCloseTrade(tradeId){ console.log('close'); }
function _agentExportCSV(){ console.log('export'); }
function _agentFetchAnly(){ console.log('anly'); }
function _agentPopAnalytics(d){ console.log('pop anly'); }
function _agentFetchAccts(){ console.log('fetch accts'); }
function _agentRenderAccts(accounts){ console.log('render accts'); }
function _agentSyncAcct(id){ console.log('sync'); }
function _agentEditAcct(id){ console.log('edit'); }
function _agentSaveAcct(){ console.log('save'); }
function _agentArchiveAcct(id){ console.log('archive'); }
function _agentEscapeHTML(str){ return ''; }
