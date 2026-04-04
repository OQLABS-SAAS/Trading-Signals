# Trading Signals SaaS — Deployment Guide

AI-powered trading signal analysis for stocks, crypto, and forex. Powered by Claude AI + real market data from Yahoo Finance.

---

## What It Does

- Enter any ticker (AAPL, BTC, EURUSD) and get an instant AI analysis
- Calculates RSI, EMA 20/50/200, MACD, Bollinger Bands, ATR, Supertrend, Volume
- Claude AI generates a BUY / HOLD / SELL signal with confidence level
- Shows entry price, stop loss, take profit, and risk/reward ratio
- Bull, Base, and Bear scenarios explained in plain English

---

## Option A — Run Locally (Test on Your Computer)

### Step 1 — Get your Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign in → click **API Keys** in the left sidebar
3. Click **Create Key** → copy it and keep it safe

### Step 2 — Install Python

Download Python 3.11+ from [python.org](https://python.org) if you don't have it.

### Step 3 — Install dependencies

Open Terminal (Mac) or Command Prompt (Windows), navigate to the `trading-signals-saas` folder, then run:

```
pip install -r requirements.txt
```

### Step 4 — Set your API key

**Mac/Linux:**
```
export ANTHROPIC_API_KEY=your_key_here
```

**Windows:**
```
set ANTHROPIC_API_KEY=your_key_here
```

### Step 5 — Start the server

```
python app.py
```

You should see: `Running on http://0.0.0.0:5000`

### Step 6 — Open in browser

Go to [http://localhost:5000](http://localhost:5000) — the app is live.

---

## Option B — Deploy to Railway (Free, Live URL in 5 Minutes)

Railway is the easiest way to get a public URL for your app. Free tier is enough to start.

### Step 1 — Create a Railway account

Go to [railway.app](https://railway.app) and sign up with GitHub.

### Step 2 — Create a new project

1. Click **New Project**
2. Select **Deploy from GitHub repo** (you'll need to push your code to GitHub first — see below)
   — OR —
   Select **Empty project** → then **Add a Service** → **GitHub Repo**

### Step 2b — Push code to GitHub (if not already done)

1. Go to [github.com](https://github.com) → **New repository** → name it `trading-signals`
2. On your computer, open Terminal in the `trading-signals-saas` folder and run:
```
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/trading-signals.git
git push -u origin main
```

### Step 3 — Connect repo to Railway

1. In Railway, click **New Project** → **Deploy from GitHub repo**
2. Select your `trading-signals` repository
3. Railway will detect it's a Python app automatically

### Step 4 — Add your API key

1. In Railway, click your service → **Variables** tab
2. Click **New Variable**
3. Name: `ANTHROPIC_API_KEY`
4. Value: your Anthropic API key
5. Click **Add**

### Step 5 — Deploy

Railway deploys automatically. In 2-3 minutes you'll see a **green checkmark** and a URL like `https://trading-signals-production.up.railway.app`.

Click the URL — your app is live.

---

## Option C — Deploy to Render (Alternative Free Option)

1. Go to [render.com](https://render.com) and sign up
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
6. Add environment variable: `ANTHROPIC_API_KEY` = your key
7. Click **Create Web Service**

---

## Folder Structure

```
trading-signals-saas/
├── app.py              ← Flask backend (all API logic)
├── requirements.txt    ← Python dependencies
├── Procfile            ← Deployment config for Railway/Heroku
├── README.md           ← This file
└── static/
    └── index.html      ← Frontend (all UI in one file)
```

---

## Supported Tickers

| Type   | Examples                        | Format         |
|--------|---------------------------------|----------------|
| Stock  | AAPL, NVDA, TSLA, MSFT, AMZN   | Just the ticker |
| Crypto | BTC, ETH, SOL, XRP             | Ticker only (auto-appends -USD) |
| Forex  | EURUSD, GBPUSD, USDJPY         | Pair without slash (auto-appends =X) |

---

## API Reference

**POST** `/api/analyze`

Request body:
```json
{
  "ticker": "AAPL",
  "asset_type": "stock"
}
```

`asset_type` options: `"stock"`, `"crypto"`, `"forex"`

Response includes: price, RSI, EMAs, MACD, Bollinger Bands, ATR, Supertrend, volume, signal, confidence, summary, entry, stop_loss, take_profit, risk_reward, bull/base/bear scenarios.

**GET** `/health` — Returns `{"status": "ok"}` if the server is running.

---

## Cost Estimate

- **Anthropic API**: ~$0.003–0.005 per analysis (claude-sonnet-4-6 pricing)
- **100 analyses/day** ≈ $0.30–0.50/day
- Railway free tier: 500 hours/month (enough for testing; ~$5/month for always-on)

---

## Troubleshooting

**"No data found for ticker"** — Check the ticker is correct. Crypto needs to be just the base (BTC not BTC-USD). Forex needs the pair without slash (EURUSD not EUR/USD).

**"Analysis generation failed"** — Your Anthropic API key is missing or invalid. Double-check it in your environment variables.

**App crashes on start** — Run `pip install -r requirements.txt` again to make sure all packages installed correctly.

**Slow first analysis** — yfinance downloads 1 year of daily data on first request. This takes 2-5 seconds. Subsequent requests for the same ticker are normal speed.

---

*Not financial advice. Use signals as one input among many in your own research.*
