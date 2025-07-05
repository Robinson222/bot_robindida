# bot_robindida.py
import threading
import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
import ta
import requests
import time
import datetime
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters

TOKEN = "TU_TOKEN_AQUI"
CHAT_ID = "TU_CHAT_ID_AQUI"
TIMEFRAME = "1h"
INTERVALO_ANALISIS = 60 * 15
LISTA_USDT_FILE = "pares_usdt.txt"
EXCEL_FILE = "registro_senales.xlsx"
SYMBOLS = ["ARPA/USDT", "SUI/USDT", "BTC/USDT"]
exchange = ccxt.binance()

def enviar_mensaje(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": texto}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Error enviando mensaje:", e)

def enviar_imagen(file_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(file_path, 'rb') as img:
            files = {'photo': img}
            data = {"chat_id": CHAT_ID}
            requests.post(url, files=files, data=data)
    except Exception as e:
        print("Error enviando imagen:", e)

def detectar_nuevos_pares():
    todos = exchange.load_markets()
    pares_usdt = [s for s in todos if s.endswith("/USDT")]
    if not os.path.exists(LISTA_USDT_FILE):
        with open(LISTA_USDT_FILE, "w") as f:
            f.write("\n".join(pares_usdt))
        return []
    with open(LISTA_USDT_FILE, "r") as f:
        anteriores = f.read().splitlines()
    nuevos = list(set(pares_usdt) - set(anteriores))
    if nuevos:
        with open(LISTA_USDT_FILE, "w") as f:
            f.write("\n".join(pares_usdt))
    return nuevos

def analizar_mercado(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
        df["ma7"] = df["close"].rolling(window=7).mean()
        df["ma25"] = df["close"].rolling(window=25).mean()
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd_diff()
        ultima = df.iloc[-1]
        señal = None
        if ultima["rsi"] < 30 and ultima["ma7"] > ultima["ma25"] and ultima["macd"] > 0:
            señal = "Compra"
        elif ultima["rsi"] > 70 and ultima["ma7"] < ultima["ma25"] and ultima["macd"] < 0:
            señal = "Venta"
        if señal:
            enviar_mensaje(f"Señal en {symbol}: {señal} a ${ultima['close']:.2f}")
            generar_imagen(df, symbol)
            enviar_imagen(f"{symbol.replace('/', '_')}.png")
            registrar_senal(symbol, ultima["close"], señal)
    except Exception as e:
        print(f"Error en {symbol}:", e)

def generar_imagen(df, symbol):
    df_plot = df[["open", "high", "low", "close", "volume"]].copy()
    mpf.plot(df_plot, type='candle', volume=True, style='charles',
             title=f"{symbol}", savefig=f"{symbol.replace('/', '_')}.png")

def registrar_senal(symbol, precio, señal):
    ahora = datetime.datetime.now()
    data = {"fecha": [ahora], "par": [symbol], "precio": [precio], "señal": [señal]}
    nuevo = pd.DataFrame(data)
    if os.path.exists(EXCEL_FILE):
        existente = pd.read_excel(EXCEL_FILE)
        df = pd.concat([existente, nuevo], ignore_index=True)
    else:
        df = nuevo
    df.to_excel(EXCEL_FILE, index=False)

def iniciar_telegram():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", lambda u, c: enviar_mensaje("Bot activo")))
    updater.start_polling()

def ciclo_analisis():
    while True:
        nuevos = detectar_nuevos_pares()
        for n in nuevos:
            enviar_mensaje(f"NUEVO PAR: {n}")
        for s in SYMBOLS:
            analizar_mercado(s)
        time.sleep(INTERVALO_ANALISIS)

def main():
    threading.Thread(target=iniciar_telegram).start()
    threading.Thread(target=ciclo_analisis).start()

if __name__ == "__main__":
    main()
