//+------------------------------------------------------------------+
//| DotVerse_EA.mq5                                                  |
//| Connects MT5 terminal to DotVerse trading signals SaaS           |
//|                                                                  |
//| SETUP (Mac / VT Markets demo):                                   |
//| 1. Copy this file to: <MT5 data folder>/MQL5/Experts/            |
//| 2. Compile in MetaEditor (F7)                                    |
//| 3. Drag onto ANY chart — timeframe and symbol do not matter      |
//| 4. In EA inputs: paste your DotVerse URL and EA secret           |
//| 5. Tick "Allow WebRequest" in MT5 Tools → Options → Expert       |
//|    Advisors, and add https://dot-verse.up.railway.app to the list|
//|                                                                  |
//| What it does every 5 seconds:                                    |
//|   PUSH  → sends account balance, equity, margin, P&L, positions  |
//|   POLL  → fetches pending orders from DotVerse                   |
//|   EXEC  → places market orders, reports fill/fail back           |
//+------------------------------------------------------------------+
#property copyright "DotVerse"
#property version   "1.00"
#property strict

//--- Inputs
input string InpBaseUrl   = "https://dot-verse.up.railway.app";  // DotVerse URL
input string InpEaSecret  = "";                                   // EA Secret (from Railway env)
input int    InpPollSecs  = 5;                                    // Poll interval (seconds)
input double InpSlippage  = 3;                                    // Slippage points

//--- Globals
int    g_timerSeconds = 0;
string g_userId       = "default";

// ── Level monitoring — track up to 50 open positions ─────────
#define MAX_TRACKED 50
ulong  g_tk[MAX_TRACKED];        // MT5 ticket
string g_tk_sym[MAX_TRACKED];    // symbol
string g_tk_dir[MAX_TRACKED];    // BUY | SELL
double g_tk_sl[MAX_TRACKED];
double g_tk_tp1[MAX_TRACKED];
double g_tk_tp2[MAX_TRACKED];
double g_tk_tp3[MAX_TRACKED];
double g_tk_hwm[MAX_TRACKED];    // high-water-mark price for trailing stop
int    g_tk_hit[MAX_TRACKED];    // bitmask: 1=SL 2=TP1 4=TP2 8=TP3
int    g_tk_count = 0;

// ── Trailing stop settings (refreshed from DotVerse every 5s) ────
bool   g_trail_on   = false;
double g_trail_pips = 50.0;

// ── Pending order TP2/TP3 lookup (by order_id before fill) ───
#define MAX_PENDING 20
long   g_pending_id[MAX_PENDING];
double g_pending_tp2[MAX_PENDING];
double g_pending_tp3[MAX_PENDING];
int    g_pending_count = 0;

//+------------------------------------------------------------------+
//| Expert initialisation                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   if (!EventSetTimer(InpPollSecs)) {
      Alert("DotVerse EA: Could not start timer.");
      return INIT_FAILED;
   }
   Print("DotVerse EA started. Polling every ", InpPollSecs, "s → ", InpBaseUrl);
   // Register any positions already open before the EA loaded
   ScanExistingPositions();
   // Immediate first cycle
   PushState();
   PollAndExecute();
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("DotVerse EA stopped.");
}

//+------------------------------------------------------------------+
//| Timer — runs every InpPollSecs seconds                            |
//+------------------------------------------------------------------+
void OnTimer()
{
   PushState();
   PollAndExecute();
   CheckLevels();
}

//+------------------------------------------------------------------+
//| Return pip size for any symbol                                    |
//| 3/5-digit pairs (EURUSD, XAUUSD, crypto): 1 pip = 10 points     |
//| 2/4-digit pairs (USDJPY): 1 pip = 10 points (same rule applies) |
//+------------------------------------------------------------------+
double PipSize(string sym)
{
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   // Odd digit counts (3, 5) = fractional pip broker — 1 pip = 10 points
   if (digits == 3 || digits == 5) return point * 10.0;
   return point;
}

