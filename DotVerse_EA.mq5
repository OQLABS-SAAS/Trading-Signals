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
string g_userId       = "default";   // server matches push/pull by user_id; default is fine for demo

//+------------------------------------------------------------------+
//| Expert initialisation                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   if (StringLen(InpEaSecret) == 0) {
      Alert("DotVerse EA: InpEaSecret is empty. Set it in EA inputs.");
      return INIT_FAILED;
   }
   if (!EventSetTimer(InpPollSecs)) {
      Alert("DotVerse EA: Could not start timer.");
      return INIT_FAILED;
   }
   Print("DotVerse EA started. Polling every ", InpPollSecs, "s → ", InpBaseUrl);
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
      string sym    = PositionGetString(POSITION_SYMBOL);
      double vol    = PositionGetDouble(POSITION_VOLUME);
      double oprice = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl     = PositionGetDouble(POSITION_SL);
      double tp     = PositionGetDouble(POSITION_TP);
      double ppnl   = PositionGetDouble(POSITION_PROFIT);
      int    ptype  = (int)PositionGetInteger(POSITION_TYPE);
      string ptype_s = (ptype == POSITION_TYPE_BUY) ? "BUY" : "SELL";

      if (i > 0) posJson += ",";
      double curPrice = (ptype == POSITION_TYPE_BUY)
                      ? SymbolInfoDouble(sym, SYMBOL_BID)
                      : SymbolInfoDouble(sym, SYMBOL_ASK);
      posJson += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\","
         "\"volume\":%.2f,\"open_price\":%.5f,\"current_price\":%.5f,"
         "\"sl\":%.5f,\"tp\":%.5f,\"profit\":%.2f}",
         ticket, sym, ptype_s, vol, oprice, curPrice, sl, tp, ppnl
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

   // Simple JSON parsing — extract each order block
   // DotVerse returns: {"orders":[{"id":1,"symbol":"EURUSD","order_type":"BUY","volume":0.01,...},...]}
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
   string orderType = JsonStr(obj, "order_type");  // BUY | SELL
   double volume    = JsonDbl(obj, "volume");
   double sl        = JsonDbl(obj, "sl");
   double tp        = JsonDbl(obj, "tp");

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
