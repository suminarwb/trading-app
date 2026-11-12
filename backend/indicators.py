"""
Perhitungan indikator teknikal murni dengan pandas/numpy (tanpa dependensi
eksternal seperti TA-Lib supaya mudah di-install di sistem apa pun).
"""

import pandas as pd
import numpy as np

from config import EMA_FAST, EMA_SLOW, RSI_PERIOD, ATR_PERIOD


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val.fillna(50)  # netral saat data awal belum cukup


def atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)

    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)

    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def pivot_points(df: pd.DataFrame) -> dict:
    """
    Pivot point klasik dihitung dari candle terakhir yang SUDAH closed
    (H, L, C hari/periode sebelumnya). Menghasilkan level support &
    resistance yang umum dipakai untuk menentukan entry/TP/SL.
    """
    last = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
    high, low, close = float(last["High"]), float(last["Low"]), float(last["Close"])

    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)

    return {"pivot": pivot, "r1": r1, "r2": r2, "s1": s1, "s2": s2}


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Menambahkan kolom-kolom indikator ke DataFrame OHLCV dan mengembalikannya."""
    out = df.copy()
    out["ema_fast"] = ema(out["Close"], EMA_FAST)
    out["ema_slow"] = ema(out["Close"], EMA_SLOW)
    out["rsi"] = rsi(out["Close"], RSI_PERIOD)
    out["atr"] = atr(out, ATR_PERIOD)
    return out