//+------------------------------------------------------------------+
//| Add any currently-open MT5 positions to the tracking array       |
//| Called from OnInit so trailing applies to pre-existing trades    |
//+------------------------------------------------------------------+
void ScanExistingPositions()
{
   int total = PositionsTotal();
   for (int i = 0; i < total; i++) {
      ulong ticket = PositionGetTicket(i);
      if (ticket == 0) continue;
      // Skip if already tracked
      bool found = false;
      for (int j = 0; j < g_tk_count; j++) { if (g_tk[j] == ticket) { found = true; break; } }
      if (found) continue;
      if (g_tk_count >= MAX_TRACKED) break;
      string sym    = PositionGetString(POSITION_SYMBOL);
      long   ptype  = PositionGetInteger(POSITION_TYPE);
      double sl     = PositionGetDouble(POSITION_SL);
      double tp     = PositionGetDouble(POSITION_TP);
      double cur    = (ptype == POSITION_TYPE_BUY)
                    ? SymbolInfoDouble(sym, SYMBOL_BID)
                    : SymbolInfoDouble(sym, SYMBOL_ASK);
      int idx = g_tk_count++;
      g_tk[idx]     = ticket;
      g_tk_sym[idx] = sym;
      g_tk_dir[idx] = (ptype == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      g_tk_sl[idx]  = sl;
      g_tk_tp1[idx] = tp;
      g_tk_tp2[idx] = 0;
      g_tk_tp3[idx] = 0;
      g_tk_hwm[idx] = cur;   // start HWM at current price
      g_tk_hit[idx] = 0;
      Print("DotVerse EA: registered existing position ticket=", ticket, " ", sym, " ", g_tk_dir[idx],
            " SL=", sl, " HWM=", cur);
   }
}

//+------------------------------------------------------------------+
//| Apply trailing stop to one tracked position                       |
//+------------------------------------------------------------------+
void ApplyTrailing(int idx)
{
   if (!g_trail_on) return;
   ulong  ticket = g_tk[idx];
   string sym    = g_tk_sym[idx];
   bool   isBuy  = (g_tk_dir[idx] == "BUY");
   double pip    = PipSize(sym);
   double dist   = g_trail_pips * pip;   // trail distance in price units

   if (!PositionSelectByTicket(ticket)) return;
   double cur    = isBuy ? SymbolInfoDouble(sym, SYMBOL_BID) : SymbolInfoDouble(sym, SYMBOL_ASK);
   double curSL  = PositionGetDouble(POSITION_SL);
   double openP  = PositionGetDouble(POSITION_PRICE_OPEN);

   // Only start trailing once position is at least 1× trail distance in profit
   double profitDist = isBuy ? (cur - openP) : (openP - cur);
   if (profitDist < dist) return;

   // Update high water mark
   if (isBuy)  { if (cur > g_tk_hwm[idx]) g_tk_hwm[idx] = cur; }
   else        { if (cur < g_tk_hwm[idx]) g_tk_hwm[idx] = cur; }

   double newSL = isBuy ? (g_tk_hwm[idx] - dist) : (g_tk_hwm[idx] + dist);

   // Only move SL in the favorable direction, and only if improvement is ≥ 1 pip
   bool shouldMove = isBuy
      ? (newSL > curSL + pip)
      : (curSL == 0 || newSL < curSL - pip);

   if (!shouldMove) return;

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   ZeroMemory(req); ZeroMemory(res);
   req.action   = TRADE_ACTION_SLTP;
   req.symbol   = sym;
   req.position = ticket;
   req.sl       = newSL;
   req.tp       = PositionGetDouble(POSITION_TP);   // preserve existing TP

   if (OrderSend(req, res) && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)) {
      g_tk_sl[idx] = newSL;
      Print("DotVerse EA: trailing SL moved ticket=", ticket, " ", sym,
            " HWM=", DoubleToString(g_tk_hwm[idx], 5),
            " newSL=", DoubleToString(newSL, 5));
   }
}

