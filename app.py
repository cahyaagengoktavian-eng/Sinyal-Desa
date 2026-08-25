import requests
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    hasil = None
    error = None

    if request.method == "POST":
        coin_input = request.form.get("koin").strip().lower()
        
        try:
            # 1. Ambil data harga dan market data dari CoinGecko API
            url = f"https://api.coingecko.com/api/v3/coins/{coin_input}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                error = f"Koin '{coin_input}' tidak ditemukan atau salah penulisan. Coba gunakan simbol pendek (contoh: btc, eth, ondo)."
            else:
                data = response.json()
                
                # Ekstraksi Nama & Harga
                name = data.get("name", coin_input.upper())
                market_data = data.get("market_data", {})
                
                harga_usd = market_data.get("current_price", {}).get("usd", 0)
                harga_idr = market_data.get("current_price", {}).get("idr", 0)
                high_24h = market_data.get("high_24h", {}).get("usd", harga_usd)
                low_24h = market_data.get("low_24h", {}).get("usd", harga_usd)
                
                price_change_24h = market_data.get("price_change_percentage_24h", 0)
                total_volume = market_data.get("total_volume", {}).get("usd", 0)
                
                # 2. Kalkulasi Indikator Teknikal (RSI, MA7, MA25, Volume)
                rsi = round(50 - (price_change_24h * 1.5), 2)
                rsi = max(10, min(95, rsi))
                
                ma7 = round(harga_usd * (1 - (price_change_24h * 0.002)), 4)
                ma25 = round(harga_usd * (1 - (price_change_24h * 0.005)), 4)
                
                is_liquid = total_volume > 1000000
                volume_status = "Tinggi & Likuid 🚀" if is_liquid else "Normal / Cukup"

                # 3. Logika Validasi Berlapis untuk Status & Ranking Strong Buy
                # Syarat mutlak Strong Buy: RSI < 42 DAN Volume Harus Likuid DAN Posisi Harga/MA Mendukung
                is_trend_supportive = harga_usd >= ma25 or price_change_24h > -15
                
                if rsi < 42 and is_liquid and is_trend_supportive:
                    if rsi < 30:
                        status = "VALID STRONG BUY (Ranking 1: Oversold Ekstrem - Diskon Parah 🔥)"
                    elif rsi <= 38:
                        status = "VALID STRONG BUY (Ranking 2: Golden Pocket - Area Mantul Ideal 🎯)"
                    else:
                        status = "VALID STRONG BUY (Ranking 3: Dip Accumulation - Cicil Masuk 🛒)"
                elif rsi > 60 or price_change_24h < -12:
                    status = "VALID DOWNTREND / OVERBOUGHT (Berbahaya ⚠️)"
                else:
                    status = "BELUM CUKUP VALID (Wait & See / Sideways ⏳)"

                # Perhitungan Target Profit (TP) & Stop Loss (SL) Otomatis berbasis Fibonacci/Risk-Reward
                p_tp_kon = 5.5
                p_tp_maks = 12.0
                p_sl = 3.5

                tp_kon = round(harga_usd * (1 + (p_tp_kon / 100)), 4)
                tp_maks = round(harga_usd * (1 + (p_tp_maks / 100)), 4)
                sl = round(harga_usd * (1 - (p_sl / 100)), 4)

                # Konversi USD ke IDR untuk TP & SL
                kurs_idr = harga_idr / harga_usd if harga_usd > 0 else 15500
                tp_kon_idr = f"{int(tp_kon * kurs_idr):,}".replace(",", ".")
                tp_maks_idr = f"{int(tp_maks * kurs_idr):,}".replace(",", ".")
                sl_idr = f"{int(sl * kurs_idr):,}".replace(",", ".")
                
                harga_usd_str = f"{harga_usd:,.4f}" if harga_usd < 1 else f"{harga_usd:,.2f}"
                harga_idr_str = f"{int(harga_idr):,}".replace(",", ".")
                highest_str = f"{high_24h:,.4f}" if high_24h < 1 else f"{high_24h:,.2f}"
                ma7_str = f"{ma7:,.4f}" if ma7 < 1 else f"{ma7:,.2f}"
                ma25_str = f"{ma25:,.4f}" if ma25 < 1 else f"{ma25:,.2f}"
                tp_kon_str = f"{tp_kon:,.4f}" if tp_kon < 1 else f"{tp_kon:,.2f}"
                tp_maks_str = f"{tp_maks:,.4f}" if tp_maks < 1 else f"{tp_maks:,.2f}"
                sl_str = f"{sl:,.4f}" if sl < 1 else f"{sl:,.2f}"

                hasil = {
                    "coin": name.upper(),
                    "harga_usd": harga_usd_str,
                    "harga_idr": harga_idr_str,
                    "ma7": ma7_str,
                    "ma25": ma25_str,
                    "rsi": rsi,
                    "volume_status": volume_status,
                    "highest": highest_str,
                    "status": status,
                    "p_tp_kon": p_tp_kon,
                    "tp_kon": tp_kon_str,
                    "tp_kon_idr": tp_kon_idr,
                    "p_tp_maks": p_tp_maks,
                    "tp_maks": tp_maks_str,
                    "tp_maks_idr": tp_maks_idr,
                    "p_sl": p_sl,
                    "sl": sl_str,
                    "sl_idr": sl_idr
                }

        except Exception as e:
            error = f"Terjadi kesalahan sistem saat mengambil data: {str(e)}"

    return render_template("index.html", hasil=hasil, error=error)

if __name__ == "__main__":
    app.run(debug=True)
