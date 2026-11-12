"""
Mesin strategi: mengubah indikator teknikal menjadi rekomendasi konkret
(sinyal, harga entry/buy, cut loss, take profit) beserta alasan yang bisa
dibaca manusia.

PENTING - DISCLAIMER:
Output modul ini adalah hasil analisis teknikal otomatis berdasarkan
data historis (EMA, RSI, ATR, pivot point). Ini BUKAN nasihat keuangan
personal. Pasar bisa bergerak berlawanan dari sinyal kapan saja karena
faktor fundamental/berita yang tidak tertangkap indikator teknikal.
Selalu terapkan manajemen risiko (position sizing) sendiri.
"""

import math
from dataclasses import dataclass, asdict
from typing import Literal, Optional

import pandas as pd

from config import (
    RSI_OVERBOUGHT, RSI_OVERSOLD, ATR_SL_MULTIPLIER, RISK_REWARD_RATIO, IDX_LOT_SIZE,
)
from indicators import compute_all_indicators, pivot_points

Signal = Literal["BUY", "SELL", "HOLD"]


@dataclass
class Recommendation:
    symbol: str
    signal: Signal
    confidence: str          # "rendah" / "sedang" / "tinggi"
    last_price: float
    entry_price: float
    cut_loss: float
    take_profit: float
    risk_reward_ratio: float
    reasons: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _trend_direction(row) -> str:
    if row["ema_fast"] > row["ema_slow"]:
        return "up"
    if row["ema_fast"] < row["ema_slow"]:
        return "down"
    return "flat"


