"""
Mengambil data OHLCV (Open, High, Low, Close, Volume) dari Yahoo Finance
menggunakan library yfinance. Gratis, tanpa API key, mendukung saham,
forex, dan crypto. Simbol yang terdaftar di TWELVE_DATA_SYMBOLS (mis.
XAUUSD=X, yang sudah tidak ada di Yahoo Finance) diambil dari Twelve Data.
"""

import time
import logging
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

from config import (
    INTERVAL_PERIOD_MAP,
    DEFAULT_INTERVAL,
    CACHE_TTL_SECONDS,
    TWELVE_DATA_API_KEY,
    TWELVE_DATA_SYMBOLS,
)

logger = logging.getLogger("data_fetcher")

# Cache in-memory sederhana: {(symbol, interval): (timestamp, dataframe)}
_cache: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}

# interval gaya yfinance -> interval gaya Twelve Data
_TD_INTERVAL_MAP = {
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "1d": "1day",
    "1wk": "1week",
}

# jumlah candle historis yang diminta per interval (cukup untuk EMA50/RSI/ATR + buffer)
_TD_OUTPUTSIZE = {
    "15m": 500,
    "30m": 500,
    "1h": 500,
    "1d": 180,
    "1wk": 110,
}


class DataFetchError(Exception):
    """Dilempar saat data tidak berhasil diambil atau simbol tidak valid."""


def _fetch_from_twelvedata(symbol: str, td_symbol: str, interval: str) -> pd.DataFrame:
    if not TWELVE_DATA_API_KEY:
        raise DataFetchError(
            f"Simbol '{symbol}' diambil dari Twelve Data, tapi TWELVE_DATA_API_KEY belum diisi. "
            f"Daftar gratis di https://twelvedata.com/pricing lalu isi TWELVE_DATA_API_KEY di file .env."
        )

    td_interval = _TD_INTERVAL_MAP.get(interval, "1day")
    outputsize = _TD_OUTPUTSIZE.get(interval, 180)

    try:
        resp = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": td_symbol,
                "interval": td_interval,
                "outputsize": outputsize,
                "apikey": TWELVE_DATA_API_KEY,
            },
            timeout=15,
        )
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 - bungkus semua error jaringan/parsing
        raise DataFetchError(f"Gagal mengambil data '{symbol}' dari Twelve Data: {exc}") from exc

    if data.get("status") == "error" or "values" not in data:
        raise DataFetchError(
            f"Twelve Data menolak permintaan untuk '{symbol}': {data.get('message', data)}"
        )

    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    if "volume" in df.columns:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    else:
        df["volume"] = 0

    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    return df[["Open", "High", "Low", "Close", "Volume"]]


def get_ohlcv(symbol: str, interval: str = DEFAULT_INTERVAL,
              period: Optional[str] = None, use_cache: bool = True) -> pd.DataFrame:
    """
    Mengambil data historis harga untuk satu simbol.

    Args:
        symbol: kode instrumen gaya Yahoo Finance, mis. "XAUUSD=X", "BBCA.JK", "BTC-USD"
        interval: granularitas candle ("15m", "30m", "1h", "1d", "1wk")
        period: rentang histori (mis. "6mo"); jika None, dipilih otomatis dari interval
        use_cache: pakai cache in-memory untuk menghindari rate-limit

    Returns:
        DataFrame dengan kolom: Open, High, Low, Close, Volume (index = datetime)

    Raises:
        DataFetchError jika simbol tidak ditemukan atau data kosong.
    """
    period = period or INTERVAL_PERIOD_MAP.get(interval, "6mo")
    cache_key = (symbol.upper(), interval)

    if use_cache and cache_key in _cache:
        ts, df_cached = _cache[cache_key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            return df_cached.copy()

    td_symbol = TWELVE_DATA_SYMBOLS.get(symbol.upper())
    if td_symbol:
        df = _fetch_from_twelvedata(symbol, td_symbol, interval)
    else:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval, auto_adjust=True)
        except Exception as exc:  # noqa: BLE001 - kita bungkus semua error jaringan/parsing
            raise DataFetchError(f"Gagal mengambil data untuk '{symbol}': {exc}") from exc

        if df is None or df.empty:
            raise DataFetchError(
                f"Data untuk simbol '{symbol}' kosong. Periksa apakah kode simbol sudah benar "
                f"(contoh format: BBCA.JK untuk saham IDX, XAUUSD=X untuk emas, BTC-USD untuk crypto)."
            )
        df = df[["Open", "High", "Low", "Close", "Volume"]]

    df = df.dropna()
    if df.empty:
        raise DataFetchError(f"Data untuk simbol '{symbol}' kosong setelah dibersihkan.")

    _cache[cache_key] = (time.time(), df.copy())
    return df


def get_last_price(symbol: str) -> float:
    """Mengambil harga penutupan/terkini paling baru untuk sebuah simbol."""
    df = get_ohlcv(symbol, interval="1d", period="5d")
    return float(df["Close"].iloc[-1])
