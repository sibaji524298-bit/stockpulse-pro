import json
import numpy as np
import pandas as pd


_RULES_CACHE = {}


def load_rules(path="indicators_rules.json"):
    if path not in _RULES_CACHE:
        with open(path, "r", encoding="utf-8") as f:
            _RULES_CACHE[path] = json.load(f)
    return _RULES_CACHE[path]


def _sign_score(strong_bull, bull, bear, strong_bear):
    if strong_bull:
        return 2
    if bull:
        return 1
    if strong_bear:
        return -2
    if bear:
        return -1
    return 0


def evaluate_stock_indicators(df: pd.DataFrame, bench_df: pd.DataFrame | None = None, rules_path="indicators_rules.json"):
    rules = load_rules(rules_path)
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    vol = df["Volume"].astype(float)

    c = float(close.iloc[-1])
    c_prev = float(close.iloc[-2]) if len(close) > 1 else c

    # 1. Trend (0.30) - Guardrail: cap correlated MA variants into one sub-group
    ma_votes = []
    for length, kind in [(20, "sma"), (50, "sma"), (200, "sma"), (20, "ema"), (50, "ema"), (20, "wma")]:
        if len(close) >= length + 2:
            if kind == "sma":
                s = close.rolling(length).mean()
            elif kind == "ema":
                s = close.ewm(span=length, adjust=False).mean()
            else:
                w = np.arange(1, length + 1)
                s = close.rolling(length).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)
            rising = s.iloc[-1] > s.iloc[-2]
            falling = s.iloc[-1] < s.iloc[-2]
            ma_votes.append(1 if (c > s.iloc[-1] and rising) else (-1 if (c < s.iloc[-1] and falling) else 0))

    if len(close) >= 200:
        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
        ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1])
        if c > ema20 > ema50 > ema200:
            ma_subgroup = 2.0
        elif c < ema20 < ema50 < ema200:
            ma_subgroup = -2.0
        else:
            ma_subgroup = float(np.clip(np.mean(ma_votes) * 2 if ma_votes else 0.0, -2, 2))
    else:
        ma_subgroup = float(np.clip(np.mean(ma_votes) * 2 if ma_votes else 0.0, -2, 2))

    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr14 = tr.ewm(alpha=1 / 14, adjust=False).mean()
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1 / 14, adjust=False).mean() / atr14.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1 / 14, adjust=False).mean() / atr14.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1 / 14, adjust=False).mean()
    adx_val = float(adx.iloc[-1]) if not np.isnan(adx.iloc[-1]) else 0.0

    adx_score = _sign_score(
        plus_di.iloc[-1] > minus_di.iloc[-1] and adx_val > 25,
        plus_di.iloc[-1] > minus_di.iloc[-1] and adx_val >= 20,
        minus_di.iloc[-1] > plus_di.iloc[-1] and adx_val >= 20,
        minus_di.iloc[-1] > plus_di.iloc[-1] and adx_val > 25,
    )

    aroon_len = min(25, max(5, len(close) - 1))
    aroon_up = 100 * high.rolling(aroon_len + 1).apply(lambda x: np.argmax(x) / aroon_len, raw=True)
    aroon_dn = 100 * low.rolling(aroon_len + 1).apply(lambda x: np.argmin(x) / aroon_len, raw=True)
    aroon_score = _sign_score(
        aroon_up.iloc[-1] > 70 and aroon_dn.iloc[-1] < 30,
        aroon_up.iloc[-1] > 70 and aroon_up.iloc[-1] > aroon_dn.iloc[-1],
        aroon_dn.iloc[-1] > 70 and aroon_dn.iloc[-1] > aroon_up.iloc[-1],
        aroon_dn.iloc[-1] > 70 and aroon_up.iloc[-1] < 30,
    )

    trend_score = float(np.mean([ma_subgroup, adx_score, aroon_score]))

    # 2. Momentum (0.20) - Guardrail: avoid treating every oscillator as independent vote
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi_val = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0
    rsi_prev = float(rsi.iloc[-2]) if len(rsi) > 1 and not np.isnan(rsi.iloc[-2]) else rsi_val
    rsi_score = _sign_score(
        rsi_val > 60 or (rsi_prev < 30 and rsi_val >= 30),
        rsi_val > 50,
        rsi_val < 50,
        rsi_val < 40 or (rsi_prev > 70 and rsi_val <= 70),
    )

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_sig = macd_line.ewm(span=9, adjust=False).mean()
    macd_score = _sign_score(
        macd_line.iloc[-1] > macd_sig.iloc[-1] and macd_line.iloc[-1] > 0,
        macd_line.iloc[-1] > macd_sig.iloc[-1],
        macd_line.iloc[-1] < macd_sig.iloc[-1],
        macd_line.iloc[-1] < macd_sig.iloc[-1] and macd_line.iloc[-1] < 0,
    )

    roc12 = ((close - close.shift(12)) / close.shift(12).replace(0, np.nan)) * 100
    roc_val = float(roc12.iloc[-1]) if len(close) > 12 and not np.isnan(roc12.iloc[-1]) else 0.0
    roc_score = 1 if roc_val > 0 else (-1 if roc_val < 0 else 0)

    momentum_score = float(np.mean([float(np.mean([rsi_score, roc_score])), macd_score]))

    # 3. Volume and Money Flow (0.20) - Guardrail: price direction accompanies volume
    obv = (np.sign(close.diff()).fillna(0) * vol).cumsum()
    obv_rising = bool(obv.iloc[-1] > obv.iloc[-5]) if len(obv) >= 5 else bool(obv.iloc[-1] >= obv.iloc[0])
    mfm = ((close - low) - (high - close)) / (high - low).replace(0, np.nan)
    cmf = (mfm * vol).rolling(20).sum() / vol.rolling(20).sum().replace(0, np.nan)
    cmf_val = float(cmf.iloc[-1]) if not np.isnan(cmf.iloc[-1]) else 0.0
    vol_ma20 = vol.rolling(20).mean().iloc[-1]
    vol_ratio = float(vol.iloc[-1] / vol_ma20) if vol_ma20 and not np.isnan(vol_ma20) else 1.0
    price_up = c > c_prev
    price_dn = c < c_prev

    volume_score = _sign_score(
        price_up and vol_ratio > 1.5 and cmf_val > 0.05 and obv_rising,
        (price_up and obv_rising) or cmf_val > 0.05,
        (price_dn and not obv_rising) or cmf_val < -0.05,
        price_dn and vol_ratio > 1.5 and cmf_val < -0.05 and not obv_rising,
    )

    # 4. Volatility and Regime (0.10) - Guardrail: risk/regime neutral when non-directional
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_up = bb_mid + 2 * bb_std
    bb_dn = bb_mid - 2 * bb_std
    volatility_score = _sign_score(
        c > bb_up.iloc[-1] and vol_ratio > 1.5,
        c > bb_mid.iloc[-1] and len(close) > 1 and close.iloc[-2] <= bb_dn.iloc[-2],
        False,
        c < bb_dn.iloc[-1] and vol_ratio > 1.5,
    )

    # 5. Relative Strength and Breadth (0.10)
    if bench_df is not None and len(bench_df) >= 20:
        aligned = pd.concat([close.rename("s"), bench_df["Close"].astype(float).rename("b")], axis=1).dropna()
        if len(aligned) >= 20:
            ratio = aligned["s"] / aligned["b"].replace(0, np.nan)
            ratio_ma20 = ratio.rolling(20).mean()
            rs_score = 1 if ratio.iloc[-1] > ratio_ma20.iloc[-1] else (-1 if ratio.iloc[-1] < ratio_ma20.iloc[-1] else 0)
        else:
            rs_score = 0
    else:
        rs_score = 0

    # 6. Structure and Levels (0.10)
    donchian_hi = high.shift(1).rolling(20).max().iloc[-1]
    donchian_lo = low.shift(1).rolling(20).min().iloc[-1]
    pp = (high.iloc[-2] + low.iloc[-2] + close.iloc[-2]) / 3.0 if len(close) > 1 else c
    structure_score = _sign_score(
        c > donchian_hi,
        c > pp,
        c < pp,
        c < donchian_lo,
    )

    family_scores = {
        "Trend": round(trend_score, 2),
        "Momentum": round(momentum_score, 2),
        "Volume and Money Flow": round(volume_score, 2),
        "Volatility and Regime": round(volatility_score, 2),
        "Relative Strength and Breadth": round(rs_score, 2),
        "Structure and Levels": round(structure_score, 2),
    }

    weights = {f["family"]: f["weight"] for f in rules["families"]}
    composite = sum(family_scores[k] * weights.get(k, 0.0) for k in family_scores)
    composite = round(float(np.clip(composite, -2.0, 2.0)), 2)

    if composite >= 1.25:
        verdict = "Strong Bullish"
    elif composite >= 0.35:
        verdict = "Bullish"
    elif composite <= -1.25:
        verdict = "Strong Bearish"
    elif composite <= -0.35:
        verdict = "Bearish"
    else:
        verdict = "Neutral / Non-directional"

    return {
        "composite_score": composite,
        "verdict": verdict,
        "family_scores": family_scores,
        "weights": weights,
        "metrics": {
            "rsi14": round(rsi_val, 2),
            "adx14": round(adx_val, 2),
            "cmf20": round(cmf_val, 3),
            "vol_ratio": round(vol_ratio, 2),
            "atr14": round(float(atr14.iloc[-1]), 2),
        },
        "catalog": rules["indicators"],
        "guardrails": rules["families"],
    }
