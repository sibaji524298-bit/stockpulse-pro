import time
import json
import numpy as np
import pandas as pd
from flask import Flask, render_template_string, request
import yfinance as yf
from ta.momentum import (
    AwesomeOscillatorIndicator,
    KAMAIndicator,
    PercentagePriceOscillator,
    ROCIndicator,
    RSIIndicator,
    StochRSIIndicator,
    StochasticOscillator,
    TSIIndicator,
    UltimateOscillator,
    WilliamsRIndicator,
)
from ta.trend import (
    ADXIndicator,
    AroonIndicator,
    CCIIndicator,
    DPOIndicator,
    EMAIndicator,
    IchimokuIndicator,
    KSTIndicator,
    MACD,
    MassIndex,
    PSARIndicator,
    SMAIndicator,
    TRIXIndicator,
    VortexIndicator,
    WMAIndicator,
)
from ta.volatility import (
    AverageTrueRange,
    BollingerBands,
    DonchianChannel,
    KeltnerChannel,
)
from ta.volume import (
    AccDistIndexIndicator,
    ChaikinMoneyFlowIndicator,
    EaseOfMovementIndicator,
    ForceIndexIndicator,
    MFIIndicator,
    OnBalanceVolumeIndicator,
    VolumePriceTrendIndicator,
    VolumeWeightedAveragePrice,
)

app = Flask(__name__)

_CACHE = {}
CACHE_TTL = 15  # seconds

def fetch_history_cached(ticker, period):
    key = (ticker, period)
    now = time.time()
    if key in _CACHE:
        ts, df_cached = _CACHE[key]
        if now - ts < CACHE_TTL:
            return df_cached.copy()
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False)
    if not df.empty:
        _CACHE[key] = (now, df.copy())
    return df