//+------------------------------------------------------------------+
//| Check tracked positions against TP/SL levels                     |
//+------------------------------------------------------------------+
void CheckLevels()
{
   // Pick up any positions that were opened manually (outside DotVerse)
   ScanExistingPositions();

   for (int i = 0; i < g_tk_count; i++) {
      ulong ticket = g_tk[i];
      string sym   = g_tk_sym[i];
      string dir   = g_tk_dir[i];
      bool isBuy   = (dir == "BUY");

      // Check if position still open
      if (!PositionSelectByTicket(ticket)) {
         // Position closed — remove from tracking
         g_tk_count--;
         g_tk[i]     = g_tk[g_tk_count];
         g_tk_sym[i] = g_tk_sym[g_tk_count];
         g_tk_dir[i] = g_tk_dir[g_tk_count];
         g_tk_sl[i]  = g_tk_sl[g_tk_count];
         g_tk_tp1[i] = g_tk_tp1[g_tk_count];
         g_tk_tp2[i] = g_tk_tp2[g_tk_count];
         g_tk_tp3[i] = g_tk_tp3[g_tk_count];
         g_tk_hwm[i] = g_tk_hwm[g_tk_count];
         g_tk_hit[i] = g_tk_hit[g_tk_count];
         i--;
         continue;
      }

      // Apply trailing stop before checking hit levels
      ApplyTrailing(i);

      double cur = isBuy ? SymbolInfoDouble(sym, SYMBOL_BID) : SymbolInfoDouble(sym, SYMBOL_ASK);
      int    hit = g_tk_hit[i];

      // SL check
      if (g_tk_sl[i] > 0 && !(hit & 1)) {
         bool slHit = isBuy ? (cur <= g_tk_sl[i]) : (cur >= g_tk_sl[i]);
         if (slHit) { SendLevelAlert(ticket, sym, dir, "SL", cur); g_tk_hit[i] |= 1; }
      }
      // TP1 check
      if (g_tk_tp1[i] > 0 && !(hit & 2)) {
         bool tp1Hit = isBuy ? (cur >= g_tk_tp1[i]) : (cur <= g_tk_tp1[i]);
         if (tp1Hit) { SendLevelAlert(ticket, sym, dir, "TP1", cur); g_tk_hit[i] |= 2; }
      }
      // TP2 check
      if (g_tk_tp2[i] > 0 && !(hit & 4)) {
         bool tp2Hit = isBuy ? (cur >= g_tk_tp2[i]) : (cur <= g_tk_tp2[i]);
         if (tp2Hit) { SendLevelAlert(ticket, sym, dir, "TP2", cur); g_tk_hit[i] |= 4; }
      }
      // TP3 check
      if (g_tk_tp3[i] > 0 && !(hit & 8)) {
         bool tp3Hit = isBuy ? (cur >= g_tk_tp3[i]) : (cur <= g_tk_tp3[i]);
         if (tp3Hit) { SendLevelAlert(ticket, sym, dir, "TP3", cur); g_tk_hit[i] |= 8; }
      }
   }
}

void SendLevelAlert(ulong ticket, string symbol, string direction, string level, double price)
{
   Print("DotVerse EA: LEVEL HIT — ", level, " ticket=", ticket, " price=", price);
   string body = StringFormat(
      "{\"ticket\":%I64u,\"symbol\":\"%s\",\"direction\":\"%s\",\"level\":\"%s\",\"price\":%.5f}",
      ticket, symbol, direction, level, price
   );
   HttpPost("/api/mt5/alert", body);
}

//+------------------------------------------------------------------+
//| Build common HTTP headers                                         |
//+------------------------------------------------------------------+
string BuildHeaders()
{
   return "Content-Type: application/json\r\n"
        + "X-EA-Secret: " + InpEaSecret + "\r\n";
}