def generate_recommendation(symbol: str, df: pd.DataFrame,
                             risk_reward_ratio: float = RISK_REWARD_RATIO,
                             atr_multiplier: float = ATR_SL_MULTIPLIER) -> Recommendation:
    """
    Membangun rekomendasi trading dari DataFrame OHLCV mentah.
    DataFrame minimal butuh ~60 baris candle agar EMA50 valid.
    """
    if len(df) < 55:
        raise ValueError(
            "Data historis terlalu sedikit untuk analisis yang andal "
            "(minimal ~55 candle agar EMA50 & ATR valid)."
        )

    data = compute_all_indicators(df)
    last = data.iloc[-1]
    pivots = pivot_points(data)

    last_price = float(last["Close"])
    trend = _trend_direction(last)
    rsi_val = float(last["rsi"])
    atr_val = float(last["atr"])

    reasons: list[str] = []
    warnings: list[str] = []
    signal: Signal = "HOLD"
    confidence = "rendah"

    ema_gap_pct = abs(last["ema_fast"] - last["ema_slow"]) / last_price * 100

    if trend == "up" and rsi_val < RSI_OVERBOUGHT:
        signal = "BUY"
        reasons.append(
            f"Trend naik: EMA{20} berada di atas EMA{50} "
            f"(selisih {ema_gap_pct:.2f}% dari harga)."
        )
        reasons.append(f"RSI {rsi_val:.1f} belum overbought (<{RSI_OVERBOUGHT}), masih ada ruang naik.")
        confidence = "tinggi" if (rsi_val < 60 and ema_gap_pct > 0.3) else "sedang"

    elif trend == "down" and rsi_val > RSI_OVERSOLD:
        signal = "SELL"
        reasons.append(
            f"Trend turun: EMA{20} berada di bawah EMA{50} "
            f"(selisih {ema_gap_pct:.2f}% dari harga)."
        )
        reasons.append(f"RSI {rsi_val:.1f} belum oversold (>{RSI_OVERSOLD}), momentum turun masih berlanjut.")
        confidence = "tinggi" if (rsi_val > 40 and ema_gap_pct > 0.3) else "sedang"

    else:
        signal = "HOLD"
        reasons.append("Trend tidak jelas atau RSI berada di zona ekstrem (overbought/oversold).")
        reasons.append(f"EMA20 vs EMA50: {trend}. RSI: {rsi_val:.1f}.")

    if rsi_val >= RSI_OVERBOUGHT:
        warnings.append(f"RSI {rsi_val:.1f} menunjukkan kondisi overbought, risiko koreksi meningkat.")
    if rsi_val <= RSI_OVERSOLD:
        warnings.append(f"RSI {rsi_val:.1f} menunjukkan kondisi oversold, risiko rebound/short-squeeze.")

    # --- Entry, Cut Loss, Take Profit ---
    entry_price = last_price

    if signal == "BUY":
        sl_from_atr = entry_price - (atr_val * atr_multiplier)
        cut_loss = min(sl_from_atr, pivots["s1"]) if pivots["s1"] < entry_price else sl_from_atr
        risk = entry_price - cut_loss
        take_profit = entry_price + (risk * risk_reward_ratio)
        reasons.append(
            f"Cut loss ditempatkan di bawah level support pivot S1 ({pivots['s1']:.4f}) "
            f"atau {atr_multiplier}x ATR ({atr_val:.4f}) dari harga entry, mana yang lebih konservatif."
        )
        reasons.append(
            f"Take profit dihitung dari risk-reward ratio 1:{risk_reward_ratio:g} terhadap risiko entry-ke-SL."
        )

    elif signal == "SELL":
        sl_from_atr = entry_price + (atr_val * atr_multiplier)
        cut_loss = max(sl_from_atr, pivots["r1"]) if pivots["r1"] > entry_price else sl_from_atr
        risk = cut_loss - entry_price
        take_profit = entry_price - (risk * risk_reward_ratio)
        reasons.append(
            f"Cut loss (untuk posisi short) ditempatkan di atas level resistance pivot R1 "
            f"({pivots['r1']:.4f}) atau {atr_multiplier}x ATR dari harga entry, mana yang lebih konservatif."
        )
        reasons.append(
            f"Take profit dihitung dari risk-reward ratio 1:{risk_reward_ratio:g} terhadap risiko entry-ke-SL."
        )

    else:  # HOLD - tetap tampilkan level referensi netral berbasis ATR & pivot
        cut_loss = entry_price - (atr_val * atr_multiplier)
        take_profit = entry_price + (atr_val * atr_multiplier * risk_reward_ratio)
        warnings.append("Sinyal HOLD: level di bawah hanya referensi, bukan rekomendasi entry aktif.")

    warnings.append(
        "Ini adalah sinyal hasil analisis teknikal otomatis, bukan nasihat keuangan personal. "
        "Selalu sesuaikan ukuran posisi dengan toleransi risiko Anda sendiri."
    )

    return Recommendation(
        symbol=symbol,
        signal=signal,
        confidence=confidence,
        last_price=round(last_price, 6),
        entry_price=round(entry_price, 6),
        cut_loss=round(cut_loss, 6),
        take_profit=round(take_profit, 6),
        risk_reward_ratio=risk_reward_ratio,
        reasons=reasons,
        warnings=warnings,
    )