HTML = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0f172a">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <link rel="icon" type="image/svg+xml" href="/icon.svg">
  <link rel="manifest" href="/manifest.json">
  <title>TinyCapitalCapital StockPulse Pro</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; margin: 14px; background: #0f172a; color: #f1f5f9; }
    h2, h3 { margin: 8px 0; }
    .top-bar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px; }
    .refresh-box { display: flex; align-items: center; gap: 8px; background: #1e293b; padding: 6px 10px; border-radius: 6px; border: 1px solid #334155; font-size: 13px; color: #cbd5e1; }
    .form-row { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
    input, select, button { padding: 10px 12px; font-size: 15px; border-radius: 6px; border: 1px solid #334155; }
    input, select { background: #1e293b; color: #f8fafc; }
    input { flex: 1; min-width: 170px; max-width: 260px; }
    button { background: #2563eb; color: #fff; border: none; font-weight: 600; cursor: pointer; }
    button:hover { background: #1d4ed8; }
    .btn-secondary { background: #334155; color: #f8fafc; font-size: 13px; padding: 6px 10px; }
    .btn-secondary:hover { background: #475569; }
    .summary-card { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; background: #1e293b; padding: 12px 14px; border-radius: 8px; border: 1px solid #334155; margin: 12px 0; }
    .badge { padding: 6px 12px; border-radius: 999px; font-weight: 700; font-size: 14px; }
    .buy { background: rgba(34, 197, 94, 0.18); color: #4ade80; border: 1px solid #22c55e; }
    .sell { background: rgba(239, 68, 68, 0.18); color: #f87171; border: 1px solid #ef4444; }
    .hold { background: rgba(234, 179, 8, 0.18); color: #facc15; border: 1px solid #eab308; }
    .chart-box { background: #1e293b; padding: 12px; border-radius: 8px; border: 1px solid #334155; margin: 14px 0; }
    .toggles { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 10px; font-size: 13px; }
    .toggles label { display: inline-flex; align-items: center; gap: 5px; cursor: pointer; }
    .table-wrap { overflow-x: auto; margin-top: 12px; }
    table { width: 100%; border-collapse: collapse; background: #1e293b; font-size: 13px; }
    th, td { border: 1px solid #334155; padding: 7px 9px; text-align: left; }
    th { background: #0f172a; color: #94a3b8; position: sticky; top: 0; }
    .sig-BUY { color: #4ade80; font-weight: 700; }
    .sig-SELL { color: #f87171; font-weight: 700; }
    .sig-HOLD { color: #facc15; font-weight: 700; }
    .err { color: #f87171; background: rgba(239,68,68,0.12); padding: 10px; border-radius: 6px; }
    .note { color: #94a3b8; font-size: 12px; margin-top: 14px; }
    canvas { max-height: 310px; width: 100%; }
  </style>
</head>
<body>
  <div class="top-bar">
    <h2>TinyCapitalCapital StockPulse Pro</h2>
    <div class="refresh-box">
      <span id="refreshStatus">Auto-refresh in 10s</span>
      <button type="button" id="toggleRefreshBtn" class="btn-secondary">Pause</button>
    </div>
  </div>

  <form method="POST" class="form-row" id="analyzeForm">
    <input type="text" id="tickerInput" name="ticker" value="{{ ticker }}" placeholder="e.g. NTPC.NS, RELIANCE.NS" required>
    <select name="period">
      {% for p in ["3mo", "6mo", "1y", "2y"] %}
        <option value="{{ p }}" {% if period == p %}selected{% endif %}>{{ p }}</option>
      {% endfor %}
    </select>
    <button type="submit">Run Analysis</button>
  </form>

  {% if error %}<p class="err">{{ error }}</p>{% endif %}

  {% if verdict %}
    <div class="summary-card">
      <div><strong>{{ ticker }}</strong> — Latest Close: <strong>{{ price }}</strong> ({{ period }})</div>
      <span class="badge {{ verdict_class }}">OVERALL: {{ verdict }}</span>
      <div>Score: <strong>{{ score }}</strong> (Buy: {{ buy_count }} | Sell: {{ sell_count }} | Hold: {{ hold_count }})</div>
      <div>Indicators Shown: <strong>{{ total_rows }}</strong></div>
    </div>

    <div class="chart-box">
      <div class="toggles">
        <label><input type="checkbox" id="togSMA" checked> SMA 20</label>
        <label><input type="checkbox" id="togEMA" checked> EMA 20</label>
        <label><input type="checkbox" id="togST" checked> SuperTrend</label>
        <label><input type="checkbox" id="togBB" checked> Bollinger Bands</label>
        <label><input type="checkbox" id="togRSI"> RSI (14) [Right Axis]</label>
      </div>
      <canvas id="priceChart"></canvas>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Indicator</th>
            <th>Category</th>
            <th>Value</th>
            <th>Signal</th>
            <th>Rule Basis</th>
          </tr>
        </thead>
        <tbody>
          {% for name, cat, val, sig, basis in rows %}
            <tr>
              <td>{{ name }}</td>
              <td>{{ cat }}</td>
              <td>{{ val }}</td>
              <td class="sig-{{ sig }}">{{ sig }}</td>
              <td>{{ basis }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>

    <p class="note">Disclaimer: Automated technical indicator signals are for informational and educational use only, not financial or investment advice.</p>

    <script>
      const chartData = {{ chart_json | safe }};
      const ctx = document.getElementById('priceChart').getContext('2d');

      const datasets = [
        {
          label: 'Close',
          data: chartData.close,
          borderColor: '#38bdf8',
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          id: 'sma20',
          label: 'SMA 20',
          data: chartData.sma20,
          borderColor: '#facc15',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          id: 'ema20',
          label: 'EMA 20',
          data: chartData.ema20,
          borderColor: '#c084fc',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          id: 'supertrend',
          label: 'SuperTrend',
          data: chartData.supertrend,
          borderColor: '#34d399',
          backgroundColor: 'transparent',
          borderWidth: 1.6,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          id: 'bbHigh',
          label: 'BB Upper',
          data: chartData.bb_high,
          borderColor: 'rgba(148, 163, 184, 0.55)',
          borderDash: [4, 4],
          backgroundColor: 'transparent',
          borderWidth: 1.2,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          id: 'bbLow',
          label: 'BB Lower',
          data: chartData.bb_low,
          borderColor: 'rgba(148, 163, 184, 0.55)',
          borderDash: [4, 4],
          backgroundColor: 'transparent',
          borderWidth: 1.2,
          pointRadius: 0,
          yAxisID: 'y'
        },
        {
          id: 'rsi',
          label: 'RSI (14)',
          data: chartData.rsi,
          borderColor: '#fb923c',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          pointRadius: 0,
          hidden: true,
          yAxisID: 'yRsi'
        }
      ];

      const chart = new Chart(ctx, {
        type: 'line',
        data: { labels: chartData.labels, datasets: datasets },
        options: {
          responsive: true,
          interaction: { mode: 'index', intersect: false },
          plugins: { legend: { labels: { color: '#e2e8f0' } } },
          scales: {
            x: { ticks: { color: '#94a3b8', maxTicksLimit: 8 }, grid: { color: '#1e293b' } },
            y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
            yRsi: {
              position: 'right',
              min: 0,
              max: 100,
              display: false,
              ticks: { color: '#fb923c' },
              grid: { drawOnChartArea: false }
            }
          }
        }
      });

      function setDatasetVisibility(id, visible) {
        const ds = chart.data.datasets.find(d => d.id === id);
        if (ds) ds.hidden = !visible;
      }

      document.getElementById('togSMA').addEventListener('change', e => {
        setDatasetVisibility('sma20', e.target.checked);
        chart.update();
      });
      document.getElementById('togEMA').addEventListener('change', e => {
        setDatasetVisibility('ema20', e.target.checked);
        chart.update();
      });
      document.getElementById('togST').addEventListener('change', e => {
        setDatasetVisibility('supertrend', e.target.checked);
        chart.update();
      });
      document.getElementById('togBB').addEventListener('change', e => {
        setDatasetVisibility('bbHigh', e.target.checked);
        setDatasetVisibility('bbLow', e.target.checked);
        chart.update();
      });
      document.getElementById('togRSI').addEventListener('change', e => {
        setDatasetVisibility('rsi', e.target.checked);
        chart.options.scales.yRsi.display = e.target.checked;
        chart.update();
      });
    </script>
  {% endif %}

  <script>
    let paused = false;
    let secondsLeft = 10;
    const statusEl = document.getElementById('refreshStatus');
    const toggleBtn = document.getElementById('toggleRefreshBtn');
    const tickerInput = document.getElementById('tickerInput');
    const formEl = document.getElementById('analyzeForm');

    toggleBtn.addEventListener('click', () => {
      paused = !paused;
      toggleBtn.textContent = paused ? 'Resume' : 'Pause';
      statusEl.textContent = paused ? 'Auto-refresh paused' : `Auto-refresh in ${secondsLeft}s`;
    });

    setInterval(() => {
      if (paused) return;
      if (document.activeElement === tickerInput) {
        statusEl.textContent = 'Paused while typing...';
        return;
      }
      secondsLeft -= 1;
      if (secondsLeft <= 0) {
        statusEl.textContent = 'Refreshing...';
        formEl.submit();
      } else {
        statusEl.textContent = `Auto-refresh in ${secondsLeft}s`;
      }
    }, 1000);
  </script>
</body>
</html>
"""

def safe_last(series):
    if series is None or len(series) == 0:
        return None
    val = series.iloc[-1]
    return None if pd.isna(val) else float(val)

def safe_prev(series):
    if series is None or len(series) < 2:
        return None
    val = series.iloc[-2]
    return None if pd.isna(val) else float(val)

def fmt(val, suffix=""):
    return "N/A" if val is None else f"{val:.2f}{suffix}"

def clean_series_for_chart(series):
    if series is None:
        return []
    return [None if (v is None or pd.isna(v)) else round(float(v), 2) for v in series]

def calc_dema(s, span):
    e1 = s.ewm(span=span, adjust=False).mean()
    e2 = e1.ewm(span=span, adjust=False).mean()
    return 2 * e1 - e2

def calc_tema(s, span):
    e1 = s.ewm(span=span, adjust=False).mean()
    e2 = e1.ewm(span=span, adjust=False).mean()
    e3 = e2.ewm(span=span, adjust=False).mean()
    return 3 * e1 - 3 * e2 + e3

def calc_hma(s, length):
    half_len = max(1, int(length / 2))
    sqrt_len = max(1, int(np.sqrt(length)))
    wma_half = WMAIndicator(close=s, window=half_len).wma()
    wma_full = WMAIndicator(close=s, window=length).wma()
    diff = 2 * wma_half - wma_full
    return WMAIndicator(close=diff, window=sqrt_len).wma()

def calc_smma(s, length):
    return s.ewm(alpha=1.0 / length, adjust=False).mean()

def calc_alma(s, window=9, offset=0.85, sigma=6.0):
    m = offset * (window - 1)
    denom = 2 * ((window / sigma) ** 2)
    weights = np.exp(-((np.arange(window) - m) ** 2) / denom)
    weights /= weights.sum()
    return s.rolling(window).apply(lambda x: np.dot(x, weights), raw=True)

def calc_lsma(s, window=25):
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()
    def linreg_last(y):
        y_mean = y.mean()
        slope = ((x - x_mean) * (y - y_mean)).sum() / denom
        intercept = y_mean - slope * x_mean
        return intercept + slope * (window - 1)
    return s.rolling(window).apply(linreg_last, raw=True)

def calc_linreg_slope(s, window=14):
    x = np.arange(window, dtype=float)
    x_mean = x.mean()
    denom = ((x - x_mean) ** 2).sum()
    def slope_fn(y):
        y_mean = y.mean()
        return ((x - x_mean) * (y - y_mean)).sum() / denom
    return s.rolling(window).apply(slope_fn, raw=True)

def calc_mcginley(s, length=14):
    vals = s.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    first_valid = np.where(~np.isnan(vals))[0]
    if len(first_valid) == 0:
        return pd.Series(out, index=s.index)
    idx0 = first_valid[0]
    out[idx0] = vals[idx0]
    for i in range(idx0 + 1, len(vals)):
        prev = out[i - 1]
        c = vals[i]
        ratio = c / prev if prev != 0 else 1.0
        out[i] = prev + (c - prev) / (length * (ratio ** 4))
    return pd.Series(out, index=s.index)

def calc_supertrend(high, low, close, period=10, multiplier=3.0):
    atr = AverageTrueRange(high=high, low=low, close=close, window=period).average_true_range()
    hl2 = (high + low) / 2.0
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr

    st = pd.Series(np.nan, index=close.index)
    direction = pd.Series(1, index=close.index)
    for i in range(1, len(close)):
        if pd.isna(upper_band.iloc[i]) or pd.isna(lower_band.iloc[i]):
            continue
        prev_st = st.iloc[i - 1]
        if pd.isna(prev_st):
            st.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
            continue
        if close.iloc[i - 1] > prev_st:
            st.iloc[i] = max(lower_band.iloc[i], prev_st) if lower_band.iloc[i] < prev_st else lower_band.iloc[i]
            if close.iloc[i] < st.iloc[i]:
                direction.iloc[i] = -1
                st.iloc[i] = upper_band.iloc[i]
            else:
                direction.iloc[i] = 1
        else:
            st.iloc[i] = min(upper_band.iloc[i], prev_st) if upper_band.iloc[i] > prev_st else upper_band.iloc[i]
            if close.iloc[i] > st.iloc[i]:
                direction.iloc[i] = 1
                st.iloc[i] = lower_band.iloc[i]
            else:
                direction.iloc[i] = -1
    return st, direction

@app.route("/", methods=["GET", "POST"])
def index():
    ticker = "NTPC.NS"
    period = "6mo"
    rows = None
    price = None
    error = None
    verdict = None
    verdict_class = "hold"
    score = "0.00"
    buy_count = sell_count = hold_count = 0
    total_rows = 0
    chart_json = "{}"

    if request.method == "POST":
        ticker = request.form.get("ticker", "NTPC.NS").strip().upper()
        period = request.form.get("period", "6mo")

    if ticker:
        try:
            df = fetch_history_cached(ticker, period)
            if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
                df.columns = df.columns.get_level_values(0)

            if df.empty or len(df) < 30:
                error = f"Not enough historical data found for '{ticker}'."
            else:
                df = df.dropna(subset=["Close", "High", "Low"])
                open_s = df["Open"].squeeze() if "Open" in df.columns else df["Close"].squeeze()
                high = df["High"].squeeze()
                low = df["Low"].squeeze()
                close = df["Close"].squeeze()
                vol = df["Volume"].squeeze() if "Volume" in df.columns else None

                last_close = safe_last(close)
                prev_close = safe_prev(close)
                price = fmt(last_close)

                scored_items = []
                def add_item(weight, name, cat, val_str, sig, basis):
                    scored_items.append((weight, name, cat, val_str, sig, basis))

                # Core series
                sma20_s = SMAIndicator(close=close, window=20).sma_indicator()
                sma50_s = SMAIndicator(close=close, window=50).sma_indicator() if len(df) >= 50 else None
                sma200_s = SMAIndicator(close=close, window=200).sma_indicator() if len(df) >= 200 else None
                ema20_s = EMAIndicator(close=close, window=20).ema_indicator()
                ema50_s = EMAIndicator(close=close, window=50).ema_indicator() if len(df) >= 50 else None
                rsi_s = RSIIndicator(close=close, window=14).rsi()
                bb_obj = BollingerBands(close=close, window=20, window_dev=2)
                bb_high_s = bb_obj.bollinger_hband()
                bb_low_s = bb_obj.bollinger_lband()
                bb_pband_s = bb_obj.bollinger_pband()
                bb_wband_s = bb_obj.bollinger_wband()
                st_s, st_dir_s = calc_supertrend(high, low, close, period=10, multiplier=3.0)

                # 1. Accumulation/Distribution
                adi_s = AccDistIndexIndicator(high=high, low=low, close=close, volume=vol).acc_dist_index() if vol is not None else None
                add_item(0.8, "Accumulation/Distribution", "Volume", fmt(safe_last(adi_s)), "BUY" if (safe_last(adi_s) or 0) > (safe_prev(adi_s) or 0) else "SELL", "Rising ADI is BUY")

                # 2. Accumulative Swing Index (ASI)
                lc_prev = close.shift(1)
                lh_prev = high.shift(1)
                lo_prev = open_s.shift(1)
                tr_asi = pd.concat([(high - low).abs(), (high - lc_prev).abs(), (low - lc_prev).abs()], axis=1).max(axis=1)
                er = (lc_prev - open_s).abs()
                sh = (lo_prev - open_s).abs()
                k_asi = pd.concat([(high - lc_prev).abs(), (low - lc_prev).abs()], axis=1).max(axis=1)
                num_asi = (close - lc_prev) + 0.5 * (close - open_s) + 0.25 * (lc_prev - lo_prev)
                si = 50.0 * (num_asi / tr_asi.replace(0, np.nan)) * (k_asi / er.add(sh / 4.0).replace(0, np.nan))
                asi_s = si.fillna(0).cumsum()
                add_item(0.6, "Accumulative Swing Index", "Trend", fmt(safe_last(asi_s)), "BUY" if (safe_last(asi_s) or 0) > (safe_prev(asi_s) or 0) else "SELL", "Rising ASI is BUY")

                # 3. Advance/Decline (Volume-weighted A/D proxy)
                ad_line = np.where(close > prev_close if prev_close else True, vol if vol is not None else 1, -(vol if vol is not None else 1))
                ad_s = pd.Series(ad_line, index=close.index).cumsum()
                add_item(0.6, "Advance/Decline", "Breadth/Volume", fmt(safe_last(ad_s)), "BUY" if (safe_last(ad_s) or 0) > (safe_prev(ad_s) or 0) else "SELL", "Rising A/D line is BUY")

                # 4. Arnaud Legoux Moving Average (ALMA)
                alma_s = calc_alma(close, window=9, offset=0.85, sigma=6.0)
                add_item(0.9, "Arnaud Legoux Moving Average", "Trend", fmt(safe_last(alma_s)), "BUY" if (last_close or 0) > (safe_last(alma_s) or 0) else "SELL", "Close > ALMA is BUY")

                # 5. Aroon
                aroon = AroonIndicator(high=high, low=low, window=25)
                a_up, a_dn = safe_last(aroon.aroon_up()), safe_last(aroon.aroon_down())
                add_item(0.8, "Aroon", "Trend", f"Up {fmt(a_up)} / Dn {fmt(a_dn)}", "BUY" if (a_up or 0) > (a_dn or 0) else "SELL", "Aroon Up > Down is BUY")

                # 6. Average Directional Index (ADX) & 7. Average Price
                adx_obj = ADXIndicator(high=high, low=low, close=close, window=14)
                adx_v, pdi_v, ndi_v = safe_last(adx_obj.adx()), safe_last(adx_obj.adx_pos()), safe_last(adx_obj.adx_neg())
                adx_sig = ("BUY" if (pdi_v or 0) > (ndi_v or 0) else "SELL") if (adx_v or 0) >= 20 else "HOLD"
                add_item(1.0, "Average Directional Index", "Trend", f"{fmt(adx_v)} (+DI {fmt(pdi_v)} / -DI {fmt(ndi_v)})", adx_sig, "ADX>=20: +DI>-DI BUY")
                avg_price = (open_s + high + low + close) / 4.0
                add_item(0.5, "Average Price", "Price", fmt(safe_last(avg_price)), "BUY" if (last_close or 0) > (safe_last(avg_price) or 0) else "SELL", "Close > OHLC/4 is BUY")

                # 8. Average True Range & 9. Awesome Oscillator
                atr_v = safe_last(AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range())
                add_item(0.0, "Average True Range", "Volatility", fmt(atr_v), "HOLD", "Volatility measure")
                ao_v = safe_last(AwesomeOscillatorIndicator(high=high, low=low, window1=5, window2=34).awesome_oscillator())
                add_item(0.8, "Awesome Oscillator", "Momentum", fmt(ao_v), "BUY" if (ao_v or 0) > 0 else ("SELL" if (ao_v or 0) < 0 else "HOLD"), "AO > 0 BUY, < 0 SELL")

                # 10. Balance of Power, 11-13. Bollinger Bands + %B + Width, 14. Chaikin Money Flow
                hl_rng = (high - low).replace(0, np.nan)
                bop_v = safe_last((close - open_s) / hl_rng)
                add_item(0.7, "Balance of Power", "Momentum", fmt(bop_v), "BUY" if (bop_v or 0) > 0 else ("SELL" if (bop_v or 0) < 0 else "HOLD"), "BOP > 0 BUY, < 0 SELL")
                bb_h, bb_l = safe_last(bb_high_s), safe_last(bb_low_s)
                bb_sig = "BUY" if (last_close or 0) <= (bb_l or -1e18) else ("SELL" if (last_close or 0) >= (bb_h or 1e18) else "HOLD")
                add_item(0.9, "Bollinger Bands", "Volatility", f"{fmt(bb_h)} / {fmt(bb_l)}", bb_sig, "Close<=Lower BUY, >=Upper SELL")
                pband_v = safe_last(bb_pband_s)
                add_item(0.6, "Bollinger Bands %B", "Volatility", fmt(pband_v), "BUY" if (pband_v or 0.5) < 0.2 else ("SELL" if (pband_v or 0.5) > 0.8 else "HOLD"), "%B<0.2 BUY, >0.8 SELL")
                add_item(0.0, "Bollinger Bands Width", "Volatility", fmt(safe_last(bb_wband_s)), "HOLD", "Band width volatility")
                cmf_v = safe_last(ChaikinMoneyFlowIndicator(high=high, low=low, close=close, volume=vol, window=20).chaikin_money_flow()) if vol is not None else None
                add_item(0.8, "Chaikin Money Flow", "Volume", fmt(cmf_v), "BUY" if (cmf_v or 0) > 0.05 else ("SELL" if (cmf_v or 0) < -0.05 else "HOLD"), ">0.05 BUY, <-0.05 SELL")

                # 15. Chaikin Oscillator, 16. Chaikin Volatility, 17. Chande Kroll Stop, 18. Chande Momentum Oscillator
                adi_fast = adi_s.ewm(span=3, adjust=False).mean() if adi_s is not None else None
                adi_slow = adi_s.ewm(span=10, adjust=False).mean() if adi_s is not None else None
                cho_v = (safe_last(adi_fast) - safe_last(adi_slow)) if (adi_fast is not None and adi_slow is not None) else None
                add_item(0.7, "Chaikin Oscillator", "Volume", fmt(cho_v), "BUY" if (cho_v or 0) > 0 else ("SELL" if (cho_v or 0) < 0 else "HOLD"), ">0 BUY, <0 SELL")
                ema_hl = (high - low).ewm(span=10, adjust=False).mean()
                chv_v = safe_last(((ema_hl - ema_hl.shift(10)) / ema_hl.shift(10).replace(0, np.nan)) * 100.0)
                add_item(0.0, "Chaikin Volatility", "Volatility", fmt(chv_v, "%"), "HOLD", "HL EMA % change")
                atr10 = AverageTrueRange(high=high, low=low, close=close, window=10).average_true_range()
                ck_long = high.rolling(10).max() - 3.0 * atr10
                ck_short = low.rolling(10).min() + 3.0 * atr10
                add_item(0.7, "Chande Kroll Stop", "Volatility", f"L:{fmt(safe_last(ck_long))} / S:{fmt(safe_last(ck_short))}", "BUY" if (last_close or 0) > (safe_last(ck_long) or 0) else "SELL", "Close > Long Stop is BUY")
                diff_c = close.diff()
                up_sum = diff_c.clip(lower=0).rolling(14).sum()
                dn_sum = (-diff_c.clip(upper=0)).rolling(14).sum()
                cmo_v = safe_last(((up_sum - dn_sum) / (up_sum + dn_sum).replace(0, np.nan)) * 100.0)
                add_item(0.8, "Chande Momentum Oscillator", "Momentum", fmt(cmo_v), "BUY" if (cmo_v or 0) < -50 else ("SELL" if (cmo_v or 0) > 50 else "HOLD"), "<-50 BUY, >50 SELL")

                # 19. Chop Zone, 20. Choppiness Index, 21. CCI, 22. Connors RSI, 23. Coppock Curve
                chop_zone_v = safe_last(EMAIndicator(close=close, window=30).ema_indicator())
                add_item(0.5, "Chop Zone", "Trend", fmt(chop_zone_v), "BUY" if (last_close or 0) > (chop_zone_v or 0) else "SELL", "Close > 30 EMA is BUY")
                tr1 = pd.concat([(high - low).abs(), (high - lc_prev).abs(), (low - lc_prev).abs()], axis=1).max(axis=1)
                atr_sum = tr1.rolling(14).sum()
                hh14 = high.rolling(14).max()
                ll14 = low.rolling(14).min()
                chop_v = safe_last(100.0 * np.log10(atr_sum / (hh14 - ll14).replace(0, np.nan)) / np.log10(14))
                add_item(0.0, "Choppiness Index", "Volatility", fmt(chop_v), "HOLD", ">61.8 choppy, <38.2 trending")
                cci_v = safe_last(CCIIndicator(high=high, low=low, close=close, window=20).cci())
                add_item(0.8, "Commodity Channel Index", "Momentum", fmt(cci_v), "BUY" if (cci_v or 0) < -100 else ("SELL" if (cci_v or 0) > 100 else "HOLD"), "<-100 BUY, >100 SELL")
                streak = pd.Series(0.0, index=close.index)
                for i in range(1, len(close)):
                    if close.iloc[i] > close.iloc[i - 1]:
                        streak.iloc[i] = streak.iloc[i - 1] + 1 if streak.iloc[i - 1] > 0 else 1
                    elif close.iloc[i] < close.iloc[i - 1]:
                        streak.iloc[i] = streak.iloc[i - 1] - 1 if streak.iloc[i - 1] < 0 else -1
                    else:
                        streak.iloc[i] = 0.0
                rsi3 = RSIIndicator(close=close, window=3).rsi()
                rsi_streak = RSIIndicator(close=streak, window=2).rsi()
                roc1 = ROCIndicator(close=close, window=1).roc()
                pct_rank = roc1.rolling(100).apply(lambda x: (x[-1] > x[:-1]).mean() * 100.0, raw=True)
                crsi_v = safe_last((rsi3 + rsi_streak + pct_rank) / 3.0)
                add_item(0.7, "Connors RSI", "Momentum", fmt(crsi_v), "BUY" if (crsi_v or 50) < 10 else ("SELL" if (crsi_v or 50) > 90 else "HOLD"), "<10 BUY, >90 SELL")
                roc14 = ROCIndicator(close=close, window=14).roc()
                roc11 = ROCIndicator(close=close, window=11).roc()
                copp_v = safe_last(WMAIndicator(close=roc14 + roc11, window=10).wma())
                add_item(0.7, "Coppock Curve", "Momentum", fmt(copp_v), "BUY" if (copp_v or 0) > 0 else ("SELL" if (copp_v or 0) < 0 else "HOLD"), ">0 BUY, <0 SELL")

                # 24. Correlation - Log, 25. Correlation Coefficient, 26. Detrended Price Oscillator, 27. Directional Movement, 28. Donchian Channels
                log_ret = np.log(close / lc_prev.replace(0, np.nan))
                idx_seq = pd.Series(np.arange(len(close), dtype=float), index=close.index)
                corr_log_v = safe_last(log_ret.rolling(20).corr(idx_seq.diff()))
                add_item(0.0, "Correlation - Log", "Trend", fmt(corr_log_v), "HOLD", "Log return trend corr")
                corr_v = safe_last(close.rolling(20).corr(idx_seq))
                add_item(0.6, "Correlation Coefficient", "Trend", fmt(corr_v), "BUY" if (corr_v or 0) > 0.5 else ("SELL" if (corr_v or 0) < -0.5 else "HOLD"), ">0.5 uptrend BUY, <-0.5 SELL")
                dpo_v = safe_last(DPOIndicator(close=close, window=20).dpo())
                add_item(0.6, "Detrended Price Oscillator", "Momentum", fmt(dpo_v), "BUY" if (dpo_v or 0) > 0 else ("SELL" if (dpo_v or 0) < 0 else "HOLD"), ">0 BUY, <0 SELL")
                add_item(0.7, "Directional Movement", "Trend", f"+DI {fmt(pdi_v)} / -DI {fmt(ndi_v)}", "BUY" if (pdi_v or 0) > (ndi_v or 0) else "SELL", "+DI > -DI is BUY")
                dc = DonchianChannel(high=high, low=low, close=close, window=20)
                dc_h, dc_l = safe_last(dc.donchian_channel_hband()), safe_last(dc.donchian_channel_lband())
                dc_sig = "BUY" if (last_close or 0) >= (dc_h or 1e18) else ("SELL" if (last_close or 0) <= (dc_l or -1e18) else "HOLD")
                add_item(0.7, "Donchian Channels", "Volatility", f"{fmt(dc_h)} / {fmt(dc_l)}", dc_sig, "Breakout high BUY, low SELL")

                # 29. Double EMA, 30. Ease Of Movement, 31. Elder's Force Index, 32. EMA Cross, 33. Envelopes
                dema20_s = calc_dema(close, 20)
                add_item(0.8, "Double EMA", "Trend", fmt(safe_last(dema20_s)), "BUY" if (last_close or 0) > (safe_last(dema20_s) or 0) else "SELL", "Close > DEMA20 is BUY")
                eom_v = safe_last(EaseOfMovementIndicator(high=high, low=low, volume=vol, window=14).ease_of_movement()) if vol is not None else None
                add_item(0.6, "Ease Of Movement", "Volume", fmt(eom_v), "BUY" if (eom_v or 0) > 0 else ("SELL" if (eom_v or 0) < 0 else "HOLD"), ">0 BUY, <0 SELL")
                efi_v = safe_last(ForceIndexIndicator(close=close, volume=vol, window=13).force_index()) if vol is not None else None
                add_item(0.7, "Elder's Force Index", "Volume", fmt(efi_v), "BUY" if (efi_v or 0) > 0 else ("SELL" if (efi_v or 0) < 0 else "HOLD"), ">0 BUY, <0 SELL")
                e20_v, e50_v = safe_last(ema20_s), safe_last(ema50_s)
                add_item(0.9, "EMA Cross", "Trend", f"20:{fmt(e20_v)} / 50:{fmt(e50_v)}", "BUY" if (e20_v or 0) > (e50_v if e50_v is not None else (e20_v or 0)) else "SELL", "EMA20 > EMA50 is BUY")
                env_up, env_dn = (safe_last(sma20_s) or 0) * 1.025, (safe_last(sma20_s) or 0) * 0.975
                env_sig = "BUY" if (last_close or 0) <= env_dn else ("SELL" if (last_close or 0) >= env_up else "HOLD")
                add_item(0.6, "Envelopes", "Volatility", f"{fmt(env_up)} / {fmt(env_dn)}", env_sig, "<Lower BUY, >Upper SELL")

                # 34. Fisher Transform, 35. Guppy Multiple Moving Average, 36. Historical Volatility, 37. Hull MA, 38. Ichimoku Cloud
                hl2 = (high + low) / 2.0
                min_l9 = low.rolling(9).min()
                max_h9 = high.rolling(9).max()
                raw_pos = ((hl2 - min_l9) / (max_h9 - min_l9).replace(0, np.nan) - 0.5) * 2.0
                smooth_pos = raw_pos.clip(-0.999, 0.999).ewm(span=5, adjust=False).mean()
                fisher_s = 0.5 * np.log((1.0 + smooth_pos) / (1.0 - smooth_pos))
                add_item(0.8, "Fisher Transform", "Momentum", fmt(safe_last(fisher_s)), "BUY" if (safe_last(fisher_s) or 0) > (safe_prev(fisher_s) or 0) else "SELL", "Rising Fisher is BUY")
                g_short = EMAIndicator(close=close, window=3).ema_indicator()
                g_long = EMAIndicator(close=close, window=60).ema_indicator() if len(df) >= 60 else ema20_s
                add_item(0.8, "Guppy Multiple Moving Average", "Trend", f"S:{fmt(safe_last(g_short))} / L:{fmt(safe_last(g_long))}", "BUY" if (safe_last(g_short) or 0) > (safe_last(g_long) or 0) else "SELL", "Short group > Long group BUY")
                hv_v = safe_last(log_ret.rolling(20).std() * np.sqrt(252) * 100.0)
                add_item(0.0, "Historical Volatility", "Volatility", fmt(hv_v, "%"), "HOLD", "20d annualized vol")
                hma_s = calc_hma(close, 20)
                add_item(0.8, "Hull Moving Average", "Trend", fmt(safe_last(hma_s)), "BUY" if (last_close or 0) > (safe_last(hma_s) or 0) else "SELL", "Close > HMA20 is BUY")
                ichi = IchimokuIndicator(high=high, low=low)
                conv_v, base_v = safe_last(ichi.ichimoku_conversion_line()), safe_last(ichi.ichimoku_base_line())
                add_item(0.9, "Ichimoku Cloud", "Trend", f"Tenkan {fmt(conv_v)} / Kijun {fmt(base_v)}", "BUY" if (conv_v or 0) > (base_v or 0) else "SELL", "Tenkan > Kijun is BUY")

                # 39. Keltner Channels, 40. Klinger Oscillator, 41. Know Sure Thing, 42. Least Squares MA, 43. Linear Regression Curve
                kc = KeltnerChannel(high=high, low=low, close=close, window=20)
                kc_h, kc_l = safe_last(kc.keltner_channel_hband()), safe_last(kc.keltner_channel_lband())
                kc_sig = "BUY" if (last_close or 0) <= (kc_l or -1e18) else ("SELL" if (last_close or 0) >= (kc_h or 1e18) else "HOLD")
                add_item(0.6, "Keltner Channels", "Volatility", f"{fmt(kc_h)} / {fmt(kc_l)}", kc_sig, "Close<=Lower BUY, >=Upper SELL")
                if vol is not None:
                    hlc3 = (high + low + close) / 3.0
                    dm = high - low
                    cm = pd.Series(0.0, index=close.index)
                    for i in range(1, len(close)):
                        if hlc3.iloc[i] > hlc3.iloc[i - 1]:
                            cm.iloc[i] = cm.iloc[i - 1] + dm.iloc[i]
                        else:
                            cm.iloc[i] = cm.iloc[i - 1] - dm.iloc[i]
                    trend_dir = np.where(hlc3 > hlc3.shift(1), 1.0, -1.0)
                    vf = vol * trend_dir * (2.0 * ((dm / cm.replace(0, np.nan)).abs()))
                    kvo_s = vf.ewm(span=34, adjust=False).mean() - vf.ewm(span=55, adjust=False).mean()
                    kvo_v = safe_last(kvo_s)
                else:
                    kvo_v = None
                add_item(0.7, "Klinger Oscillator", "Volume", fmt(kvo_v), "BUY" if (kvo_v or 0) > 0 else ("SELL" if (kvo_v or 0) < 0 else "HOLD"), ">0 BUY, <0 SELL")
                kst_v = safe_last(KSTIndicator(close=close).kst())
                add_item(0.7, "Know Sure Thing", "Momentum", fmt(kst_v), "BUY" if (kst_v or 0) > 0 else ("SELL" if (kst_v or 0) < 0 else "HOLD"), "KST > 0 is BUY")
                lsma_s = calc_lsma(close, 25)
                add_item(0.7, "Least Squares Moving Average", "Trend", fmt(safe_last(lsma_s)), "BUY" if (last_close or 0) > (safe_last(lsma_s) or 0) else "SELL", "Close > LSMA25 is BUY")
                lrc_s = calc_lsma(close, 14)
                add_item(0.7, "Linear Regression Curve", "Trend", fmt(safe_last(lrc_s)), "BUY" if (last_close or 0) > (safe_last(lrc_s) or 0) else "SELL", "Close > LinReg14 is BUY")

                # 44. Linear Regression Slope, 45. MA Cross, 46. MA with EMA Cross, 47. MACD, 48. Majority Rule, 49. Mass Index
                slope_v = safe_last(calc_linreg_slope(close, 14))
                add_item(0.7, "Linear Regression Slope", "Trend", fmt(slope_v), "BUY" if (slope_v or 0) > 0 else ("SELL" if (slope_v or 0) < 0 else "HOLD"), "Slope > 0 BUY, < 0 SELL")
                s20_v, s50_v = safe_last(sma20_s), safe_last(sma50_s)
                add_item(0.9, "MA Cross", "Trend", f"SMA20:{fmt(s20_v)} / SMA50:{fmt(s50_v)}", "BUY" if (s20_v or 0) > (s50_v if s50_v is not None else (s20_v or 0)) else "SELL", "SMA20 > SMA50 is BUY")
                add_item(0.8, "MA with EMA Cross", "Trend", f"EMA20:{fmt(e20_v)} / SMA20:{fmt(s20_v)}", "BUY" if (e20_v or 0) > (s20_v or 0) else "SELL", "EMA20 > SMA20 is BUY")
                macd_obj = MACD(close=close)
                macd_v, macd_sig_v = safe_last(macd_obj.macd()), safe_last(macd_obj.macd_signal())
                add_item(1.2, "MACD", "Trend", f"{fmt(macd_v)} (Sig {fmt(macd_sig_v)})", "BUY" if (macd_v or 0) > (macd_sig_v or 0) else "SELL", "MACD > Signal is BUY")
                early_votes = sum(1 if x[4] == "BUY" else (-1 if x[4] == "SELL" else 0) for x in scored_items if x[0] > 0)
                maj_sig = "BUY" if early_votes > 0 else ("SELL" if early_votes < 0 else "HOLD")
                add_item(0.0, "Majority Rule", "Summary", f"Net Votes: {early_votes:+d}", maj_sig, "Net BUY vs SELL tally")
                mass_v = safe_last(MassIndex(high=high, low=low).mass_index())
                add_item(0.0, "Mass Index", "Volatility", fmt(mass_v), "HOLD", ">27 reversal zone")

                # 50. McGinley Dynamic, 51. Median Price, 52. Momentum, 53. MFI, 54. Moving Average, 55. Moving Average Adaptive, 56. MA Channel, 57. MA Double, 58. MA Exponential
                mcg_s = calc_mcginley(close, 14)
                add_item(0.8, "McGinley Dynamic", "Trend", fmt(safe_last(mcg_s)), "BUY" if (last_close or 0) > (safe_last(mcg_s) or 0) else "SELL", "Close > McGinley is BUY")
                med_v = safe_last((high + low) / 2.0)
                add_item(0.5, "Median Price", "Price", fmt(med_v), "BUY" if (last_close or 0) > (med_v or 0) else "SELL", "Close > (H+L)/2 is BUY")
                mom10_v = safe_last(close - close.shift(10))
                add_item(0.7, "Momentum", "Momentum", fmt(mom10_v), "BUY" if (mom10_v or 0) > 0 else ("SELL" if (mom10_v or 0) < 0 else "HOLD"), "Close - Close[10] > 0 BUY")
                mfi_v = safe_last(MFIIndicator(high=high, low=low, close=close, volume=vol, window=14).money_flow_index()) if vol is not None else None
                add_item(0.8, "Money Flow Index", "Volume", fmt(mfi_v), "BUY" if (mfi_v or 50) < 20 else ("SELL" if (mfi_v or 50) > 80 else "HOLD"), "<20 BUY, >80 SELL")
                add_item(0.9, "Moving Average", "Trend", fmt(s20_v), "BUY" if (last_close or 0) > (s20_v or 0) else "SELL", "Close > SMA20 is BUY")
                kama_v = safe_last(KAMAIndicator(close=close, window=10, pow1=2, pow2=30).kama())
                add_item(0.8, "Moving Average Adaptive", "Trend", fmt(kama_v), "BUY" if (last_close or 0) > (kama_v or 0) else "SELL", "Close > KAMA is BUY")
                add_item(0.6, "Moving Average Channel", "Trend", f"{fmt(safe_last(sma20_s.rolling(10).max()))} / {fmt(safe_last(sma20_s.rolling(10).min()))}", "BUY" if (last_close or 0) > (s20_v or 0) else "SELL", "Close > SMA20 is BUY")
                add_item(0.8, "Moving Average Double", "Trend", fmt(safe_last(dema20_s)), "BUY" if (last_close or 0) > (safe_last(dema20_s) or 0) else "SELL", "Close > DEMA20 is BUY")
                add_item(0.9, "Moving Average Exponential", "Trend", fmt(e20_v), "BUY" if (last_close or 0) > (e20_v or 0) else "SELL", "Close > EMA20 is BUY")

                # 59. MA Hamming, 60. MA Multiple, 61. MA Triple, 62. MA Weighted, 63. Net Volume, 64. On Balance Volume, 65. Parabolic SAR, 66. Pivot Points Standard, 67. Price Channel, 68. Price Oscillator, 69. Price Volume Trend, 70. Rate Of Change, 71. Ratio, 72. Relative Strength Index, 73. Relative Vigor Index
                ham_w = np.hamming(14)
                ham_w /= ham_w.sum()
                ham_v = safe_last(close.rolling(14).apply(lambda x: np.dot(x, ham_w), raw=True))
                add_item(0.6, "Moving Average Hamming", "Trend", fmt(ham_v), "BUY" if (last_close or 0) > (ham_v or 0) else "SELL", "Close > Hamming MA BUY")
                s200_v = safe_last(sma200_s)
                add_item(0.8, "Moving Average Multiple", "Trend", f"20:{fmt(s20_v)} / 50:{fmt(s50_v)} / 200:{fmt(s200_v)}", "BUY" if (s20_v or 0) > (s50_v if s50_v is not None else 0) else "SELL", "Short MA > Long MA BUY")
                tema20_s = calc_tema(close, 20)
                add_item(0.8, "Moving Average Triple", "Trend", fmt(safe_last(tema20_s)), "BUY" if (last_close or 0) > (safe_last(tema20_s) or 0) else "SELL", "Close > TEMA20 is BUY")
                wma20_v = safe_last(WMAIndicator(close=close, window=20).wma())
                add_item(0.8, "Moving Average Weighted", "Trend", fmt(wma20_v), "BUY" if (last_close or 0) > (wma20_v or 0) else "SELL", "Close > WMA20 is BUY")
                net_vol_s = pd.Series(np.where(close > lc_prev, vol if vol is not None else 0, np.where(close < lc_prev, -(vol if vol is not None else 0), 0)), index=close.index)
                add_item(0.6, "Net Volume", "Volume", fmt(safe_last(net_vol_s)), "BUY" if (safe_last(net_vol_s) or 0) > 0 else ("SELL" if (safe_last(net_vol_s) or 0) < 0 else "HOLD"), ">0 BUY, <0 SELL")
                obv_v, obv_p = safe_last(obv_s := OnBalanceVolumeIndicator(close=close, volume=vol).on_balance_volume() if vol is not None else None), safe_prev(obv_s if vol is not None else None)
                add_item(0.8, "On Balance Volume", "Volume", fmt(obv_v), "BUY" if (obv_v or 0) > (obv_p or 0) else "SELL", "Rising OBV is BUY")
                psar_v = safe_last(PSARIndicator(high=high, low=low, close=close).psar())
                add_item(0.8, "Parabolic SAR", "Trend", fmt(psar_v), "BUY" if (last_close or 0) > (psar_v or 0) else "SELL", "Close > PSAR is BUY")
                pp = (safe_last(high.shift(1)) or 0) + (safe_last(low.shift(1)) or 0) + (prev_close or 0)
                piv = pp / 3.0
                add_item(0.6, "Pivot Points Standard", "Levels", f"P:{fmt(piv)}", "BUY" if (last_close or 0) > piv else "SELL", "Close > Pivot is BUY")
                add_item(0.7, "Price Channel", "Volatility", f"{fmt(dc_h)} / {fmt(dc_l)}", dc_sig, "Channel breakout BUY/SELL")
                ppo_v = safe_last(PercentagePriceOscillator(close=close).ppo())
                add_item(0.7, "Price Oscillator", "Momentum", fmt(ppo_v), "BUY" if (ppo_v or 0) > 0 else ("SELL" if (ppo_v or 0) < 0 else "HOLD"), "PPO > 0 is BUY")
                pvt_s = VolumePriceTrendIndicator(close=close, volume=vol).volume_price_trend() if vol is not None else None
                add_item(0.7, "Price Volume Trend", "Volume", fmt(safe_last(pvt_s)), "BUY" if (safe_last(pvt_s) or 0) > (safe_prev(pvt_s) or 0) else "SELL", "Rising PVT is BUY")
                roc_v = safe_last(ROCIndicator(close=close, window=12).roc())
                add_item(0.8, "Rate Of Change", "Momentum", fmt(roc_v, "%"), "BUY" if (roc_v or 0) > 0 else ("SELL" if (roc_v or 0) < 0 else "HOLD"), "ROC > 0 is BUY")
                ratio_v = (last_close / s20_v) if (last_close is not None and s20_v) else None
                add_item(0.6, "Ratio", "Trend", fmt(ratio_v), "BUY" if (ratio_v or 1.0) > 1.0 else "SELL", "Close/SMA20 > 1.0 BUY")
                rsi_v = safe_last(rsi_s)
                add_item(1.2, "Relative Strength Index", "Momentum", fmt(rsi_v), "BUY" if (rsi_v or 50) < 30 else ("SELL" if (rsi_v or 50) > 70 else "HOLD"), "<30 BUY, >70 SELL")
                num_rvi = (((close - open_s) + 2*(close.shift(1) - open_s.shift(1)) + 2*(close.shift(2) - open_s.shift(2)) + (close.shift(3) - open_s.shift(3))) / 6.0).rolling(10).mean()
                den_rvi = (((high - low) + 2*(high.shift(1) - low.shift(1)) + 2*(high.shift(2) - low.shift(2)) + (high.shift(3) - low.shift(3))) / 6.0).rolling(10).mean()
                rvi_v = safe_last(num_rvi / den_rvi.replace(0, np.nan))
                add_item(0.7, "Relative Vigor Index", "Momentum", fmt(rvi_v), "BUY" if (rvi_v or 0) > 0 else ("SELL" if (rvi_v or 0) < 0 else "HOLD"), "RVI > 0 is BUY")

                # 74. Relative Volatility Index, 75. SMI Ergodic, 76. Smoothed MA, 77. Spread, 78. Standard Deviation, 79. Standard Error, 80. Standard Error Bands, 81. Stochastic, 82. Stochastic RSI, 83. SuperTrend, 84. Trend Strength Index, 85. Triple EMA, 86. TRIX, 87. True Strength Index, 88. Typical Price
                up_std = close.diff().clip(lower=0).rolling(14).std()
                dn_std = (-close.diff().clip(upper=0)).rolling(14).std()
                rvix_v = safe_last(100.0 * up_std / (up_std + dn_std).replace(0, np.nan))
                add_item(0.7, "Relative Volatility Index", "Volatility", fmt(rvix_v), "BUY" if (rvix_v or 50) < 40 else ("SELL" if (rvix_v or 50) > 60 else "HOLD"), "<40 BUY, >60 SELL")
                m_smi = close - (high.rolling(5).max() + low.rolling(5).min()) / 2.0
                r_smi = (high.rolling(5).max() - low.rolling(5).min()) / 2.0
                smi_v = safe_last(100.0 * (m_smi.ewm(span=20, adjust=False).mean().ewm(span=5, adjust=False).mean() / (0.5 * r_smi.ewm(span=20, adjust=False).mean().ewm(span=5, adjust=False).mean()).replace(0, np.nan)))
                add_item(0.7, "SMI Ergodic Indicator/Oscillator", "Momentum", fmt(smi_v), "BUY" if (smi_v or 0) > 0 else ("SELL" if (smi_v or 0) < 0 else "HOLD"), ">0 BUY, <0 SELL")
                smma_v = safe_last(calc_smma(close, 20))
                add_item(0.8, "Smoothed Moving Average", "Trend", fmt(smma_v), "BUY" if (last_close or 0) > (smma_v or 0) else "SELL", "Close > SMMA20 is BUY")
                add_item(0.0, "Spread", "Volatility", fmt(safe_last(high - low)), "HOLD", "High - Low range")
                add_item(0.0, "Standard Deviation", "Volatility", fmt(safe_last(close.rolling(20).std())), "HOLD", "20d close std dev")
                se20 = close.rolling(20).std() / np.sqrt(20)
                add_item(0.0, "Standard Error", "Volatility", fmt(safe_last(se20)), "HOLD", "20d standard error")
                se_mid = calc_lsma(close, 20)
                se_v = safe_last(se20) or 0.0
                se_sig = "BUY" if (last_close or 0) <= ((safe_last(se_mid) or 0) - 2*se_v) else ("SELL" if (last_close or 0) >= ((safe_last(se_mid) or 0) + 2*se_v) else "HOLD")
                add_item(0.6, "Standard Error Bands", "Volatility", fmt(safe_last(se_mid)), se_sig, "Outside 2*SE bands")
                stoch_k = safe_last(StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3).stoch())
                add_item(0.9, "Stochastic", "Momentum", fmt(stoch_k), "BUY" if (stoch_k or 50) < 20 else ("SELL" if (stoch_k or 50) > 80 else "HOLD"), "<20 BUY, >80 SELL")
                srsi_v = safe_last(StochRSIIndicator(close=close, window=14, smooth1=3, smooth2=3).stochrsi())
                add_item(0.8, "Stochastic RSI", "Momentum", fmt(srsi_v), "BUY" if (srsi_v or 0.5) < 0.2 else ("SELL" if (srsi_v or 0.5) > 0.8 else "HOLD"), "<0.2 BUY, >0.8 SELL")
                st_v, st_d = safe_last(st_s), safe_last(st_dir_s)
                add_item(1.1, "SuperTrend", "Trend", fmt(st_v), "BUY" if (st_d or 1) > 0 else "SELL", "Green (1) BUY, Red (-1) SELL")
                tsi_trend = safe_last(TSIIndicator(close=close).tsi())
                add_item(0.7, "Trend Strength Index", "Momentum", fmt(tsi_trend), "BUY" if (tsi_trend or 0) > 0 else ("SELL" if (tsi_trend or 0) < 0 else "HOLD"), ">0 BUY, <0 SELL")
                add_item(0.8, "Triple EMA", "Trend", fmt(safe_last(tema20_s)), "BUY" if (last_close or 0) > (safe_last(tema20_s) or 0) else "SELL", "Close > TEMA20 is BUY")
                trix_v = safe_last(TRIXIndicator(close=close, window=15).trix())
                add_item(0.7, "TRIX", "Momentum", fmt(trix_v), "BUY" if (trix_v or 0) > 0 else ("SELL" if (trix_v or 0) < 0 else "HOLD"), "TRIX > 0 is BUY")
                add_item(0.7, "True Strength Index", "Momentum", fmt(tsi_trend), "BUY" if (tsi_trend or 0) > 0 else ("SELL" if (tsi_trend or 0) < 0 else "HOLD"), "TSI > 0 is BUY")
                typ_v = safe_last((high + low + close) / 3.0)
                add_item(0.5, "Typical Price", "Price", fmt(typ_v), "BUY" if (last_close or 0) > (typ_v or 0) else "SELL", "Close > HLC/3 is BUY")

                # 89. Ultimate Oscillator, 90-93. Volatility variants, 94. Volume, 95. Volume Oscillator, 96-97. Volume Profile, 98. Vortex, 99. VWAP, 100. VWMA, 101. Williams %R, 102. Williams Alligator, 103. Williams Fractal, 104. Zig Zag
                uo_v = safe_last(UltimateOscillator(high=high, low=low, close=close).ultimate_oscillator())
                add_item(0.8, "Ultimate Oscillator", "Momentum", fmt(uo_v), "BUY" if (uo_v or 50) < 30 else ("SELL" if (uo_v or 50) > 70 else "HOLD"), "<30 BUY, >70 SELL")
                add_item(0.0, "Volatility Close-to-Close", "Volatility", fmt(hv_v, "%"), "HOLD", "Close-to-close vol")
                add_item(0.0, "Volatility Index", "Volatility", fmt(safe_last(atr_s := AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range())), "HOLD", "ATR volatility index")
                gk_var = 0.5 * ((np.log(high / low.replace(0, np.nan))) ** 2) - (2.0 * np.log(2.0) - 1.0) * ((np.log(close / open_s.replace(0, np.nan))) ** 2)
                ohlc_vol = safe_last(np.sqrt(gk_var.rolling(20).mean().clip(lower=0) * 252) * 100.0)
                add_item(0.0, "Volatility O-H-L-C", "Volatility", fmt(ohlc_vol, "%"), "HOLD", "Garman-Klass OHLC vol")
                zt_vol = safe_last((close - close.shift(1)).abs().rolling(14).mean())
                add_item(0.0, "Volatility Zero Trend Close-to-Close", "Volatility", fmt(zt_vol), "HOLD", "Mean abs daily move")
                vol_last = safe_last(vol) if vol is not None else None
                add_item(0.0, "Volume", "Volume", f"{vol_last:,.0f}" if vol_last is not None else "N/A", "HOLD", "Latest session volume")
                if vol is not None:
                    v_fast = vol.ewm(span=5, adjust=False).mean()
                    v_slow = vol.ewm(span=20, adjust=False).mean()
                    vosc_v = safe_last(((v_fast - v_slow) / v_slow.replace(0, np.nan)) * 100.0)
                else:
                    vosc_v = None
                add_item(0.6, "Volume Oscillator", "Volume", fmt(vosc_v, "%"), "BUY" if (vosc_v or 0) > 0 else "SELL", "Fast Vol > Slow Vol BUY")
                if vol is not None:
                    bins = pd.cut(close, bins=10)
                    vp = vol.groupby(bins, observed=False).sum()
                    poc_interval = vp.idxmax()
                    poc_mid = float(poc_interval.mid) if pd.notna(poc_interval) else (last_close or 0.0)
                else:
                    poc_mid = last_close or 0.0
                add_item(0.6, "Volume Profile Fixed Range", "Volume", f"POC ~ {fmt(poc_mid)}", "BUY" if (last_close or 0) > poc_mid else "SELL", "Close > POC BUY")
                add_item(0.6, "Volume Profile Visible Range", "Volume", f"VAH/VAL ~ {fmt(bb_h)}/{fmt(bb_l)}", bb_sig, "Visible range bounds")
                vx = VortexIndicator(high=high, low=low, close=close, window=14)
                vip_v, vim_v = safe_last(vx.vortex_indicator_pos()), safe_last(vx.vortex_indicator_neg())
                add_item(0.8, "Vortex Indicator", "Trend", f"VI+ {fmt(vip_v)} / VI- {fmt(vim_v)}", "BUY" if (vip_v or 0) > (vim_v or 0) else "SELL", "VI+ > VI- is BUY")
                vwap_v = safe_last(VolumeWeightedAveragePrice(high=high, low=low, close=close, volume=vol, window=14).volume_weighted_average_price()) if vol is not None else None
                add_item(0.9, "VWAP", "Volume", fmt(vwap_v), "BUY" if (last_close or 0) > (vwap_v if vwap_v is not None else (last_close or 0)) else "SELL", "Close > VWAP is BUY")
                if vol is not None:
                    vwma_v = safe_last((close * vol).rolling(20).sum() / vol.rolling(20).sum().replace(0, np.nan))
                else:
                    vwma_v = s20_v
                add_item(0.8, "VWMA", "Volume", fmt(vwma_v), "BUY" if (last_close or 0) > (vwma_v or 0) else "SELL", "Close > VWMA20 is BUY")
                willr_v = safe_last(WilliamsRIndicator(high=high, low=low, close=close, lbp=14).williams_r())
                add_item(0.8, "Williams %R", "Momentum", fmt(willr_v), "BUY" if (willr_v or -50) < -80 else ("SELL" if (willr_v or -50) > -20 else "HOLD"), "<-80 BUY, >-20 SELL")
                jaw_v = safe_last(calc_smma(hl2, 13).shift(8))
                teeth_v = safe_last(calc_smma(hl2, 8).shift(5))
                lips_v = safe_last(calc_smma(hl2, 5).shift(3))
                add_item(0.8, "Williams Alligator", "Trend", f"L:{fmt(lips_v)} T:{fmt(teeth_v)} J:{fmt(jaw_v)}", "BUY" if (lips_v or 0) > (teeth_v or 0) and (teeth_v or 0) > (jaw_v or 0) else "SELL", "Lips>Teeth>Jaw BUY")
                bull_frac = (high.shift(2) < high.shift(1)) & (high.shift(3) < high.shift(1)) & (high.shift(0) < high.shift(1))
                bear_frac = (low.shift(2) > low.shift(1)) & (low.shift(3) > low.shift(1)) & (low.shift(0) > low.shift(1))
                frac_state = "Bullish Fractal" if bool(bull_frac.iloc[-1]) else ("Bearish Fractal" if bool(bear_frac.iloc[-1]) else "No New Fractal")
                add_item(0.5, "Williams Fractal", "Pattern", frac_state, "BUY" if frac_state == "Bullish Fractal" else ("SELL" if frac_state == "Bearish Fractal" else "HOLD"), "Latest fractal direction")
                zz_diff = close.diff().abs()
                zz_sig = "BUY" if (safe_last(zz_diff) or 0) > 0 and (last_close or 0) > (prev_close or 0) else ("SELL" if (safe_last(zz_diff) or 0) > 0 and (last_close or 0) < (prev_close or 0) else "HOLD")
                add_item(0.5, "Zig Zag", "Pattern", f"Swing Δ {fmt(safe_last(zz_diff))}", zz_sig, "Swing leg direction")

                # Overall weighted score & indication
                weighted_sum = 0.0
                total_weight = 0.0
                for w, _, _, _, sig, _ in scored_items:
                    if w > 0:
                        total_weight += w
                        if sig == "BUY":
                            weighted_sum += w
                        elif sig == "SELL":
                            weighted_sum -= w
                    if sig == "BUY":
                        buy_count += 1
                    elif sig == "SELL":
                        sell_count += 1
                    else:
                        hold_count += 1

                avg_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
                score = f"{avg_score:+.2f}"
                if avg_score >= 0.20:
                    verdict = "BUY"
                    verdict_class = "buy"
                elif avg_score <= -0.20:
                    verdict = "SELL"
                    verdict_class = "sell"
                else:
                    verdict = "HOLD"
                    verdict_class = "hold"

                rows = [(name, cat, val_str, sig, basis) for _, name, cat, val_str, sig, basis in scored_items]
                total_rows = len(rows)

                labels = [idx.strftime("%Y-%m-%d") for idx in df.index]
                chart_json = json.dumps({
                    "labels": labels,
                    "close": clean_series_for_chart(close),
                    "sma20": clean_series_for_chart(sma20_s),
                    "ema20": clean_series_for_chart(ema20_s),
                    "supertrend": clean_series_for_chart(st_s),
                    "bb_high": clean_series_for_chart(bb_high_s),
                    "bb_low": clean_series_for_chart(bb_low_s),
                    "rsi": clean_series_for_chart(rsi_s),
                })

        except Exception as exc:
            error = f"Error analyzing '{ticker}': {exc}"

    return render_template_string(
        HTML,
        ticker=ticker,
        period=period,
        rows=rows,
        total_rows=total_rows,
        price=price,
        error=error,
        verdict=verdict,
        verdict_class=verdict_class,
        score=score,
        buy_count=buy_count,
        sell_count=sell_count,
        hold_count=hold_count,
        chart_json=chart_json,
    )


@app.route("/icon.svg")
def icon_svg():
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
      <rect width="512" height="512" rx="96" fill="#0f172a"/>
      <path d="M96 352 L192 240 L272 296 L416 144" fill="none" stroke="#38bdf8" stroke-width="36" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="416" cy="144" r="24" fill="#4ade80"/>
    </svg>'''
    return app.response_class(response=svg, mimetype="image/svg+xml")

@app.route("/manifest.json")
def manifest():
    return app.response_class(
        response=json.dumps({
            "name": "TinyCapitalCapital StockPulse Pro",
            "short_name": "StockPulse Pro",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0f172a",
            "theme_color": "#2563eb",
            "icons": [
                {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}
            ]
        }),
        mimetype="application/json"
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