//+------------------------------------------------------------------+
//| POST helper — returns response body string, "" on error          |
//+------------------------------------------------------------------+
string HttpPost(string path, string body)
{
   string url     = InpBaseUrl + path;
   string headers = BuildHeaders();
   char   reqData[], resData[];
   string resHeaders;
   StringToCharArray(body, reqData, 0, StringLen(body));

   Print("DotVerse EA: POST ", url, " body=", StringSubstr(body,0,80));
   int result = WebRequest("POST", url, headers, 5000, reqData, resData, resHeaders);
   int err    = GetLastError();
   Print("DotVerse EA: POST result=", result, " err=", err, " resp=", CharArrayToString(resData));
   if (result == -1) {
      Print("DotVerse EA: POST FAILED. Add ", InpBaseUrl, " to Tools→Options→Expert Advisors→WebRequest list.");
      return "";
   }
   return CharArrayToString(resData);
}

//+------------------------------------------------------------------+
//| GET helper                                                        |
//+------------------------------------------------------------------+
string HttpGet(string path)
{
   string url     = InpBaseUrl + path;
   string headers = BuildHeaders();
   char   resData[];
   string resHeaders;
   char   empty[];

   int result = WebRequest("GET", url, headers, 5000, empty, resData, resHeaders);
   if (result == -1) {
      Print("DotVerse EA: GET ", path, " failed. err=", GetLastError());
      return "";
   }
   return CharArrayToString(resData);
}

//+------------------------------------------------------------------+
//| Push account state and open positions to DotVerse                 |
//+------------------------------------------------------------------+
void PushState()
{
   // --- Account snapshot ---
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity     = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin     = AccountInfoDouble(ACCOUNT_MARGIN);
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double profit     = AccountInfoDouble(ACCOUNT_PROFIT);
   string currency   = AccountInfoString(ACCOUNT_CURRENCY);

   // --- Open positions ---
   string posJson = "[";
   int total = PositionsTotal();
   for (int i = 0; i < total; i++) {
      ulong ticket = PositionGetTicket(i);
      if (ticket == 0) continue;
      string sym     = PositionGetString(POSITION_SYMBOL);
      string cmt     = PositionGetString(POSITION_COMMENT);
      double vol     = PositionGetDouble(POSITION_VOLUME);
      double oprice  = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl      = PositionGetDouble(POSITION_SL);
      double tp      = PositionGetDouble(POSITION_TP);
      double ppnl    = PositionGetDouble(POSITION_PROFIT);
      int    ptype   = (int)PositionGetInteger(POSITION_TYPE);
      string ptype_s = (ptype == POSITION_TYPE_BUY) ? "BUY" : "SELL";

      if (i > 0) posJson += ",";
      double curPrice = (ptype == POSITION_TYPE_BUY)
                      ? SymbolInfoDouble(sym, SYMBOL_BID)
                      : SymbolInfoDouble(sym, SYMBOL_ASK);
      posJson += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\","
         "\"volume\":%.2f,\"open_price\":%.5f,\"current_price\":%.5f,"
         "\"sl\":%.5f,\"tp\":%.5f,\"profit\":%.2f,\"comment\":\"%s\"}",
         ticket, sym, ptype_s, vol, oprice, curPrice, sl, tp, ppnl, cmt
      );
   }
   posJson += "]";

   string body = StringFormat(
      "{\"user_id\":\"%s\","
      "\"account\":{\"balance\":%.2f,\"equity\":%.2f,\"margin\":%.2f,"
                   "\"free_margin\":%.2f,\"profit\":%.2f,\"currency\":\"%s\"},"
      "\"positions\":%s}",
      g_userId, balance, equity, margin, freeMargin, profit, currency, posJson
   );

   HttpPost("/api/mt5/push", body);
}

