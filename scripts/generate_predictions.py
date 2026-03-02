"""
Script pour générer 40 prédictions variées et remplir le dashboard Grafana
"""
import requests
import random
import time
from datetime import datetime
import urllib3

# Désactiver les warnings SSL pour certificat auto-signé
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://152.228.129.204:8001/model/predict"
API_TOKEN = "NB9IMYY2LUCQG0FM"

headers = {
    "X-API-Key": API_TOKEN,
    "Content-Type": "application/json"
}

# Scénarios pour obtenir différents types de prédictions
scenarios = {
    "SHORT": [
        # Marché baissier : EUR/USD en baisse, DXY en hausse, VIX élevé
        {"base_close": 1.0700, "dxy": 106.5, "vix": 28.0, "spx": 4200},
        {"base_close": 1.0680, "dxy": 107.0, "vix": 32.0, "spx": 4150},
        {"base_close": 1.0650, "dxy": 106.8, "vix": 25.5, "spx": 4180},
    ],
    "NEUTRAL": [
        # Marché stable : EUR/USD stable, VIX normal, indices stables
        {"base_close": 1.0850, "dxy": 103.5, "vix": 16.0, "spx": 4500},
        {"base_close": 1.0840, "dxy": 103.8, "vix": 18.5, "spx": 4480},
        {"base_close": 1.0860, "dxy": 103.2, "vix": 17.2, "spx": 4520},
    ],
    "LONG": [
        # Marché haussier : EUR/USD en hausse, DXY en baisse, risk-on
        {"base_close": 1.0950, "dxy": 101.5, "vix": 14.0, "spx": 4650},
        {"base_close": 1.0980, "dxy": 100.8, "vix": 12.5, "spx": 4700},
        {"base_close": 1.0920, "dxy": 102.0, "vix": 15.5, "spx": 4620},
    ]
}

def generate_payload(scenario_type, scenario_params):
    """Génère un payload de prédiction basé sur un scénario"""
    base = scenario_params["base_close"]

    # Variation aléatoire légère pour diversifier
    variation = random.uniform(-0.0015, 0.0015)
    close = base + variation

    # OHLCV cohérent
    high = close + random.uniform(0.0005, 0.0020)
    low = close - random.uniform(0.0005, 0.0020)
    open_price = close + random.uniform(-0.0010, 0.0010)

    # Assurer cohérence OHLC
    high = max(high, open_price, close)
    low = min(low, open_price, close)

    payload = {
        "open": round(open_price, 4),
        "high": round(high, 4),
        "low": round(low, 4),
        "close": round(close, 4),
        "tick_volume": random.randint(800, 2000),
        "dxy_close": round(scenario_params["dxy"] + random.uniform(-0.5, 0.5), 2),
        "vix_close": round(scenario_params["vix"] + random.uniform(-2.0, 2.0), 2),
        "spx_close": round(scenario_params["spx"] + random.uniform(-50, 50), 2)
    }

    return payload

def make_prediction(payload, index, total):
    """Fait un appel API de prédiction"""
    try:
        response = requests.post(
            API_URL,
            json=payload,
            headers=headers,
            verify=False,  # Désactiver vérification SSL
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[{index}/{total}] OK {data['prediction_label']:8s} | "
                  f"Confiance: {data['confidence']:.1%} | "
                  f"Close: {payload['close']:.4f} | "
                  f"DXY: {payload['dxy_close']:.1f} | "
                  f"VIX: {payload['vix_close']:.1f}")
            return data
        else:
            print(f"[{index}/{total}] ERREUR {response.status_code}: {response.text[:100]}")
            return None

    except Exception as e:
        print(f"[{index}/{total}] EXCEPTION: {str(e)[:100]}")
        return None

def main():
    """Génère 40 prédictions variées"""
    print(f"Demarrage de la generation de 40 predictions")
    print(f"API: {API_URL}")
    print(f"Token: {API_TOKEN[:8]}...")
    print(f"Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = {"SHORT": 0, "NEUTRAL": 0, "LONG": 0, "ERROR": 0}
    predictions = []

    # Distribution souhaitée : ~40% SHORT, 30% NEUTRAL, 30% LONG
    distribution = (
        ["SHORT"] * 16 +
        ["NEUTRAL"] * 12 +
        ["LONG"] * 12
    )
    random.shuffle(distribution)

    for i, target_type in enumerate(distribution, 1):
        # Sélectionner un scénario aléatoire du type cible
        scenario = random.choice(scenarios[target_type])
        payload = generate_payload(target_type, scenario)

        # Faire la prédiction
        result = make_prediction(payload, i, 40)

        if result:
            predictions.append(result)
            results[result['prediction_label']] += 1
        else:
            results["ERROR"] += 1

        # Pause entre les appels (éviter de surcharger l'API)
        if i < 40:
            time.sleep(0.5)

    # Résumé
    print("\n" + "="*70)
    print("RESUME DES PREDICTIONS")
    print("="*70)
    print(f"Total reussi : {len(predictions)}/40")
    print(f"SHORT        : {results['SHORT']:2d} ({results['SHORT']/40*100:5.1f}%)")
    print(f"NEUTRAL      : {results['NEUTRAL']:2d} ({results['NEUTRAL']/40*100:5.1f}%)")
    print(f"LONG         : {results['LONG']:2d} ({results['LONG']/40*100:5.1f}%)")
    print(f"ERREURS      : {results['ERROR']:2d}")

    if predictions:
        avg_confidence = sum(p['confidence'] for p in predictions) / len(predictions)
        print(f"\nConfiance moyenne : {avg_confidence:.1%}")

    print("\nGeneration terminee ! Consultez Grafana pour voir les metriques.")

if __name__ == "__main__":
    main()
