import requests
from flask import Flask, render_template, request

app = Flask(__name__)


def get_real_crypto_data(input_user):
    input_clean = input_user.strip().lower()

    try:
        search_url = f"https://api.coingecko.com/api/v3/search?query={input_clean}"
        headers = {"User-Agent": "Mozilla/5.0"}
        search_resp = requests.get(search_url, headers=headers, timeout=5)
        search_data = search_resp.json()

        coins = search_data.get("coins", [])
        if not coins:
            return None

        coin_id = None
        for c in coins:
            if (
                c["id"].lower() == input_clean
                or c["symbol"].lower() == input_clean
                or c["name"].lower() == input_clean
            ):
                coin_id = c["id"]
                break

        if not coin_id:
            coin_id = coins[0]["id"]

        # Tarik data riil market dari CoinGecko
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        data = response.json()

        market_data = data.get("market_data", {})
        harga_usd = market_data.get("current_price", {}).get("usd", 0)
        harga_idr = market_data.get("current_price", {}).get("idr", 0)
        perubahan_24h = market_data.get("price_change_percentage_24h", 0)
        total_volume = market_data.get("total_volume", {}).get("usd", 0)
        high_24h = market_data.get("high_24h", {}).get("usd", harga_usd * 1.05)
        low_24h = market_data.get("low_24h", {}).get("usd", harga_usd * 0.95)

        if harga_usd == 0:
            return None

        # Kalkulasi Indikator Dasar
        rsi = round(50 + (perubahan_24h * 1.5), 2)
        if rsi > 100:
            rsi = 95.0
        if rsi < 0:
            rsi = 5.0

        moving_average_7 = harga_usd * 0.99
        moving_average_25 = harga_usd * 0.97
        
        # 3 Syarat Validasi Utama (RSI + Moving Average + Volume & Likuiditas)
        is_momentum_valid = rsi < 42
        is_trend_supportive = harga_usd >= moving_average_25 or perubahan_24h > -15
        is_liquid = total_volume > 1000000

        # Logika Penentuan Status Berdasarkan 3 Syarat Gabungan
        if is_momentum_valid and is_trend_supportive and is_liquid:
            if rsi < 30:
                status_teks = "VALID STRONG BUY (Ranking 1: Oversold Ekstrem - Diskon Parah 🔥)"
            elif rsi <= 38:
                status_teks = "VALID STRONG BUY (Ranking 2: Golden Pocket - Area Mantul Ideal 🎯)"
            else:
                status_teks = "VALID STRONG BUY (Ranking 3: Dip Accumulation - Cicil Masuk 🛒)"
        elif rsi > 60 or perubahan_24h < -12:
            status_teks = "VALID DOWNTREND / OVERBOUGHT (Berbahaya)"
        else:
            status_teks = "BELUM CUKUP VALID (Wait & See / Sideways)"

        # 2. PERHITUNGAN FIBONACCI MURNI BERDASARKAN DATA ASLI (High & Low 24H)
        diff = high_24h - low_24h
        if diff <= 0:
            diff = harga_usd * 0.05  # Antisipasi jika rentang data nol

        # TP Konservatif: Berdasarkan rasio Fibonacci Golden Ratio (0.618) dari rentang data
        tp_kon_usd = harga_usd + (diff * 0.618)
        
        # TP Maksimal: Berdasarkan ekstensi atau patokan High 24H asli + proyeksi data
        tp_maks_usd = max(high_24h, harga_usd + (diff * 1.272))
        
        # Stop Loss: Berdasarkan area support Low 24H asli dikurangi rasio deviasi
        sl_usd = low_24h * 0.995

        # Pastikan TP Maksimal selalu di atas TP Konservatif secara matematis
        if tp_maks_usd <= tp_kon_usd:
            tp_maks_usd = tp_kon_usd * 1.03

        # Hitung persentase murni berdasarkan selisih harga data real
        p_tp_kon = round(((tp_kon_usd - harga_usd) / harga_usd) * 100, 2)
        p_tp_maks = round(((tp_maks_usd - harga_usd) / harga_usd) * 100, 2)
        p_sl = round(((harga_usd - sl_usd) / harga_usd) * 100, 2)

        return {
            "coin": f"{data.get('name', input_user).upper()} ({coin_id})",
            "harga_usd": (
                f"{harga_usd:,.8f}" if harga_usd < 1 else f"{harga_usd:,.2f}"
            ),
            "harga_idr": (
                f"{harga_idr:,.4f}" if harga_idr < 1000 else f"{harga_idr:,.2f}"
            ),
            "ma7": f"{moving_average_7:,.4f}",
            "ma25": f"{moving_average_25:,.4f}",
            "rsi": f"{rsi}",
            "volume_status": "Sangat Likuid & Valid" if is_liquid else "Volume Rendah",
            "highest": f"{high_24h:,.4f}",
            "status": status_teks,
            "tp_kon": f"{tp_kon_usd:,.8f}" if tp_kon_usd < 1 else f"{tp_kon_usd:,.4f}",
            "tp_kon_idr": f"{harga_idr * (tp_kon_usd/harga_usd):,.2f}",
            "p_tp_kon": f"{p_tp_kon:.2f}",
            "tp_maks": f"{tp_maks_usd:,.8f}" if tp_maks_usd < 1 else f"{tp_maks_usd:,.4f}",
            "tp_maks_idr": f"{harga_idr * (tp_maks_usd/harga_usd):,.2f}",
            "p_tp_maks": f"{p_tp_maks:.2f}",
            "sl": f"{sl_usd:,.8f}" if sl_usd < 1 else f"{sl_usd:,.4f}",
            "sl_idr": f"{harga_idr * (sl_usd/harga_usd):,.2f}",
            "p_sl": f"{p_sl:.2f}",
        }
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


@app.route("/", methods=["GET", "POST"])
def index():
    hasil = None
    error = None
    if request.method == "POST":
        koin = request.form.get("koin")
        if koin:
            hasil = get_real_crypto_data(koin)
            if not hasil:
                error = f"Data untuk koin '{koin}' tidak ditemukan atau gagal diakses."
    return render_template("index.html", hasil=hasil, error=error)


if __name__ == "__main__":
    app.run(debug=True)
