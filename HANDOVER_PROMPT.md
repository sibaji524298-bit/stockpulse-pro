Continue working on **TinyCapitalCapital StockPulse Pro** ("Small Capital. Big Dreams." / TinyCapitalClub), an interactive stock analysis web application for the Indian Stock Market (NSE/BSE such as NTPC.NS, TCS.NS, BANKBARODA.NS) developed in Termux on Android and deployed to Render.

### Project & Deployment Details
- **Application Name:** TinyCapitalCapital StockPulse Pro
- **Local Working Directory:** ~/Stocks (in Termux on Android)
- **Core Stack:** Python (Flask, yfinance, pandas, numpy, ta), gunicorn, HTML/Tailwind CSS, Chart.js with toggle overlays (including SuperTrend and Bollinger Bands), 100+ technical indicators with Buy/Sell/Hold counts and an aggregate score (e.g., Score: +0.60 (Buy: 68 | Sell: 14 | Hold: 22) Indicators Shown: 104), rule-based verdict (OVERALL: BUY / SELL / HOLD), 10-second auto-refresh UI with a pause toggle, 15-second in-memory cache (_CACHE, CACHE_TTL = 15), and PWA support (manifest.json, SVG icons).
- **GitHub Repository:** https://github.com/sibaji524298-bit/stockpulse-pro.git (branch: main)
- **Live Render URL:** https://tinycapitalclub.onrender.com
- **Render Web Service Settings:**
  - Language/Runtime: Python 3
  - Branch: main
  - Build Command: pip install -r requirements.txt
  - Start Command: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
  - Auto-Deploy: On Commit

### Key Milestones & Fixes Already Completed
1. Resolved Termux package setup and verified imports (yfinance, pandas, ta, flask), patched AroonIndicator syntax, and added requirements.txt, Procfile, and .gitignore.
2. Initialized Git on main, pushed initial commit (c72a167) to sibaji524298-bit/stockpulse-pro.git using HTTPS + Personal Access Token (and reset origin URL to https://github.com/sibaji524298-bit/stockpulse-pro.git afterward). Note: An earlier token (<REDACTED_GITHUB_PAT>) was shared in chat earlier and the user prefers not to touch token/auth settings unless needed while the live site is working.
3. Created the Render web service (stockpulse-pro-80bo.onrender.com). Initially encountered a password prompt screenshot from a separate/earlier StockPulse PRO login screen, then hit Error analyzing 'NTPC.NS': maximum recursion depth exceeded and Error analyzing 'TCS.NS': maximum recursion depth exceeded.
4. Inspected ~/Stocks/app.py and found the root cause inside fetch_history_cached(ticker, period): on a cache miss, df = fetch_history_cached(ticker, period) called itself recursively instead of calling yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False).
5. Patched fetch_history_cached via patch_cache.py, verified python -m py_compile app.py, committed as 03b229e ("Fix infinite recursion in fetch_history_cached"), pushed to origin main, redeployed on Render, and confirmed live analysis works.
6. Prepared fix_tcs_recursion.py (_clean_ohlcv to flatten MultiIndex columns and normalize 1D float64 Open/High/Low/Close/Volume series if needed), documented the end-to-end deploy and rollback plan (git revert, git checkout <commit> -- app.py, and Render dashboard rollback), and saved a runbook to ~/Stocks/RUNBOOK.md.

### How to Assist Me
- Treat ~/Stocks/app.py on main (commit 03b229e and later updates) and https://tinycapitalclub.onrender.com as the active baseline.
- Provide clear, copy-pasteable Termux commands with brief verification checks, without altering working auth/token setups unnecessarily.
- Help me with any next enhancements, indicator/chart tweaks, bug fixes, Git/Render deployments, or rollbacks I ask for.

## Update (Nov 20, 2026)
- Aligned logo in header, set 20s refresh, expanded lookback periods to 30m..max.
- Pushed to origin/main for Render deploy.

---
## Deployment Update (Nov 20, 2026)
- App Title: Tiny Capital Club StockPulse Pro.
- Header Logo: 88px circular logo aligned inline with the title using static/logo.png.
- Controls & Refresh: Lookback periods from 30m through max; 20s auto-refresh active.
- Hosting: GitHub main branch (sibaji524298-bit/stockpulse-pro.git) deployed on Render (https://tinycapitalclub.onrender.com).
- Backups: Updated app.py.bak and created a timestamped backup in ~/Stocks.

---
## Indicator Engine & Option A UI Update (Nov 20, 2026)
- Added `indicators_rules.json` (104 indicators from Sheet1 + 6 weighted families & score scale from Sheet2) and `indicator_engine.py` with anti-redundancy and repainting guardrails.
- Wired Option A composite verdict (`-2.00` to `+2.00`), 6 family score pills, and searchable 104-indicator reference table into `app.py` while keeping header, `88px` logo, title, `20s` refresh, `30m`–`max` lookback, colors, and chart intact.
- Ensured `openpyxl` is listed in `requirements.txt`.

---
## Lookback & Data-Fetch Alignment Update (Nov 20, 2026)
- Aligned lookback resolution (`30m` through `max`), interval mapping, and a short-lived `(symbol, period, interval)` fetch cache in `app.py` so the Majority Rule Composite Verdict panel and chart analyze consistent bars.
- Added active `period / interval · N bars` context to the Majority Rule verdict header.
- Refreshed local backup (`app.py.bak`) and device shared storage backup (`~/storage/shared/StockPulse_Backup`).
