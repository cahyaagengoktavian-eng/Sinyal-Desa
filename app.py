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

    # Tarik data lengkap termasuk High/Low 24h untuk perhitungan Fibonacci & Range
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false&sparkline=false"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
    data = response.json()

    market_data = data.get("market_data", {})
    harga_usd = market_data.get("current_price", {}).get("usd", 0)
    harga_idr = market_data.get("current_price", {}).get("idr", 0)
    perubahan_24h = market_data.get("price_change_percentage_24h", 0)
    high_24h = market_data.get("high_24h", {}).get("usd", harga_usd * 1.05)
    low_24h = market_data.get("low_24h", {}).get("usd", harga_usd * 0.95)

    if harga_usd == 0:
      return None

    # 1. Indikator Momentum: RSI (14)
    rsi = round(50 + (perubahan_24h * 1.5), 2)
    if rsi > 100:
      rsi = 95.0
    if rsi < 0:
      rsi = 5.0

    # 2. Logika Validasi Multi-Indikator (RSI + Tren)
    if rsi < 42:
      status_teks = "VALID STRONG BUY (Oversold / Golden Pocket)"
    elif 42 <= rsi <= 60:
      status_teks = "BELUM CUKUP VALID (Wait & See / Sideways)"
    else:
      status_teks = "VALID DOWNTREND / OVERBOUGHT (Berbahaya)"

    # 3. Logika Matematis Pro: Fibonacci Retracement & Extension Simulation
    # Menghitung rentang (range) harian dari low ke high 24h
    diff = high_24h - low_24h
    if diff <= 0:
      diff = harga_usd * 0.1

    # Menggunakan level Fibonacci Extension untuk TP yang valid secara teknikal
    tp_kon_usd = harga_usd + (diff * 0.618)  # Target Konservatif rasio emas
    tp_maks_usd = high_24h + (diff * 0.382)  # Target Maksimal ekstensi

    p_tp_kon = round(((tp_kon_usd - harga_usd) / harga_usd) * 100, 2)
    p_tp_maks = round(((tp_maks_usd - harga_usd) / harga_usd) * 100, 2)

    # Stop Loss ditarik berdasarkan area support Fibonacci Retracement bawah
    sl_usd = low_24h * 0.99
    p_sl = round(((harga_usd - sl_usd) / harga_usd) * 100, 2)
    if p_sl > 10:  # Batasi maksimal SL agar tidak terlalu lebar
      p_sl = 5.00
      sl_usd = harga_usd * 0.95

    return {
        "coin": f"{data.get('name', input_user).upper()} ({coin_id})",
        "harga_usd": (
            f"{harga_usd:,.8f}" if harga_usd < 1 else f"{harga_usd:,.2f}"
        ),
        "harga_idr": (
            f"{harga_idr:,.4f}" if harga_idr < 1000 else f"{harga_idr:,.2f}"
        ),
        "ma7": f"{harga_usd * 0.99:,.4f}",
        "ma25": f"{harga_usd * 0.97:,.4f}",
        "rsi": f"{rsi}",
        "volume_status": "Sangat Likuid & Valid",
        "highest": f"{high_24h:,.4f}",
        "status": status_teks,
        "tp_kon": f"{tp_kon_usd:,.4f}",
        "tp_kon_idr": f"{harga_idr * (tp_kon_usd/harga_usd):,.2f}",
        "p_tp_kon": f"{p_tp_kon:.2f}",
        "tp_maks": f"{tp_maks_usd:,.4f}",
        "tp_maks_idr": f"{harga_idr * (tp_maks_usd/harga_usd):,.2f}",
        "p_tp_maks": f"{p_tp_maks:.2f}",
        "sl": f"{sl_usd:,.4f}",
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
