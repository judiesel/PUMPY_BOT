import os
import requests
import time
import numpy as np
import hmac, hashlib, json, base64
from datetime import datetime
import threading
from flask import Flask, jsonify

# === CONFIGURATION GLOBALE ===
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
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

# === DÉTECTION DES MEILLEURES CRYPTOS ===
def get_top_cryptos():
    """Récupère les 10 cryptos les plus capitalisées et retourne leurs IDs"""
    url = f"{COINGECKO_API_URL}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=10&page=1"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        if isinstance(data, list):  # Vérifie que `data` est bien une liste et non une erreur
            return {coin["symbol"].upper() + "USDT": coin["id"] for coin in data}
        else:
            print(f"⚠️ Réponse inattendue de CoinGecko : {data}")
            return {}
    except requests.exceptions.RequestException as e:
        print(f"🚨 Erreur de connexion à CoinGecko : {e}")
        return {}

# === OBTENIR LES PRIX DES MEILLEURES CRYPTOS ===
def get_market_price(pair, crypto_id):
    """Récupère le prix actuel d'une crypto depuis CoinGecko"""
    url = f"{COINGECKO_API_URL}/simple/price?ids={crypto_id}&vs_currencies=usd"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if crypto_id in data and "usd" in data[crypto_id]:
            return data[crypto_id]["usd"]
        else:
            print(f"⚠️ CoinGecko n'a pas retourné de prix pour {crypto_id}. Réponse reçue : {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"🚨 Erreur de connexion à CoinGecko : {e}")
        return None

# === DÉTECTION AUTOMATIQUE DE LA CRYPTO LA PLUS VOLATILE ===
def find_most_volatile_crypto():
    """Analyse plusieurs cryptos et choisit la plus volatile"""
    top_cryptos = get_top_cryptos()
    
    if not top_cryptos:
        print("❌ Impossible de récupérer les cryptos du moment, réessai en cours...")
        return None, None

    volatilities = {}

    for pair, crypto_id in top_cryptos.items():
        prices = []
        for _ in range(3):  # Analyse sur 15 secondes (3 requêtes de 5s)
            price = get_market_price(pair, crypto_id)
            if price:
                prices.append(price)
            time.sleep(5)

        if len(prices) >= 2:
            volatility = max(prices) - min(prices)
            volatilities[pair] = volatility

    if not volatilities:
        print("❌ Aucune volatilité détectée, re-scan en cours...")
        return None, None

    best_pair = max(volatilities, key=volatilities.get)
    print(f"🚀 Crypto la plus volatile détectée : {best_pair}")
    return best_pair, top_cryptos.get(best_pair, None)

# === PLACER UN TRADE SUR COINBASE ===
def place_trade(pair, action, amount):
    """Passe un trade sur Coinbase"""
    url = "https://api.pro.coinbase.com/orders"
    timestamp = str(int(time.time()))
    body = json.dumps({
        "side": action,
        "product_id": pair,
        "size": str(amount),
        "type": "market"
    })

    message = timestamp + "POST" + "/orders" + body

    signature = hmac.new(
        base64.b64decode(COINBASE_API_SECRET),
        message.encode("utf-8"),
        hashlib.sha256
    ).digest()

    headers = {
        "CB-ACCESS-KEY": COINBASE_API_KEY,
        "CB-ACCESS-SIGN": base64.b64encode(signature).decode(),
        "CB-ACCESS-TIMESTAMP": timestamp,
        "CB-ACCESS-PASSPHRASE": COINBASE_API_PASSPHRASE,
        "Content-Type": "application/json"
    }

    if PAPER_TRADING:
        print(f"[PAPER] {action.upper()} {amount} de {pair} au prix actuel.")
    else:
        response = requests.post(url, headers=headers, data=body)
        print(f"⚠️ Trade {action.upper()} exécuté sur Coinbase : {response.json()}")

# === DASHBOARD WEB ===
app = Flask(__name__)

@app.route('/status')
def get_status():
    best_pair, _ = find_most_volatile_crypto()
    return jsonify({
        "Crypto suivie": best_pair or "Aucune crypto détectée",
        "Capital": CAPITAL
    })

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)

# === LANCEMENT DU BOT ===
def run_pumpy():
    global CAPITAL
    print("🚀 PUMPY démarre en mode Paper Trading...")

    while True:
        best_pair, crypto_id = find_most_volatile_crypto()
        if best_pair is None:
            time.sleep(DASHBOARD_REFRESH)
            continue

        market_price = get_market_price(best_pair, crypto_id)
        if market_price:
            trade_size = CAPITAL * TRADE_ALLOCATION
            place_trade(best_pair, "buy", trade_size)
            time.sleep(5)
            place_trade(best_pair, "sell", trade_size * (1 + TAKE_PROFIT_PERCENTAGE / 100))
            profit_today = (trade_size * (TAKE_PROFIT_PERCENTAGE / 100)) - (trade_size * TAKER_FEE)
            CAPITAL += profit_today
            print(f"📈 Gain réalisé : {profit_today:.2f}$. Nouveau capital : {CAPITAL:.2f}$")

        time.sleep(DASHBOARD_REFRESH)

# === DÉMARRAGE SUR RAILWAY ===
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    run_pumpy()
