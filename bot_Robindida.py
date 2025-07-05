# ✅ BOT CRIPTO MULTITAREA Y MEJORADO (VERSIÓN FINAL)
# Analiza el mercado cada hora, detecta nuevas monedas, envía señales con imagen y responde en Telegram

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
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

# ========================
# CONFIGURACIÓN GENERAL
# ========================
TOKEN = "7545625230:AAGxAtfVyPlI7gFWPf6Gd3N3JZKUX1LIVF0"
CHAT_ID = "7591626762"
TIMEFRAME = "1h"
INTERVALO_ANALISIS = 60 * 60  # 1 hora
LISTA_USDT_FILE = "pares_usdt.txt"
EXCEL_FILE = "registro_senales.xlsx"
SYMBOLS = ["ARPA/USDT", "SUI/USDT", "BTC/USDT"]

# ========================
# ENVIAR MENSAJE A TELEGRAM
# ========================
def enviar_mensaje(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": texto}
    try:
        requests.post(url, data=data)
        print(f"✅ Mensaje enviado: {texto}")
    except Exception as e:
        print("❌ Error enviando mensaje:", e)

# ========================
# ENVIAR IMAGEN A TELEGRAM
# ========================
def enviar_imagen(file_path):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        with open(file_path, 'rb') as img:
            files = {'photo': img}
            data = {"chat_id": CHAT_ID}
            requests.post(url, files=files, data=data)
            print(f"📷 Imagen enviada: {file_path}")
    except Exception as e:
        print("❌ Error enviando imagen:", e)

# ========================
# DETECTAR NUEVOS PARES USDT
# ========================
def detectar_nuevos_pares(exchange):
    nuevos = []
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

# ========================
# ANÁLISIS TÉCNICO Y SEÑALES
# ========================
def analizar_mercado(exchange, symbol):
    try:
        print(f"🔍 Analizando {symbol}...")
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
            señal = "📈 Compra (RSI bajo, cruce alcista, MACD positivo)"
        elif ultima["rsi"] > 70 and ultima["ma7"] < ultima["ma25"] and ultima["macd"] < 0:
            señal = "📉 Venta (RSI alto, cruce bajista, MACD negativo)"

        if señal:
            mensaje = f"🔔 Señal detectada en {symbol}\n{señal}\nPrecio: ${ultima['close']:.2f}"
            enviar_mensaje(mensaje)
            generar_imagen(df, symbol)
            enviar_imagen(f"{symbol.replace('/', '_')}.png")
            registrar_senal(symbol, ultima["close"], señal)
        else:
            print(f"⏸ Sin señal para {symbol}")

    except Exception as e:
        print(f"❌ Error al analizar {symbol}: {e}")

# ========================
# GENERAR IMAGEN DEL GRÁFICO
# ========================
def generar_imagen(df, symbol):
    df_plot = df[["open", "high", "low", "close", "volume"]].copy()
    mpf.plot(df_plot, type='candle', volume=True, style='charles',
             title=f"Gráfico {symbol}", savefig=f"{symbol.replace('/', '_')}.png")

# ========================
# REGISTRAR EN EXCEL
# ========================
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
    print(f"📊 Señal registrada para {symbol} en Excel")

# ========================
# RESPONDER MENSAJES EN TELEGRAM CON BOTONES
# ========================
def responder_info(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("ℹ️ ¿Qué hace este bot?", callback_data='info')],
        [InlineKeyboardButton("📊 Ver últimas señales", callback_data='ultimas')],
        [InlineKeyboardButton("🆘 Ayuda", callback_data='ayuda')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 Hola, soy tu bot cripto. ¿Qué quieres hacer?",
        reply_markup=reply_markup
    )

def manejar_botones(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == "info":
        texto = (
            "🚀 *¿Qué hace este bot?*\n"
            "• Analiza el mercado cada hora\n"
            "• Envía señales de compra/venta\n"
            "• Muestra gráficas e indicadores\n"
            "• Detecta nuevas monedas listadas\n"
            "• Responde por Telegram con gráficos\n"
            "• Registra señales en Excel\n"
            "✅ ¡Trabaja 24/7 para ti!"
        )
    elif query.data == "ultimas":
        if os.path.exists(EXCEL_FILE):
            df = pd.read_excel(EXCEL_FILE)
            ultimas = df.tail(5).to_string(index=False)
            texto = f"📊 Últimas señales:\n{ultimas}"
        else:
            texto = "📭 No hay señales registradas aún."
    elif query.data == "ayuda":
        texto = "🆘 *Ayuda rápida*\n• Usa /start para ver el menú\n• Presiona los botones para navegar\n• El bot trabaja solo, tú solo revisa."
    else:
        texto = "❓ No entendí esa opción."

    query.edit_message_text(text=texto, parse_mode="Markdown")

# ========================
# INICIAR TELEGRAM
# ========================
def iniciar_telegram_respuestas():
    print("📩 Bot escuchando mensajes de Telegram...")
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", responder_info))
    dispatcher.add_handler(CommandHandler("info", responder_info))
    dispatcher.add_handler(CallbackQueryHandler(manejar_botones))
    # dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), responder_info))
    updater.start_polling()

# ========================
# TAREA: ANÁLISIS CADA HORA
# ========================
def tarea_analisis():
    print("🕒 Tarea de análisis iniciada")
    exchange = ccxt.binance()
    while True:
        print("🔄 Ejecutando análisis completo")
        nuevos = detectar_nuevos_pares(exchange)
        for nuevo in nuevos:
            enviar_mensaje(f"🚨 NUEVO PAR LISTADO EN BINANCE: {nuevo}")
        for symbol in SYMBOLS:
            analizar_mercado(exchange, symbol)
        print(f"⏳ Esperando {INTERVALO_ANALISIS} segundos...")
        time.sleep(INTERVALO_ANALISIS)

# ========================
# INICIO MULTITAREA
# ========================
def main():
    print("✅ BOT CRIPTO INICIADO CORRECTAMENTE")
    hilo1 = threading.Thread(target=tarea_analisis)
    hilo2 = threading.Thread(target=iniciar_telegram_respuestas)
    hilo1.start()
    hilo2.start()
    hilo1.join()
    hilo2.join()

if __name__ == "__main__":
    main()
