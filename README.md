# Trading Analysis App

Aplikasi analisis teknikal otomatis untuk multi-market (saham IDX, forex,
emas/XAUUSD, crypto) yang menghasilkan rekomendasi **harga buy, cut loss,
dan take profit** berdasarkan indikator EMA, RSI, ATR, dan pivot point.

Sumber data: **Yahoo Finance** (via `yfinance`) — gratis, tanpa API key,
mencakup hampir semua jenis instrumen dalam satu sumber.

---

## ⚠️ Disclaimer

Aplikasi ini menghasilkan sinyal dari **analisis teknikal otomatis**
berdasarkan data historis. Ini **bukan nasihat keuangan personal**. Harga
pasar bisa bergerak berlawanan arah kapan saja karena faktor fundamental,
berita, atau sentimen yang tidak tertangkap oleh indikator teknikal.
Selalu terapkan manajemen risiko dan position sizing sesuai toleransi
risiko Anda sendiri. Gunakan dengan tanggung jawab sendiri.

---

## Struktur Project

```
trading-app/
├── backend/
│   ├── app.py              # Server FastAPI (endpoint API)
│   ├── config.py           # Watchlist, parameter indikator & risiko
│   ├── data_fetcher.py     # Ambil data harga dari Yahoo Finance
│   ├── indicators.py       # EMA, RSI, ATR, pivot point
│   ├── strategy.py         # Logika sinyal & perhitungan entry/SL/TP
│   └── requirements.txt
└── frontend/
    └── index.html          # Dashboard web (watchlist + chart)
```

## Instalasi & Menjalankan

1. **Install Python 3.10+** jika belum ada.

2. Buat virtual environment (opsional tapi disarankan):
   ```bash
   cd trading-app/backend
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. Install dependensi:
   ```bash
   pip install -r requirements.txt
   ```

4. Jalankan server:
   ```bash
   uvicorn app:app --reload --port 8000
   ```

5. Buka browser ke **http://localhost:8000** — dashboard akan otomatis
   memuat watchlist default (Gold Spot XAUUSD, BTC-USD, EUR/USD, BBCA.JK).

   Dokumentasi API interaktif tersedia di **http://localhost:8000/docs**.

   > **Emas (XAUUSD=X)** diambil dari Twelve Data, bukan Yahoo Finance (Yahoo
   > sudah tidak menyediakan simbol ini). Daftar gratis di
   > [twelvedata.com/pricing](https://twelvedata.com/pricing), lalu salin
   > `backend/.env.example` menjadi `backend/.env` dan isi `TWELVE_DATA_API_KEY`.
   > Tanpa API key ini, simbol lain (forex, crypto, saham) tetap berfungsi
   > normal — hanya XAUUSD=X yang akan gagal.

## Mengubah Watchlist

Edit `backend/config.py`, bagian `DEFAULT_WATCHLIST`. Format simbol
mengikuti konvensi Yahoo Finance:

| Jenis Instrumen | Format Simbol       | Contoh        |
|---|---|---|
| Saham IDX        | `KODE.JK`           | `BBCA.JK`     |
| Forex            | `PASANGAN=X`        | `EURUSD=X`    |
| Emas (spot)      | `XAUUSD=X`          | `XAUUSD=X`    |
| Crypto           | `KODE-USD`          | `BTC-USD`     |
| Indeks           | `^KODE`             | `^JKSE`       |

Simbol emas (`XAUUSD=X`) diambil dari Twelve Data, bukan Yahoo Finance —
lihat `TWELVE_DATA_SYMBOLS` di `backend/config.py` jika ingin menambah
simbol lain yang juga perlu sumber data ini (mis. perak `XAG/USD`).

## Mengubah Parameter Strategi

Di `backend/config.py`:
- `EMA_FAST` / `EMA_SLOW` — periode EMA untuk deteksi trend
- `RSI_PERIOD`, `RSI_OVERBOUGHT`, `RSI_OVERSOLD` — ambang momentum
- `ATR_SL_MULTIPLIER` — seberapa jauh cut loss dari harga entry (dalam satuan ATR)
- `RISK_REWARD_RATIO` — rasio take profit terhadap risiko (mis. 2.0 = 1:2)

## Menambahkan Sumber Data Lain (opsional)

Jika suatu saat butuh data real-time yang lebih presisi (misalnya untuk
scalping crypto), tambahkan fetcher baru di `data_fetcher.py` yang
memanggil **Binance API** (`https://api.binance.com/api/v3/klines`,
gratis & tanpa API key untuk data publik) lalu arahkan `strategy.py`
untuk memakainya sesuai `market` pada watchlist.

## Batasan yang Perlu Diketahui

- Data Yahoo Finance untuk forex/emas kadang punya jeda (delay) beberapa
  menit, bukan tick-by-tick real-time — cukup untuk swing/day trading,
  kurang ideal untuk scalping.
- Endpoint `yfinance` tidak resmi mem-wrap website Yahoo Finance, sehingga
  bisa saja berhenti bekerja jika Yahoo mengubah struktur situsnya. Jika
  itu terjadi, cek update `yfinance` versi terbaru atau ganti ke Twelve
  Data / Alpha Vantage (perlu API key gratis).