//+------------------------------------------------------------------+
//| Poll pending orders and execute them                              |
//+------------------------------------------------------------------+
void PollAndExecute()
{
   string resp = HttpGet("/api/mt5/pending");
   if (StringLen(resp) == 0) return;

   // Parse automation settings embedded in response
   int setStart = StringFind(resp, "\"settings\":{");
   if (setStart >= 0) {
      int setEnd = StringFind(resp, "}", setStart);
      if (setEnd > setStart) {
         string setBlock = StringSubstr(resp, setStart, setEnd - setStart + 1);
         string trailStr = JsonStr(setBlock, "trailing_on");
         g_trail_on   = (trailStr == "true");
         double tp    = JsonDbl(setBlock, "trailing_pips");
         if (tp > 0) g_trail_pips = tp;
      }
   }

   // Simple JSON parsing — extract each order block
   // DotVerse returns: {"orders":[...],"settings":{...}}
   // We parse the array manually to stay dependency-free.

   // Find "orders":[ ... ]
   int arrStart = StringFind(resp, "\"orders\":[");
   if (arrStart < 0) return;
   arrStart = StringFind(resp, "[", arrStart);
   if (arrStart < 0) return;

   int pos = arrStart + 1;
   int len = StringLen(resp);

   while (pos < len) {
      // Skip whitespace
      while (pos < len && (StringGetCharacter(resp, pos) == ' ' || StringGetCharacter(resp, pos) == '\n'
             || StringGetCharacter(resp, pos) == '\r' || StringGetCharacter(resp, pos) == '\t'))
         pos++;
      if (pos >= len) break;
      ushort ch = StringGetCharacter(resp, pos);
      if (ch == ']') break;  // end of array
      if (ch != '{') { pos++; continue; }

      // Find matching closing brace
      int depth = 0, objEnd = pos;
      for (int k = pos; k < len; k++) {
         ushort c = StringGetCharacter(resp, k);
         if (c == '{') depth++;
         else if (c == '}') { depth--; if (depth == 0) { objEnd = k; break; } }
      }
      string obj = StringSubstr(resp, pos, objEnd - pos + 1);
      ExecuteOrder(obj);
      pos = objEnd + 1;
      // Skip comma
      while (pos < len && StringGetCharacter(resp, pos) == ',') pos++;
   }
}

//+------------------------------------------------------------------+
//| Extract a string value from a JSON object (naive, no nesting)    |
//+------------------------------------------------------------------+
string JsonStr(string json, string key)
{
   string search = "\"" + key + "\":";
   int i = StringFind(json, search);
   if (i < 0) return "";
   i += StringLen(search);
   // Skip whitespace
   while (i < StringLen(json) && StringGetCharacter(json, i) == ' ') i++;
   ushort fch = StringGetCharacter(json, i);
   if (fch == '"') {
      // String value
      i++;
      int j = i;
      while (j < StringLen(json) && StringGetCharacter(json, j) != '"') j++;
      return StringSubstr(json, i, j - i);
   } else {
      // Numeric / boolean / null — read until comma, }, or ]
      int j = i;
      while (j < StringLen(json)) {
         ushort c = StringGetCharacter(json, j);
         if (c == ',' || c == '}' || c == ']') break;
         j++;
      }
      return StringSubstr(json, i, j - i);
   }
}

double JsonDbl(string json, string key) { return StringToDouble(JsonStr(json, key)); }
long   JsonInt(string json, string key) { return StringToInteger(JsonStr(json, key)); }

