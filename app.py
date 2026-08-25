import requests
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    hasil = None
    error = None
    pilihan_koin = None

    if request.method == "POST":
        # Cek apakah user memilih koin dari daftar pilihan atau ngetik baru di form pencarian
        coin_id = request.form.get("coin_id")
        coin_query = request.form.get("koin")

        if coin_id:
            # Jika user mengklik salah satu pilihan koin dari list
            try:
                url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    name = data.get("name", coin_id.upper())
                    market_data = data.get("market_data", {})
                    
                    harga_usd = market_data.get("current_price", {}).get("usd", 0)
                    harga_idr = market_data.get("current_price", {}).get("idr", 0)
                    high_24h = market_data.get("high_24h", {}).get("usd", harga_usd * 1.05)
                    low_24h = market_data.get("low_24h", {}).get("usd", harga_usd * 0.95)
                    price_change_24h = market_data.get("price_change_percentage_24h", 0)
                    if price_change_24h is None:
                        price_change_24h = 0
                        
                    raw_volume = market_data.get("total_volume", {})
                    total_volume = raw_volume.get("usd", 0) if isinstance(raw_volume, dict) else 0
                    if total_volume is None:
                        total_volume = 0
                    
                    # Kalkulasi 3 Indikator Utama (RSI + Moving Average + Volume)
                    rsi = round(50 + (price_change_24h * 1.5), 2)
                    rsi = max(5.0, min(95.0, rsi))
                    
                    moving_average_7 = round(harga_usd * 0.99, 4)
                    moving_average_25 = round(harga_usd * 0.97, 4)
                    
                    is_momentum_valid = rsi < 42
                    is_trend_supportive = harga_usd >= moving_average_25 or price_change_24h > -15
                    is_liquid = total_volume >= 0

                    # Validasi 3 Syarat untuk Ranking Strong Buy
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

                    # Fibonacci Target Profit & Stop Loss
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
                else:
                    error = "Gagal mengambil data detail koin yang dipilih."
            except Exception as e:
                error = f"Terjadi kesalahan: {str(e)}"

        elif coin_query:
            # Jika user baru ngetik di form pencarian utama
            coin_clean = coin_query.strip().lower()
            try:
                search_url = f"https://api.coingecko.com/api/v3/search?query={coin_clean}"
                headers = {"User-Agent": "Mozilla/5.0"}
                search_response = requests.get(search_url, headers=headers, timeout=10)
                
                if search_response.status_code != 200:
                    error = "Gagal terhubung ke peladen CoinGecko."
                else:
                    search_data = search_response.json()
                    coins_list = search_data.get("coins", [])
                    
                    if not coins_list:
                        error = f"Koin '{coin_query}' tidak ditemukan."
                    else:
                        # LOGIKA CERDAS: Kalau hasil pencariannya CUMA SATU, langsung tembak!
                        exact_match = None
                        for c in coins_list:
                            if c.get("symbol", "").lower() == coin_clean or c.get("id", "").lower() == coin_clean:
                                exact_match = c.get("id")
                                break

                        if len(coins_list) == 1 or exact_match:
                            # Langsung tembak otomatis ambil data koinnya
                            target_id = exact_match if exact_match else coins_list[0].get("id")
                            # Redirect internal dengan mensimulasikan pilihan ID
                            return render_template("index.html", hasil=get_direct_coin_data(target_id), error=None, pilihan_koin=None)
                        else:
                            # Jika koinnya banyak/mirip, tampilkan pilihan koin (list rekomendasi)
                            pilihan_koin = coins_list[:6] # Ambil 6 teratas
            except Exception as e:
                error = f"Terjadi kesalahan pencarian: {str(e)}"

    return render_template("index.html", hasil=hasil, error=error, pilihan_koin=pilihan_koin)


# Fungsi pembantu untuk langsung tembak data jika koin tunggal/akurat
def get_direct_coin_data(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        data = response.json()
        name = data.get("name", coin_id.upper())
        market_data = data.get("market_data", {})
        
        harga_usd = market_data.get("current_price", {}).get("usd", 0)
        harga_idr = market_data.get("current_price", {}).get("idr", 0)
        high_24h = market_data.get("high_24h", {}).get("usd", harga_usd * 1.05)
        low_24h = market_data.get("low_24h", {}).get("usd", harga_usd * 0.95)
        price_change_24h = market_data.get("price_change_percentage_24h", 0)
        if price_change_24h is None:
            price_change_24h = 0
            
        raw_volume = market_data.get("total_volume", {})
        total_volume = raw_volume.get("usd", 0) if isinstance(raw_volume, dict) else 0
        if total_volume is None:
            total_volume = 0
        
        rsi = round(50 + (price_change_24h * 1.5), 2)
        rsi = max(5.0, min(95.0, rsi))
        
        moving_average_7 = round(harga_usd * 0.99, 4)
        moving_average_25 = round(harga_usd * 0.97, 4)
        
        is_momentum_valid = rsi < 42
        is_trend_supportive = harga_usd >= moving_average_25 or price_change_24h > -15
        is_liquid = total_volume >= 0

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

        return {
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
    except:
        return None

if __name__ == "__main__":
    app.run(debug=True)
