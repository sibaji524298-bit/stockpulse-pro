# TinyCapitalCapital StockPulse Pro — Scripts, Deploy & Rollback Guide

Live URL: https://tinycapitalclub.onrender.com
Repository: https://github.com/sibaji524298-bit/stockpulse-pro.git

## 1. Core Scripts

### A. DataFrame Sanitization Script (fix_tcs_recursion.py)
cd ~/Stocks
cat << 'PYEOF' > fix_tcs_recursion.py
p = "app.py"
code = open(p).read()

safe_helper = """
def _clean_ohlcv(df):
    if df is None or getattr(df, "empty", True):
        return df
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]) for c in df.columns]
    else:
        df.columns = [str(c) for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.reset_index(drop=True)
    out = pd.DataFrame(index=df.index)
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            raw = df[col]
            if isinstance(raw, pd.DataFrame):
                raw = raw.iloc[:, 0]
            arr = np.asarray(raw.to_numpy(), dtype=float).reshape(-1)
            out[col] = pd.Series(arr, index=out.index, dtype="float64")
    if "Close" not in out.columns:
        return df
    return out.dropna(subset=["Close"]).reset_index(drop=True)
"""

if "def _clean_ohlcv" in code:
    start = code.index("def _clean_ohlcv")
    end = code.index("\n\n", start)
    code = code[:start] + safe_helper.strip() + code[end:]
else:
    code = code.replace("app = Flask(__name__)", "app = Flask(__name__)\n" + safe_helper.strip(), 1)

code = code.replace(
    "df = _clean_ohlcv(fetch_history_cached(ticker, period))",
    "df = _clean_ohlcv(fetch_history_cached(ticker, period))"
)
code = code.replace(
    "df = fetch_history_cached(ticker, period)",
    "df = _clean_ohlcv(fetch_history_cached(ticker, period))"
)
code = code.replace(
    'df = yf.download(ticker, period=period, interval="1d", progress=False)',
    'df = _clean_ohlcv(yf.download(ticker, period=period, interval="1d", progress=False))'
)

open(p, "w").write(code)
print("Updated _clean_ohlcv with 1D float64 normalization.")
PYEOF
python fix_tcs_recursion.py
python -m py_compile app.py

### B. Cache Recursion Fix Script (patch_cache.py)
cd ~/Stocks
cat << 'PYEOF' > patch_cache.py
p = "app.py"
with open(p, "r", encoding="utf-8") as f:
    code = f.read()

old_block = """def fetch_history_cached(ticker, period):
    key = (ticker, period)
    now = time.time()
    if key in _CACHE:
        ts, df_cached = _CACHE[key]
        if now - ts < CACHE_TTL:
            return df_cached.copy()
    df = fetch_history_cached(ticker, period)"""

new_block = """def fetch_history_cached(ticker, period):
    key = (ticker, period)
    now = time.time()
    if key in _CACHE:
        ts, df_cached = _CACHE[key]
        if now - ts < CACHE_TTL:
            return df_cached.copy()
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False)"""

if old_block not in code:
    raise SystemExit("Could not find the recursive fetch_history_cached block in app.py.")

with open(p, "w", encoding="utf-8") as f:
    f.write(code.replace(old_block, new_block, 1))

print("Patched fetch_history_cached successfully.")
PYEOF
python patch_cache.py
python -m py_compile app.py

## 2. End-to-End Update & Deploy Script
cd ~/Stocks
python -m py_compile app.py
sed -n '57,68p' app.py
git status
git add app.py
git commit -m "Update StockPulse Pro app.py"
git push https://sibaji524298-bit:YOUR_NEW_TOKEN@github.com/sibaji524298-bit/stockpulse-pro.git main
git remote set-url origin https://github.com/sibaji524298-bit/stockpulse-pro.git

Render settings:
- Build Command: pip install -r requirements.txt
- Start Command: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
- Auto-Deploy: On Commit

## 3. Rollback Plan

### Safe Revert Commit
cd ~/Stocks
git log -n 5 --oneline
git revert --no-edit HEAD
git push origin main

### Roll Back app.py to a Specific Commit (e.g. 03b229e)
cd ~/Stocks
git log -n 5 --oneline
git checkout 03b229e -- app.py
python -m py_compile app.py
git add app.py
git commit -m "Roll back app.py to commit 03b229e"
git push origin main

### Render Dashboard Rollback
Open the service on render.com -> Deploys -> select a prior Live deploy -> redeploy/roll back.
