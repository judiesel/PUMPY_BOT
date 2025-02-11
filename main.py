import os
import requests
import time
import numpy as np
import hmac, hashlib, json, base64
from datetime import datetime
import threading
from flask import Flask, jsonify

# === CONFIGURATION GLOBALE ===
API_KEY = os.getenv("COINBASE_API_KEY")
API_SECRET = os.getenv("COINBASE_API_SECRET")
API_PASSPHRASE = os.getenv("COINBASE_API_PASSPHRASE")

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

# === API COINBASE PRO ===
BASE_URL = "https://api.pro.coinbase.com"

def get_market_price(pair):
    """Récupère le prix actuel du marché"""
    url = f"{BASE_URL}/products/{pair}/ticker"
    response = requests.get(url)
    if response.status_code == 200:
        return float(response.json()["price"])
    return None

def place_trade(pair, action, amount):
    """Passe un trade fictif ou réel"""
    if PAPER_TRADING:
        print(f"[PAPER] {action.upper()} {amount} de {pair} au prix actuel.")
    else:
        print(f"⚠️ Mode réel activé ! Trade exécuté : {action.upper()} {amount} {pair}")

# === ALGORITHME DE DÉTECTION DES CRYPTOS LES PLUS VOLATILES ===
def find_most_volatile_crypto():
    """Analyse plusieurs cryptos et choisit la plus volatile"""
    pairs = ["BTC-USDC", "ETH-USDC", "SOL-USDC", "ADA-USDC", "XRP-USDC"]
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

    best_pair = max(volatilities, key=volatilities.get)
    print(f"🚀 Crypto la plus volatile détectée : {best_pair}")
    return best_pair

# === OPTIMISATION AUTOMATIQUE DE LA STRATÉGIE ===
def optimize_strategy(profit_today):
    global TAKE_PROFIT_PERCENTAGE, STOP_LOSS_PERCENTAGE, TRADE_ALLOCATION

    if profit_today < 0.05:  # Si les gains sont trop faibles
        TAKE_PROFIT_PERCENTAGE += 0.5
        STOP_LOSS_PERCENTAGE -= 0.2
        TRADE_ALLOCATION += 0.02
        print("🔄 Augmentation de l'agressivité pour maximiser les gains !")
    elif profit_today > 0.10:  # Si les gains sont trop élevés
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

# === DASHBOARD WEB POUR SUIVRE LES GAINS ===
app = Flask(__name__)

@app.route('/status')
def get_status():
    return jsonify({
        "Crypto suivie": find_most_volatile_crypto(),
        "Prix actuel": get_market_price(find_most_volatile_crypto()),
        "Capital": CAPITAL
    })

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    run_pumpy()
