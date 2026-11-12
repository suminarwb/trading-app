"""
FastAPI server untuk aplikasi analisis trading.

Jalankan dengan:
    uvicorn app:app --reload --port 8000

Lalu buka frontend/index.html di browser (atau akses docs interaktif di
http://localhost:8000/docs).
"""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import DEFAULT_WATCHLIST, DEFAULT_INTERVAL, INTERVAL_PERIOD_MAP, DEFAULT_RISK_PERCENT, IDX_LOT_SIZE
from data_fetcher import get_ohlcv, DataFetchError
from strategy import generate_recommendation, calculate_position_size, calculate_position_size_from_quantity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

_WATCHLIST_MARKET_BY_SYMBOL = {item["symbol"].upper(): item["market"] for item in DEFAULT_WATCHLIST}


def _infer_market(symbol: str) -> str:
    """Menentukan jenis market dari simbol, dipakai untuk aturan position sizing (mis. lot IDX)."""
    upper = symbol.upper()
    if upper in _WATCHLIST_MARKET_BY_SYMBOL:
        return _WATCHLIST_MARKET_BY_SYMBOL[upper]
    if upper.endswith(".JK"):
        return "idx"
    if upper.endswith("-USD") or upper.endswith("-USDT"):
        return "crypto"
    if upper.endswith("=X"):
        return "forex"
    return "other"

app = FastAPI(
    title="Trading Analysis API",
    description="Analisis teknikal otomatis: sinyal buy/sell, cut loss, take profit.",
    version="1.0.0",
)

# CORS dibuka untuk localhost supaya frontend statis bisa memanggil API ini.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/watchlist")
def watchlist():
    """Mengembalikan daftar simbol default yang dikonfigurasi di config.py."""
    return {"watchlist": DEFAULT_WATCHLIST}


@app.get("/api/analyze")
def analyze(
    symbol: str = Query(..., description="Kode simbol gaya Yahoo Finance, mis. XAUUSD=X, BBCA.JK, BTC-USD"),
    interval: str = Query(DEFAULT_INTERVAL, description="15m, 30m, 1h, 1d, atau 1wk"),
    period: Optional[str] = Query(None, description="Rentang histori, mis. 6mo, 1y. Default mengikuti interval."),
    risk_reward: float = Query(2.0, gt=0, description="Rasio risk-reward untuk take profit, mis. 2.0 = 1:2"),
    capital: Optional[float] = Query(None, gt=0, description="Modal Anda; jika diisi, response menyertakan position sizing (quantity/lot, risk amount, nilai posisi)."),
    risk_percent: float = Query(DEFAULT_RISK_PERCENT, gt=0, le=100, description="Persentase modal yang dipertaruhkan per trade, mis. 1.0 = 1%. Diabaikan jika `quantity` diisi."),
    quantity: Optional[float] = Query(None, gt=0, description="Mode alternatif: jumlah lot (IDX) atau unit (market lain) yang sudah Anda tentukan sendiri. Jika diisi bersama `capital`, risk_percent diabaikan dan sistem menghitung risk yang dihasilkan sebagai gantinya."),
):
    """Analisis teknikal lengkap untuk satu simbol -> sinyal + entry/SL/TP (+ position sizing jika `capital` diisi)."""
    try:
        df = get_ohlcv(symbol, interval=interval, period=period)
        rec = generate_recommendation(symbol, df, risk_reward_ratio=risk_reward)
    except DataFetchError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error analyzing %s", symbol)
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan internal: {exc}") from exc

    # Sertakan sedikit histori harga untuk keperluan chart di frontend
    tail = df.tail(120).reset_index()
    date_col = tail.columns[0]
    candles = [
        {
            "time": row[date_col].strftime("%Y-%m-%d %H:%M"),
            "open": round(float(row["Open"]), 6),
            "high": round(float(row["High"]), 6),
            "low": round(float(row["Low"]), 6),
            "close": round(float(row["Close"]), 6),
        }
        for _, row in tail.iterrows()
    ]

    position_sizing = None
    if capital is not None:
        market = _infer_market(symbol)
        if quantity is not None:
            base_quantity = quantity * IDX_LOT_SIZE if market == "idx" else quantity
            position_sizing = calculate_position_size_from_quantity(rec, capital, base_quantity, market=market)
        else:
            position_sizing = calculate_position_size(rec, capital, risk_percent, market=market)

    return {"recommendation": rec.to_dict(), "candles": candles, "position_sizing": position_sizing}


@app.get("/api/watchlist/analyze")
def analyze_watchlist(risk_reward: float = Query(2.0, gt=0)):
    """Analisis singkat untuk semua simbol di watchlist sekaligus (untuk dashboard)."""
    results = []
    for item in DEFAULT_WATCHLIST:
        symbol = item["symbol"]
        try:
            df = get_ohlcv(symbol, interval=DEFAULT_INTERVAL, period=INTERVAL_PERIOD_MAP[DEFAULT_INTERVAL])
            rec = generate_recommendation(symbol, df, risk_reward_ratio=risk_reward)
            results.append({**item, "recommendation": rec.to_dict()})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gagal menganalisis %s: %s", symbol, exc)
            results.append({**item, "error": str(exc)})

    return {"results": results}


# Menyajikan frontend statis (opsional) langsung dari FastAPI di path "/"
# sehingga cukup jalankan satu server untuk backend + tampilan web.
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
