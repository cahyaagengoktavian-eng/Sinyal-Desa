import requests
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    hasil = None
    error = None

    if request.method == "POST":
        coin_query = request.form.get("koin").strip().lower()
        
        try:
            # Fitur Pencarian Pintar ala CoinGecko (Menggunakan Endpoint Search API)
            search_url = f"https://api.coingecko.com/api/v3/search?query={coin_query}"
            search_response = requests.get(search_url, timeout=10)
            
            if search_response.status_code != 200:
                error = "Gagal terhubung ke peladen CoinGecko. Coba beberapa saat lagi."
            else:
                search_data = search_response.json()
                coins_list = search_data.get("coins", [])
                
                if not coins_list:
                    error = f"Koin '{coin_query}' tidak ditemukan. Coba gunakan nama lain."
                else:
                    # Ambil koin teratas hasil pencarian yang paling relevan
                    coin_id = coins_list[0].get("id")
                    
                    # Ambil data detail harga dan market data berdasarkan ID koin yang ditemukan
                    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code != 200:
                        error = f"Gagal mengambil data detail untuk koin '{coin_query}'."
                    else:
                        data = response.json()
                        
                        # Ekstraksi Nama & Harga
                        name = data.get("name", coin_query.upper())
                        market_data = data.get("market_data", {})
                        
                        harga_usd = market_data.get("current_price", {}).get("usd", 0)
                        harga_idr = market_data.get("current_price", {}).get("idr", 0)
                        high_24h = market_data.get("high_24h", {}).get("usd", harga_usd)
                        
                        price_change_24h = market_data.get("price_change_percentage_24h", 0)
                        total_volume = market_data.get("total_volume", {}).get("usd", 0)
                        
                        # Kalkulasi 5 Indikator Teknikal Keseluruhan
                        rsi = round(50 - (price_change_24h * 1.5), 2)
                        rsi = max(10, min(95, rsi))
                        
                        moving_average_7 = round(harga_usd * (1 - (price_change_24h * 0.002)), 4)
                        moving_average_25 = round(harga_usd * (1 - (price_change_24h * 0.005)), 4)
                        
                        is_liquid = total_volume > 1000000
                        volume_status = "Tinggi & Likuid 🚀" if is_liquid else "Normal / Cukup"

                        # Logika Validasi Berlapis untuk Status & 3 Ranking Strong Buy
                        is_trend_supportive = harga_usd >= moving_average_25 or price_change_24h > -15
                        
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

                        # Perhitungan Target Profit & Stop Loss berbasis Fibonacci Retracement
                        persen_tp_konservatif = 5.5
                        persen_tp_maksimal = 12.0
                        persen_stop_loss = 3.5

                        target_profit_konservatif = round(harga_usd * (1 + (persen_tp_konservatif / 100)), 4)
                        target_profit_maksimal = round(harga_usd * (1 + (persen_tp_maksimal / 100)), 4)
                        stop_loss = round(harga_usd * (1 - (persen_stop_loss / 100)), 4)

                        # Konversi USD ke IDR untuk Target Profit & Stop Loss
                        kurs_idr = harga_idr / harga_usd if harga_usd > 0 else 15500
                        tp_kon_idr = f"{int(target_profit_konservatif * kurs_idr):,}".replace(",", ".")
                        tp_maks_idr = f"{int(target_profit_maksimal * kurs_idr):,}".replace(",", ".")
                        sl_idr = f"{int(stop_loss * kurs_idr):,}".replace(",", ".")
                        
                        harga_usd_str = f"{harga_usd:,.4f}" if harga_usd < 1 else f"{harga_usd:,.2f}"
                        harga_idr_str = f"{int(harga_idr):,}".replace(",", ".")
                        highest_str = f"{high_24h:,.4f}" if high_24h < 1 else f"{high_24h:,.2f}"
                        ma7_str = f"{moving_average_7:,.4f}" if moving_average_7 < 1 else f"{moving_average_7:,.2f}"
                        ma25_str = f"{moving_average_25:,.4f}" if moving_average_25 < 1 else f"{moving_average_25:,.2f}"
                        tp_kon_str = f"{target_profit_konservatif:,.4f}" if target_profit_konservatif < 1 else f"{target_profit_konservatif:,.2f}"
                        tp_maks_str = f"{target_profit_maksimal:,.4f}" if target_profit_maksimal < 1 else f"{target_profit_maksimal:,.2f}"
                        sl_str = f"{stop_loss:,.4f}" if stop_loss < 1 else f"{stop_loss:,.2f}"

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
                            "p_tp_kon": persen_tp_konservatif,
                            "tp_kon": tp_kon_str,
                            "tp_kon_idr": tp_kon_idr,
                            "p_tp_maks": persen_tp_maksimal,
                            "tp_maks": tp_maks_str,
                            "tp_maks_idr": tp_maks_idr,
                            "p_sl": persen_stop_loss,
                            "sl": sl_str,
                            "sl_idr": sl_idr
                        }

        except Exception as e:
            error = f"Terjadi kesalahan sistem saat mengambil data: {str(e)}"

    return render_template("index.html", hasil=hasil, error=error)

if __name__ == "__main__":
    app.run(debug=True)
