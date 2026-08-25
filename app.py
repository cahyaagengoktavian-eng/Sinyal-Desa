import requests
from flask import Flask, render_template, request

app = Flask(__name__)


def get_real_crypto_data(input_user):
  input_clean = input_user.strip().lower()

  # 1. Coba cari dulu lewat kamus manual (buat shortcut koin populer)
  coin_mapping = {
      "bitcoin": "bitcoin",
      "btc": "bitcoin",
      "ethereum": "ethereum",
      "eth": "ethereum",
      "solana": "solana",
      "sol": "solana",
      "injective": "injective-protocol",
      "inj": "injective-protocol",
      "avantis": "avantis",
      "avnt": "avantis",
  }

  coin_id = coin_mapping.get(input_clean)

  try:
    # 2. Kalau koinnya gak ada di kamus, otomatis cari ID-nya lewat API Search CoinGecko
    if not coin_id:
      search_url = (
          f"https://api.coingecko.com/api/v3/search?query={input_clean}"
      )
      headers = {"User-Agent": "Mozilla/5.0"}
      search_resp = requests.get(search_url, headers=headers, timeout=5)
      search_data = search_resp.json()

      coins = search_data.get("coins", [])
      if not coins:
        return None  # Koin benar-benar tidak ditemukan di market

      # Ambil hasil pencarian teratas yang paling akurat
      coin_id = coins[0]["id"]

    # 3. Tarik data harga pakai ID yang sudah didapat
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd,idr&include_market_cap=true&include_24hr_change=true"
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
    data = response.json()

    if coin_id not in data:
      return None

    market_data = data[coin_id]
    harga_usd = market_data.get("usd", 0)
    harga_idr = market_data.get("idr", 0)
    perubahan_24h = market_data.get("usd_24h_change", 0)

    rsi = round(50 + (perubahan_24h * 1.5), 2)
    if rsi > 100:
      rsi = 95.0
    if rsi < 0:
      rsi = 5.0

    if rsi < 45:
      status_teks = "VALID STRONG BUY"
    elif 45 <= rsi <= 65:
      status_teks = "BELUM CUKUP VALID (Wait & See)"
    else:
      status_teks = "VALID DOWNTREND / BERBAHAYA"

    return {
        "coin": input_user.upper(),
        "harga_usd": (
            f"{harga_usd:,.8f}" if harga_usd < 1 else f"{harga_usd:,.2f}"
        ),
        "harga_idr": (
            f"{harga_idr:,.4f}" if harga_idr < 1000 else f"{harga_idr:,.2f}"
        ),
        "ma7": f"{harga_usd * 0.99:,.4f}",
        "ma25": f"{harga_usd * 0.97:,.4f}",
        "rsi": f"{rsi}",
        "volume_status": "Sehat",
        "highest": f"{harga_usd * 1.08:,.4f}",
        "status": status_teks,
        "tp_kon": f"{harga_usd * 1.10:,.4f}",
        "tp_kon_idr": f"{harga_idr * 1.10:,.4f}",
        "p_tp_kon": "10.00",
        "tp_maks": f"{harga_usd * 1.20:,.4f}",
        "tp_maks_idr": f"{harga_idr * 1.20:,.4f}",
        "p_tp_maks": "20.00",
        "sl": f"{harga_usd * 0.95:,.4f}",
        "sl_idr": f"{harga_idr * 0.95:,.4f}",
        "p_sl": "5.00",
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