def calculate_position_size(rec: Recommendation, capital: float, risk_percent: float,
                             market: Optional[str] = None) -> dict:
    """
    Menghitung ukuran posisi (quantity/lot) berdasarkan modal dan persentase
    risiko per trade, memakai jarak entry -> cut loss dari rekomendasi.

    Saham IDX (market == "idx") dibulatkan ke bawah ke kelipatan lot
    (IDX_LOT_SIZE) dan dibatasi agar tidak melebihi modal yang tersedia,
    karena saham dibeli tunai (tanpa leverage). Market lain (forex, crypto,
    futures) diasumsikan bisa trading dengan leverage/margin, jadi quantity
    murni mengikuti target risiko dan hanya diberi peringatan bila nilai
    posisi melebihi modal.
    """
    warnings: list[str] = []

    if rec.signal == "HOLD":
        return {
            "capital": capital,
            "risk_percent": risk_percent,
            "quantity": 0,
            "risk_amount": 0.0,
            "position_value": 0.0,
            "position_value_pct_of_capital": 0.0,
            "warnings": ["Sinyal HOLD: tidak ada rekomendasi ukuran posisi aktif."],
        }

    risk_per_unit = abs(rec.entry_price - rec.cut_loss)
    if risk_per_unit <= 0:
        return {
            "capital": capital,
            "risk_percent": risk_percent,
            "quantity": 0,
            "risk_amount": 0.0,
            "position_value": 0.0,
            "position_value_pct_of_capital": 0.0,
            "warnings": ["Jarak entry ke cut loss nol, tidak bisa menghitung ukuran posisi."],
        }

    risk_budget = capital * (risk_percent / 100)
    quantity = risk_budget / risk_per_unit
    affordable_quantity = capital / rec.entry_price

    if market == "idx":
        quantity = min(quantity, affordable_quantity)
        quantity = math.floor(quantity / IDX_LOT_SIZE) * IDX_LOT_SIZE
        if quantity <= 0:
            warnings.append(
                f"Modal tidak cukup untuk membeli minimal 1 lot ({IDX_LOT_SIZE} lembar) "
                f"pada risk {risk_percent:g}% dari modal."
            )
    else:
        quantity = round(quantity, 6)
        if quantity <= 0:
            warnings.append("Modal atau risk% terlalu kecil untuk menghasilkan ukuran posisi.")

    position_value = quantity * rec.entry_price
    actual_risk_amount = quantity * risk_per_unit

    if position_value > capital:
        warnings.append(
            "Nilai posisi melebihi modal tunai Anda - baru bisa dieksekusi penuh jika "
            "instrumen/broker ini menyediakan leverage/margin."
        )

    return {
        "capital": round(capital, 2),
        "risk_percent": risk_percent,
        "quantity": quantity,
        "lot_size": IDX_LOT_SIZE if market == "idx" else None,
        "risk_amount": round(actual_risk_amount, 2),
        "position_value": round(position_value, 2),
        "position_value_pct_of_capital": round(position_value / capital * 100, 2) if capital else 0.0,
        "warnings": warnings,
    }


def calculate_position_size_from_quantity(rec: Recommendation, capital: float, quantity: float,
                                           market: Optional[str] = None) -> dict:
    """
    Kebalikan dari calculate_position_size(): user sudah menentukan sendiri
    jumlah lot/unit yang mau dibeli (`quantity`, dalam satuan dasar - lembar
    saham untuk IDX, bukan lot), lalu dihitung risk amount & risk% yang
    dihasilkan dari jarak entry -> cut loss milik rekomendasi.
    """
    if rec.signal == "HOLD":
        return {
            "capital": capital,
            "risk_percent": 0.0,
            "quantity": quantity,
            "lot_size": IDX_LOT_SIZE if market == "idx" else None,
            "risk_amount": 0.0,
            "position_value": 0.0,
            "position_value_pct_of_capital": 0.0,
            "warnings": ["Sinyal HOLD: tidak ada rekomendasi ukuran posisi aktif."],
        }

    risk_per_unit = abs(rec.entry_price - rec.cut_loss)
    position_value = quantity * rec.entry_price
    risk_amount = quantity * risk_per_unit
    risk_percent = (risk_amount / capital * 100) if capital else 0.0

    warnings: list[str] = []
    if position_value > capital:
        warnings.append(
            "Nilai posisi melebihi modal tunai Anda - baru bisa dieksekusi penuh jika "
            "instrumen/broker ini menyediakan leverage/margin."
        )

    return {
        "capital": round(capital, 2),
        "risk_percent": round(risk_percent, 2),
        "quantity": quantity,
        "lot_size": IDX_LOT_SIZE if market == "idx" else None,
        "risk_amount": round(risk_amount, 2),
        "position_value": round(position_value, 2),
        "position_value_pct_of_capital": round(position_value / capital * 100, 2) if capital else 0.0,
        "warnings": warnings,
    }
