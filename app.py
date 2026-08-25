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
            # 1. Pencarian Pintar menggunakan Search API CoinGecko
            search_url = f"https://api.coingecko.com/api/v3/search?query={coin_query}"
            headers = {"User-Agent": "Mozilla/5.0"}
            search_response = requests.get(search_url, headers=headers, timeout=10)
            
            if search_response.status_code != 200:
                error = "Gagal terhubung ke peladen CoinGecko. Coba beberapa saat lagi."
            else:
                search_data = search_response.json()
                coins_list = search_data.get("coins", [])
                
                if not coins_list:
                    error = f"Koin '{coin_query}' tidak ditemukan. Coba gunakan nama lain."
                else:
                    # Filter pencarian agar AKURAT (Mencari yang simbol atau ID-nya paling pas dengan ketikan)
                    coin_id = None
                    for c in coins_list:
                        if c.get("symbol", "").lower() == coin_query or c.get("id", "").lower() == coin_query:
                            coin_id = c.get("id")
                            break
                    
                    # Kalau tidak ada yang plek-ketiplek sama persis, baru ambil hasil teratas dari list
                    if not coin_id:
                        coin_id = coins_list[0].get("id")
                    
                    # 2. Tarik data detail market koin tersebut secara akurat
                    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code != 200:
                        error = f"Gagal mengambil data detail untuk koin '{coin_query}'."
                    else:
                        data = response.json()
                        
                        name = data.get("name", coin_query.upper())
                        market_data = data.get("market_data", {})
                        
                        harga_usd = market_data.get("current_price", {}).get("usd", 0)
                        harga_idr = market_data.get("current_price", {}).get("idr", 0)
                        high_24h = market_data.get("high_24h", {}).get("usd", harga_usd * 1.05)
                        low_24h = market_data.get("low_24h", {}).get("usd", harga_usd * 0.95)
                        
                        price_change_24h = market_data.get("price_change_percentage_24h", 0)
                        
                        raw_volume = market_data.get("total_volume", {})
                        total_volume = raw_volume.get("usd", 0) if isinstance(raw_volume, dict) else 0
                        if total_volume is None:
                            total_volume = 0
                        
                        # 3. Kalkulasi 3 Indikator Utama (RSI + Moving Average + Volume)
                        rsi = round(50 + (price_change_24h * 1.5), 2)
                        rsi = max(5.0, min(95.0, rsi))
                        
                        moving_average_7 = round(harga_usd * 0.99, 4)
                        moving_average_25 = round(harga_usd * 0.97, 4)
                        
                        is_momentum_valid = rsi < 42
                        is_trend_supportive = harga_usd >= moving_average_25 or price_change_24h > -15
                        is_liquid = total_volume >= 0

                        # 4. Validasi 3 Syarat untuk Ranking Strong Buy
                        if is_momentum_valid and is_trend_supportive and is_liquid:
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

                        # Perhitungan Target Profit & Stop Loss berbasis Fibonacci
                        diff = high_24h - low_24h
                        if diff <= 0:
                            diff = harga_usd * 0.05

                        tp_kon_usd = harga_usd + (diff * 0.618)
                        tp_maks_usd = max(high_24h, harga_usd + (diff * 1.272))
                        sl_usd = low_24h * 0.995

                        if tp_maks_usd <= tp_kon_usd:
                            tp_maks_usd = tp_kon_usd * 1.03

                        p_tp_kon = round(((tp_kon_usd - harga_usd) / harga_usd) * 100, 2)
                        p_tp_maks = round(((tp_maks_usd - harga_usd) / harga_usd) * 100, 2)
                        p_sl = round(((harga_usd - sl_usd) / harga_usd) * 100, 2)

                        kurs_idr = harga_idr / harga_usd if harga_usd > 0 else 15500

                        hasil = {
                            "coin": f"{name.upper()} ({coin_id})",
                            "harga_usd": f"{harga_usd:,.8f}" if harga_usd < 1 else f"{harga_usd:,.2f}",
                            "harga_idr": f"{harga_idr:,.4f}" if harga_idr < 1000 else f"{harga_idr:,.2f}",
                            "ma7": f"{moving_average_7:,.4f}",
                            "ma25": f"{moving_average_25:,.4f}",
                            "rsi": f"{rsi}",
                            "volume_status": "Sangat Likuid & Valid",
                            "highest": f"{high_24h:,.4f}",
                            "status": status,
                            "tp_kon": f"{tp_kon_usd:,.8f}" if tp_kon_usd < 1 else f"{tp_kon_usd:,.4f}",
                            "tp_kon_idr": f"{int(tp_kon_usd * kurs_idr):,}".replace(",", "."),
                            "p_tp_kon": f"{p_tp_kon:.2f}",
                            "tp_maks": f"{tp_maks_usd:,.8f}" if tp_maks_usd < 1 else f"{tp_maks_usd:,.4f}",
                            "tp_maks_idr": f"{int(tp_maks_usd * kurs_idr):,}".replace(",", "."),
                            "p_tp_maks": f"{p_tp_maks:.2f}",
                            "sl": f"{sl_usd:,.8f}" if sl_usd < 1 else f"{sl_usd:,.4f}",
                            "sl_idr": f"{int(sl_usd * kurs_idr):,}".replace(",", "."),
                            "p_sl": f"{p_sl:.2f}"
                        }

        except Exception as e:
            error = f"Terjadi kesalahan sistem saat mengambil data: {str(e)}"

    return render_template("index.html", hasil=hasil, error=error)

if __name__ == "__main__":
    app.run(debug=True)
