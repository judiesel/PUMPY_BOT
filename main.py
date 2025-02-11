import os
import requests
import time
import hmac, hashlib, json, base64
from datetime import datetime
import threading
from flask import Flask, jsonify

# === CONFIGURATION GLOBALE ===
KRAKEN_API_URL = "https://api.kraken.com/0"
KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")  # Récupère la clé API stockée en variable d'environnement
KRAKEN_API_SECRET = os.getenv("KRAKEN_API_SECRET")  # Récupère le secret API stocké en variable d'environnement

PAPER_TRADING = True  # Mode fictif activé
TRADE_ALLOCATION = 0.1  # % du capital alloué à chaque trade
DASHBOARD_REFRESH = 5  # Rafraîchir toutes les 5 secondes
HIGH_FREQUENCY_TRADING = True  # Scalping haute fréquence
CAPITAL = 10000  # Capital de départ fictif
STOP_LOSS_PERCENTAGE = 3  # Stop-loss dynamique
TAKE_PROFIT_PERCENTAGE = 5  # Take-profit optimisé

# === FRAIS KRAKEN ===
MAKER_FEE = 0.0026  # 0.26%
TAKER_FEE = 0.0016  # 0.16%

# === OBTENIR LES MEILLEURES CRYPTOS SUR KRAKEN ===
def get_top_cryptos():
    """Récupère les paires de trading disponibles sur Kraken"""
    url = f"{KRAKEN_API_URL}/public/AssetPairs"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        if "result" in data:
            pairs = list(data["result"].keys())
            return {pair: pair for pair in pairs if "USD" in pair}  # Filtrer uniquement les paires en USD
        else:
            print(f"⚠️ Réponse inattendue de Kraken : {data}")
            return {}
    except requests.exceptions.RequestException as e:
        print(f"🚨 Erreur de connexion à Kraken : {e}")
        return {}

# === OBTENIR LES PRIX EN TEMPS RÉEL DE KRAKEN ===
def get_market_price(pair):
    """Récupère le prix actuel d'une crypto depuis Kraken"""
    url = f"{KRAKEN_API_URL}/public/Ticker?pair={pair}"

    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        if "result" in data:
            first_key = list(data["result"].keys())[0]  # Obtenir la clé du dictionnaire
            return float(data["result"][first_key]["c"][0])  # Dernier prix du marché
        else:
            print(f"⚠️ Kraken n'a pas retourné de prix pour {pair}. Réponse reçue : {data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"🚨 Erreur de connexion à Kraken : {e}")
        return None

# === DÉTECTION AUTOMATIQUE DE LA CRYPTO LA PLUS VOLATILE ===
def find_most_volatile_crypto():
    """Analyse plusieurs cryptos et choisit la plus volatile"""
    top_cryptos = get_top_cryptos()
    
    if not top_cryptos:
        print("❌ Impossible de récupérer les cryptos du moment, réessai en cours...")
        return None

    volatilities = {}

    for pair in top_cryptos.keys():
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

# === DASHBOARD WEB ===
app = Flask(__name__)

@app.route('/status')
def get_status():
    best_pair = find_most_volatile_crypto()
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
        best_pair = find_most_volatile_crypto()
        if best_pair is None:
            time.sleep(DASHBOARD_REFRESH)
            continue

        market_price = get_market_price(best_pair)
        if market_price:
            trade_size = CAPITAL * TRADE_ALLOCATION
            print(f"📈 Trade simulé : Achat de {trade_size} USD sur {best_pair} à {market_price}$")
            time.sleep(5)
            print(f"📈 Trade simulé : Vente de {trade_size} USD sur {best_pair} à {market_price * (1 + TAKE_PROFIT_PERCENTAGE / 100)}$")
            profit_today = (trade_size * (TAKE_PROFIT_PERCENTAGE / 100)) - (trade_size * TAKER_FEE)
            CAPITAL += profit_today
            print(f"📈 Gain réalisé : {profit_today:.2f}$. Nouveau capital : {CAPITAL:.2f}$")

        time.sleep(DASHBOARD_REFRESH)

# === DÉMARRAGE SUR RAILWAY ===
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    run_pumpy()

@app.route('/')
def home():
    return "🚀 PUMPY est en ligne ! Utilise /status pour voir les performances.", 200
