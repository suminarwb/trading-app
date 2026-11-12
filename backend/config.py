"""
Konfigurasi aplikasi analisis trading.
Ubah nilai di bawah sesuai kebutuhan Anda tanpa perlu menyentuh kode logic.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# SUMBER DATA TAMBAHAN (di luar Yahoo Finance)
# Yahoo Finance sudah tidak lagi menyediakan XAUUSD=X, jadi simbol tersebut
# diambil dari Twelve Data (https://twelvedata.com/pricing - gratis, 800
# request/hari). Daftar dulu untuk mendapatkan API key, lalu isi di file
# `.env` (lihat `.env.example`):
#   TWELVE_DATA_API_KEY=xxxxxxxx
# ---------------------------------------------------------------------------
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

# Simbol yang dipetakan ke Twelve Data alih-alih Yahoo Finance.
# key = simbol gaya Yahoo yang dipakai di seluruh aplikasi/watchlist/URL
# value = simbol versi Twelve Data
TWELVE_DATA_SYMBOLS = {
    "XAUUSD=X": "XAU/USD",
}

# ---------------------------------------------------------------------------
# WATCHLIST DEFAULT
# Format simbol mengikuti konvensi Yahoo Finance:
#   Saham IDX   -> "BBCA.JK", "TLKM.JK", dst (tambahkan suffix .JK)
#   Forex       -> "EURUSD=X", "USDJPY=X"
#   Emas        -> "XAUUSD=X" (spot, via Twelve Data - lihat TWELVE_DATA_SYMBOLS di atas)
#   Crypto      -> "BTC-USD", "ETH-USD"
#   Indeks      -> "^JKSE" (IHSG), "^GSPC" (S&P 500)
# ---------------------------------------------------------------------------
DEFAULT_WATCHLIST = [
    {"symbol": "XAUUSD=X", "label": "Gold Spot (XAU/USD)", "market": "forex"},
    {"symbol": "BTC-USD", "label": "Bitcoin", "market": "crypto"},
    {"symbol": "EURUSD=X", "label": "EUR/USD", "market": "forex"},
    {"symbol": "BBCA.JK", "label": "Bank BCA", "market": "idx"},
]

# ---------------------------------------------------------------------------
# PARAMETER TIMEFRAME
# interval didukung yfinance: 15m, 30m, 1h, 1d, 1wk
# period = rentang histori yang diambil untuk menghitung indikator
# ---------------------------------------------------------------------------
DEFAULT_INTERVAL = "1d"
DEFAULT_PERIOD = "6mo"

INTERVAL_PERIOD_MAP = {
    "15m": "5d",
    "30m": "1mo",
    "1h": "3mo",
    "1d": "6mo",
    "1wk": "2y",
}

# ---------------------------------------------------------------------------
# PARAMETER INDIKATOR
# ---------------------------------------------------------------------------
EMA_FAST = 20
EMA_SLOW = 50
RSI_PERIOD = 14
ATR_PERIOD = 14

RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# ---------------------------------------------------------------------------
# PARAMETER MANAJEMEN RISIKO
# ATR_SL_MULTIPLIER   : jarak cut loss = ATR * multiplier ini
# RISK_REWARD_RATIO   : take profit = jarak risiko (entry-SL) * rasio ini
# DEFAULT_RISK_PERCENT: persentase modal yang dipertaruhkan per trade (dipakai
#                       untuk hitung position sizing jika user tidak menentukan)
# IDX_LOT_SIZE        : saham IDX hanya bisa dibeli per kelipatan lot ini (1 lot = 100 lembar)
# ---------------------------------------------------------------------------
ATR_SL_MULTIPLIER = 1.5
RISK_REWARD_RATIO = 2.0
DEFAULT_RISK_PERCENT = 1.0
IDX_LOT_SIZE = 100

# Cache sederhana agar tidak membanjiri Yahoo Finance dengan request berulang
CACHE_TTL_SECONDS = 60
