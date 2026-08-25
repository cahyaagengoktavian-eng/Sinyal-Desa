import os
import requests
import pandas as pd
import numpy as np
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

requests.packages.urllib3.disable_warnings()

TOKEN_TELEGRAM = "8907737843:AAE6xmLoX7ONcLEqO07nSTP_nabe59GOPY0"

app = Flask(__name__)

# Inisialisasi bot
telegram_app = Application.builder().token(TOKEN_TELEGRAM).build()
is_initialized = False

async def initialize_bot():
    global is_initialized
    if not is_initialized:
        await telegram_app.initialize()
        is_initialized = True

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_idr_rate():
    try:
        res = requests.get("https://open.er-api.com/v6/latest/USD", timeout=3)
        if res.status_code == 200:
            return res.json()['rates']['IDR']
    except:
        pass
    return 16000.0

def analyze_crypto_data(input_user):
    simbol_binance = input_user.upper() + "USDT"
    df = None
    
    try:
        url_binance = f"https://api.binance.com/api/v3/klines?symbol={simbol_binance}&interval=1d&limit=60"
        res = requests.get(url_binance, verify=False, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if len(data) > 30:
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'asset_vol', 'trades', 'tb_base', 'tb_quote', 'ignore'
                ])
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
    except:
        pass

    if df is None or df.empty:
        try:
            url_cg = f"https://api.coingecko.com/api/v3/coins/{input_user}/market_chart?vs_currency=usd&days=60"
            res = requests.get(url_cg, verify=False, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if 'prices' in data and len(data['prices']) > 30:
                    df = pd.DataFrame(data['prices'], columns=['timestamp', 'close'])
                    df['volume'] = 0.0
                    df['high'] = df['close']
                    df['low'] = df['close']
        except:
            pass

    if df is None or df.empty:
        return None

    kurs_idr = get_idr_rate()

    df['MA7'] = df['close'].rolling(window=7).mean()
    df['MA25'] = df['close'].rolling(window=25).mean()
    df['RSI14'] = calculate_rsi(df['close'], period=14)
    df['Vol_MA5'] = df['volume'].rolling(window=5).mean()

    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    harga_usd = df['close'].iloc[-1]
    ma7_usd = df['MA7'].iloc[-1]
    ma25_usd = df['MA25'].iloc[-1]
    rsi = df['RSI14'].iloc[-1]
    macd = df['MACD'].iloc[-1]
    sig = df['Signal_Line'].iloc[-1]
    vol_sekarang = df['volume'].iloc[-1]
    vol_ma5 = df['Vol_MA5'].iloc[-1]

    highest_price = df['high'].max()
    lowest_price = df['low'].min()
    diff = highest_price - lowest_price
    fib_382 = highest_price - (diff * 0.382)
    fib_618 = highest_price - (diff * 0.618)

    tp_konservatif_target = min(fib_382, harga_usd * 1.12)
    if tp_konservatif_target <= harga_usd:
        tp_konservatif_target = harga_usd * 1.05
    persen_tp_konservatif = ((tp_konservatif_target - harga_usd) / harga_usd) * 100

    if highest_price > harga_usd:
        tp_maksimal_target = highest_price
    else:
        tp_maksimal_target = harga_usd * 1.25
    persen_tp_maksimal = ((tp_maksimal_target - harga_usd) / harga_usd) * 100

    support_terdekat = min(ma25_usd, fib_618)
    if support_terdekat >= harga_usd or support_terdekat == 0:
        sl_target = harga_usd * 0.965
    else:
        sl_target = support_terdekat * 0.99
    
    persen_sl = ((harga_usd - sl_target) / harga_usd) * 100

    harga_idr = harga_usd * kurs_idr
    tp_kon_idr = tp_konservatif_target * kurs_idr
    tp_maks_idr = tp_maksimal_target * kurs_idr
    sl_idr = sl_target * kurs_idr

    skor_validasi = 0
    if harga_usd > ma7_usd and ma7_usd > ma25_usd: skor_validasi += 2
    elif harga_usd > ma7_usd: skor_validasi += 1
    else: skor_validasi -= 2

    if rsi > 70: skor_validasi -= 3 
    elif 45 <= rsi <= 65: skor_validasi += 2 
    elif rsi < 30: skor_validasi += 1 

    if macd > sig: skor_validasi += 1
    else: skor_validasi -= 1

    if vol_sekarang > vol_ma5: skor_validasi += 1
    else: skor_validasi -= 1

    pesan = f"📊 *LAPORAN ANALISIS: {input_user.upper()}*\n"
    pesan += f"━━━━━━━━━━━━━━━━━━━━━━━\n"
    pesan += f"💵 Harga: `${harga_usd:,.8f}` (Rp{harga_idr:,.4f})\n"
    pesan += f"📈 MA7: `${ma7_usd:,.8f}` | MA25: `${ma25_usd:,.8f}`\n"
    pesan += f"📉 RSI: `{rsi:.2f}`\n"
    pesan += f"📦 Volume: `{'🟢 Sehat' if vol_sekarang > vol_ma5 else '🟡 Tipis'}`\n"
    pesan += f"🏔️ Jangkauan 60H: Tinggi `${highest_price:,.8f}`\n"
    pesan += f"━━━━━━━━━━━━━━━━━━━━━━━\n"

    if skor_validasi >= 4:
        pesan += f"🟢 *STATUS: VALID STRONG BUY*\n\n"
        pesan += f"🎯 *TP Konservatif* (+{persen_tp_konservatif:.2f}%):\n`${tp_konservatif_target:,.8f}` (Rp{tp_kon_idr:,.4f})\n\n"
        pesan += f"🚀 *TP Maksimal* (+{persen_tp_maksimal:.2f}%):\n`${tp_maksimal_target:,.8f}` (Rp{tp_maks_idr:,.4f})\n\n"
        pesan += f"🛡️ *Stop Loss* (-{persen_sl:.2f}%):\n`${sl_target:,.8f}` (Rp{sl_idr:,.4f})"
    elif 1 <= skor_validasi < 4:
        pesan += f"🟡 *STATUS: BELUM CUKUP VALID (Wait & See)*\n"
        pesan += f"_Indikator belum kompak. Tidak ada rekomendasi TP / SL._"
    else:
        pesan += f"🔴 *STATUS: VALID DOWNTREND / BERBAHAYA*\n"
        pesan += f"_Pasar sedang tertekan turun. Jauhi koin ini._"

    return pesan

async def start(update: Update, context):
    await update.message.reply_text(
        "Halo bos! 🤖\nKirimkan saja nama koin yang mau dianalisis (contoh: `bitcoin`, `ethereum`, `solana`), nanti bot bakal langsung kirim laporan lengkapnya ke sini!"
    )

async def handle_message(update: Update, context):
    koin = update.message.text.strip().lower()
    await update.message.reply_text(f"⏳ Sedang menganalisis struktur data untuk *{koin.upper()}*...", parse_mode='Markdown')
    
    hasil_analisis = analyze_crypto_data(koin)
    
    if hasil_analisis is None:
        await update.message.reply_text(f"❌ Maaf, data untuk koin *{koin.upper()}* tidak ditemukan. Coba cek penulisannya.", parse_mode='Markdown')
    else:
        await update.message.reply_text(hasil_analisis, parse_mode='Markdown')

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

@app.route('/', methods=['POST'])
def webhook():
    import asyncio
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, telegram_app.bot)
    
    async def process():
        await initialize_bot()
        await telegram_app.process_update(update)
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(process())
        else:
            asyncio.run(process())
    except RuntimeError:
        asyncio.run(process())
        
    return "OK", 200

@app.route('/', methods=['GET'])
def index():
    return "Bot Telegram Sinyal Desa is running on Vercel!", 200