//+------------------------------------------------------------------+
//| Execute a single order JSON object                                |
//+------------------------------------------------------------------+
void ExecuteOrder(string obj)
{
   long   orderId   = JsonInt(obj, "id");
   string symbol    = JsonStr(obj, "symbol");
   string orderType = JsonStr(obj, "order_type");  // BUY | SELL | CLOSE
   string action    = JsonStr(obj, "action");       // open | close
   long   closeTk   = JsonInt(obj, "close_ticket"); // MT5 ticket to close (when action=close)
   double volume    = JsonDbl(obj, "volume");
   double sl        = JsonDbl(obj, "sl");
   double tp        = JsonDbl(obj, "tp");
   double tp2       = JsonDbl(obj, "tp2");
   double tp3       = JsonDbl(obj, "tp3");

   // ── MODIFY_SL order: breakeven or trailing stop automation ────
   if (action == "modify_sl" && closeTk > 0 && sl > 0) {
      Print("DotVerse EA: modifying SL ticket=", closeTk, " new_sl=", sl);
      bool modified = false;
      if (PositionSelectByTicket((ulong)closeTk)) {
         MqlTradeRequest req = {};
         MqlTradeResult  res = {};
         ZeroMemory(req); ZeroMemory(res);
         req.action   = TRADE_ACTION_SLTP;
         req.symbol   = PositionGetString(POSITION_SYMBOL);
         req.position = (ulong)closeTk;
         req.sl       = sl;
         req.tp       = PositionGetDouble(POSITION_TP); // preserve existing TP
         modified = OrderSend(req, res);
         if (modified && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED))
            Print("DotVerse EA: SL modified OK ticket=", closeTk, " new_sl=", sl);
         else
            Print("DotVerse EA: SL modify FAILED ticket=", closeTk, " retcode=", res.retcode);
      } else {
         Print("DotVerse EA: position ", closeTk, " not found for SL modify");
         modified = true;
      }
      string mstatus = modified ? "filled" : "failed";
      string mbody = StringFormat(
         "{\"order_id\":%I64d,\"status\":\"%s\",\"ticket\":%I64d,\"fill_price\":%.5f,\"comment\":\"modify_sl\"}",
         orderId, mstatus, closeTk, sl
      );
      HttpPost("/api/mt5/confirm", mbody);
      return;
   }

   // ── CLOSE order: user tapped a Trade Manager button ───────────
   if (action == "close" && closeTk > 0) {
      Print("DotVerse EA: closing position ticket=", closeTk);
      bool closed = false;
      // Check the position still exists
      if (PositionSelectByTicket((ulong)closeTk)) {
         string  posSym  = PositionGetString(POSITION_SYMBOL);
         double  posVol  = PositionGetDouble(POSITION_VOLUME);
         long    posType = PositionGetInteger(POSITION_TYPE); // 0=BUY, 1=SELL
         ENUM_ORDER_TYPE closeType = (posType == 0) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
         ENUM_ORDER_TYPE_FILLING filling = ORDER_FILLING_RETURN;
         int fillFlags = (int)SymbolInfoInteger(posSym, SYMBOL_FILLING_MODE);
         if (fillFlags & SYMBOL_FILLING_IOC) filling = ORDER_FILLING_IOC;

         MqlTradeRequest req = {};
         MqlTradeResult  res = {};
         ZeroMemory(req); ZeroMemory(res);
         req.action      = TRADE_ACTION_DEAL;
         req.symbol      = posSym;
         req.volume      = posVol;
         req.type        = closeType;
         req.type_filling= filling;
         req.deviation   = (ulong)InpSlippage;
         req.position    = (ulong)closeTk;
         req.comment     = "DotVerse close #" + IntegerToString(orderId);
         if (closeType == ORDER_TYPE_BUY)
            req.price = SymbolInfoDouble(posSym, SYMBOL_ASK);
         else
            req.price = SymbolInfoDouble(posSym, SYMBOL_BID);
         closed = OrderSend(req, res);
         if (closed && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED))
            Print("DotVerse EA: close OK ticket=", closeTk, " retcode=", res.retcode);
         else
            Print("DotVerse EA: close FAILED ticket=", closeTk, " retcode=", res.retcode, " ", res.comment);
      } else {
         Print("DotVerse EA: position ", closeTk, " not found (already closed?)");
         closed = true; // treat as success so the order doesn't repeat
      }
      // Report back
      string status = closed ? "filled" : "failed";
      string body   = StringFormat(
         "{\"order_id\":%I64d,\"status\":\"%s\",\"ticket\":%I64d,\"fill_price\":0,\"comment\":\"close\"}",
         orderId, status, closeTk
      );
      HttpPost("/api/mt5/confirm", body);
      return;
   }

   // Store tp2/tp3 for this order_id so we can look them up after fill
   if (g_pending_count < MAX_PENDING) {
      g_pending_id[g_pending_count]  = orderId;
      g_pending_tp2[g_pending_count] = tp2;
      g_pending_tp3[g_pending_count] = tp3;
      g_pending_count++;
   }

   if (orderId == 0 || StringLen(symbol) == 0) {
      Print("DotVerse EA: skipping malformed order: ", obj);
      return;
   }

   Print("DotVerse EA: executing order #", orderId, " ", orderType, " ", volume, " ", symbol);

   ENUM_ORDER_TYPE otype = (orderType == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   MqlTradeRequest  req = {};
   MqlTradeResult   res = {};
   ZeroMemory(req);
   ZeroMemory(res);

   // Auto-detect supported filling mode for this symbol
   ENUM_ORDER_TYPE_FILLING filling = ORDER_FILLING_FOK;
   int fillFlags = (int)SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if      (fillFlags & SYMBOL_FILLING_IOC)    filling = ORDER_FILLING_IOC;
   else if (fillFlags & SYMBOL_FILLING_BOC)    filling = ORDER_FILLING_BOC;
   else                                         filling = ORDER_FILLING_RETURN;

   req.action      = TRADE_ACTION_DEAL;
   req.symbol      = symbol;
   req.volume      = volume;
   req.type        = otype;
   req.type_filling= filling;
   req.deviation   = (ulong)InpSlippage;
   req.comment     = "DotVerse #" + IntegerToString(orderId);
   Print("DotVerse EA: filling mode=", EnumToString(filling), " fillFlags=", fillFlags);

   // Price — market order uses Ask for BUY, Bid for SELL
   if (otype == ORDER_TYPE_BUY)
      req.price = SymbolInfoDouble(symbol, SYMBOL_ASK);
   else
      req.price = SymbolInfoDouble(symbol, SYMBOL_BID);

   if (sl > 0) req.sl = sl;
   if (tp > 0) req.tp = tp;

   bool sent = OrderSend(req, res);

   string status, comment;
   long   ticket    = 0;
   double fillPrice = 0;

   if (sent && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED)) {
      status    = "filled";
      ticket    = (long)res.deal;
      fillPrice = res.price;
      comment   = "Filled at " + DoubleToString(fillPrice, 5);
      Print("DotVerse EA: order #", orderId, " filled. deal=", ticket, " price=", fillPrice);

      // Look up tp2/tp3 for this order_id and register for level monitoring
      double o_tp2 = 0, o_tp3 = 0;
      for (int pi = 0; pi < g_pending_count; pi++) {
         if (g_pending_id[pi] == orderId) { o_tp2 = g_pending_tp2[pi]; o_tp3 = g_pending_tp3[pi]; break; }
      }
      if (g_tk_count < MAX_TRACKED) {
         int idx = g_tk_count++;
         g_tk[idx]     = (ulong)ticket;
         g_tk_sym[idx] = symbol;
         g_tk_dir[idx] = orderType;
         g_tk_sl[idx]  = sl;
         g_tk_tp1[idx] = tp;
         g_tk_tp2[idx] = o_tp2;
         g_tk_tp3[idx] = o_tp3;
         g_tk_hwm[idx] = fillPrice;  // HWM starts at fill price
         g_tk_hit[idx] = 0;
         Print("DotVerse EA: tracking ticket ", ticket, " SL=", sl, " TP1=", tp, " TP2=", o_tp2, " TP3=", o_tp3);
      }
   } else {
      status  = "failed";
      comment = "retcode=" + IntegerToString(res.retcode) + " " + res.comment;
      Print("DotVerse EA: order #", orderId, " FAILED. ", comment);
   }

   // Report result back to DotVerse
   string body = StringFormat(
      "{\"order_id\":%I64d,\"status\":\"%s\",\"ticket\":%I64d,\"fill_price\":%.5f,\"comment\":\"%s\"}",
      orderId, status, ticket, fillPrice, comment
   );
   HttpPost("/api/mt5/confirm", body);
}
//+------------------------------------------------------------------+
