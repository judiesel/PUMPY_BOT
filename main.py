import os
import requests
import time
import numpy as np
import hmac, hashlib, json, base64
from datetime import datetime
import threading
from flask import Flask, jsonify

# === CONFIGURATION GLOBALE ===
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price"
COINBASE_API_KEY = os.getenv("COINBASE_API_KEY")
COINBASE_API_SECRET = os.getenv("COINBASE_API_SECRET")
COINBASE_API_PASSPHRASE = os.getenv("COINBASE_API_PASSPHRASE")

PAPER_TRADING = True  # Mode fictif activé
TRADE_ALLOCATION = 0.1  # % du capital alloué à chaque trade
DASHBOARD_REFRESH = 5  # Rafraîchir toutes les 5 secondes
THRESHOLD_VOLATILITY = 3.0  # Détection avancée des cryptos volatiles
HIGH_FREQUENCY_TRADING = True  # Scalping haute fréquence
CAPITAL = 10000  # Capital de départ fictif
STOP_LOSS_PERCENTAGE = 3  # Stop-loss dynamique
TAKE_PROFIT_PERCENTAGE = 5  # Take-profit optimisé

# === FRAIS COINBASE ===
MAKER_FEE = 0.002  # 0.20%
TAKER_FEE = 0.001  # 0.10%

# === OBTENIR LES PRIX DE BINANCE ===
def get_market_price(pair):
    """Récupère le prix actuel du marché depuis Binance"""
    binance_symbol = pair.replace("-", "").upper()  # Adapter format Binance (ex: "BTCUSDT" au lieu de "BTC-USDC")
    url = f"{BINANCE_API_URL}?symbol={binance_symbol}"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        if "price" in data:
            return float(data["price"])
        else:
            print(f"⚠️ API Binance indisponible, réponse : {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"🚨 Erreur de connexion à Binance : {e}")
        return None

# === DÉTECTION DE LA CRYPTO LA PLUS VOLATILE ===
def find_most_volatile_crypto():
    """Analyse plusieurs cryptos et choisit la plus volatile"""
    pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]  # Format Binance
    volatilities = {}

    for pair in pairs:
        prices = []
        for _ in range(3):  # Analyse sur 15 secondes (3 requêtes de 5s)
            price = get_market_price(pair)
            if price:
                prices.append(price)
            time.sleep(5)

        if len(prices) >= 2:
            volatility = max(prices) - min(prices)
            volatilities[pair] = volatility

    if not volatilities:
        print("❌ Aucune volatilité détectée, re-scan en cours...")
        return None

    best_pair = max(volatilities, key=volatilities.get)
    print(f"🚀 Crypto la plus volatile détectée : {best_pair}")
    return best_pair

# === PLACER UN TRADE SUR COINBASE ===
def place_trade(pair, action, amount):
    """Passe un trade sur Coinbase"""
    url = f"https://api.pro.coinbase.com/orders"
    timestamp = str(int(time.time()))
    message = timestamp + 'POST' + '/orders' + json.dumps({
        "side": action,
        "product_id": pair,
        "size": amount,
        "type": "market"
    })

    signature = hmac.new(
        base64.b64decode(COINBASE_API_SECRET),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()

    headers = {
        'CB-ACCESS-KEY': COINBASE_API_KEY,
        'CB-ACCESS-SIGN': base64.b64encode(signature).decode(),
        'CB-ACCESS-TIMESTAMP': timestamp,
        'CB-ACCESS-PASSPHRASE': COINBASE_API_PASSPHRASE,
        'Content-Type': 'application/json'
    }

    if PAPER_TRADING:
        print(f"[PAPER] {action.upper()} {amount} de {pair} au prix actuel.")
    else:
        response = requests.post(url, headers=headers, json={
            "side": action,
            "product_id": pair,
            "size": amount,
            "type": "market"
        })
        print(f"⚠️ Trade {action.upper()} exécuté sur Coinbase : {response.json()}")

# === OPTIMISATION AUTOMATIQUE ===
def optimize_strategy(profit_today):
    global TAKE_PROFIT_PERCENTAGE, STOP_LOSS_PERCENTAGE, TRADE_ALLOCATION

    if profit_today < 0.05:
        TAKE_PROFIT_PERCENTAGE += 0.5
        STOP_LOSS_PERCENTAGE -= 0.2
        TRADE_ALLOCATION += 0.02
        print("🔄 Augmentation de l'agressivité pour maximiser les gains !")
    elif profit_today > 0.10:
        TAKE_PROFIT_PERCENTAGE -= 0.5
        STOP_LOSS_PERCENTAGE += 0.2
        TRADE_ALLOCATION -= 0.02
        print("🔄 Sécurisation des gains, réduction des risques !")

# === LANCEMENT DU BOT ===
def run_pumpy():
    global CAPITAL
    print("🚀 PUMPY démarre en mode Paper Trading...")

    while True:
        best_pair = find_most_volatile_crypto()
        if best_pair is None:
            time.sleep(DASHBOARD_REFRESH)
            continue

        market_price = get_market_price(best_pair)
        if market_price:
            trade_size = CAPITAL * TRADE_ALLOCATION
            place_trade(best_pair, "buy", trade_size)
            time.sleep(5)
            place_trade(best_pair, "sell", trade_size * (1 + TAKE_PROFIT_PERCENTAGE / 100))
            profit_today = (trade_size * (TAKE_PROFIT_PERCENTAGE / 100)) - (trade_size * TAKER_FEE)
            CAPITAL += profit_today
            print(f"📈 Gain réalisé : {profit_today:.2f}$. Nouveau capital : {CAPITAL:.2f}$")

            optimize_strategy(profit_today)

        time.sleep(DASHBOARD_REFRESH)

# === DASHBOARD WEB ===
app = Flask(__name__)

@app.route('/status')
def get_status():
    return jsonify({
        "Crypto suivie": find_most_volatile_crypto() or "Aucune crypto détectée",
        "Prix actuel": get_market_price(find_most_volatile_crypto()) or "Non disponible",
        "Capital": CAPITAL
    })

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)

# === DÉMARRAGE SUR RAILWAY ===
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    run_pumpy()
