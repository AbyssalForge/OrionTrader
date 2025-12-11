"""
Exemple d'utilisation de Vault dans FastAPI
"""

from fastapi import FastAPI, HTTPException
from utils.vault_helper import get_vault
from datetime import datetime

app = FastAPI(title="OrionTrader API - Exemple Vault")


# ═══════════════════════════════════════════════════════════════════════
# EXEMPLE 1: Récupérer un secret simple
# ═══════════════════════════════════════════════════════════════════════

@app.get("/")
def root():
    """Endpoint de base"""
    return {
        "message": "OrionTrader API with Vault",
        "endpoints": [
            "/secret/binance",
            "/secret/mt5",
            "/health",
            "/config"
        ]
    }


@app.get("/secret/binance")
def get_binance_secret():
    """Récupérer les credentials Binance depuis Vault"""
    try:
        vault = get_vault()

        # Récupérer le secret complet
        binance_creds = vault.get_secret('api/binance')

        # Retourner sans exposer les secrets complets
        return {
            "status": "success",
            "api_key_preview": binance_creds['api_key'][:10] + "...",
            "has_secret": bool(binance_creds.get('api_secret'))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# EXEMPLE 2: Récupérer plusieurs secrets
# ═══════════════════════════════════════════════════════════════════════

@app.get("/secret/mt5")
def get_mt5_secret():
    """Récupérer les credentials MT5 depuis Vault"""
    try:
        vault = get_vault()

        # Récupérer les credentials MT5
        mt5_creds = vault.get_secret('api/mt5')

        return {
            "status": "success",
            "login": mt5_creds['login'],
            "server": mt5_creds['server'],
            "password_set": bool(mt5_creds.get('password'))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# EXEMPLE 3: Utiliser dans une logique métier
# ═══════════════════════════════════════════════════════════════════════

@app.post("/trade/execute")
def execute_trade(symbol: str, amount: float):
    """
    Exemple d'exécution de trade utilisant les secrets Vault
    """
    try:
        vault = get_vault()

        # 1. Récupérer les credentials MT5
        mt5_creds = vault.get_secret('api/mt5')

        # 2. Récupérer les clés API
        api_keys = vault.get_secret('api/binance')

        # 3. Simuler l'exécution du trade
        # En production, vous utiliseriez vraiment les credentials ici
        result = {
            "status": "executed",
            "symbol": symbol,
            "amount": amount,
            "timestamp": datetime.now().isoformat(),
            "mt5_server": mt5_creds['server'],
            "api_used": api_keys['api_key'][:5] + "..."
        }

        # 4. Sauvegarder le résultat dans Vault
        vault.set_secret(
            'api/last-trade',
            symbol=symbol,
            amount=amount,
            timestamp=datetime.now().isoformat(),
            status='executed'
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# EXEMPLE 4: Health check avec Vault
# ═══════════════════════════════════════════════════════════════════════

@app.get("/health")
def health_check():
    """Vérifier la santé de l'API et la connexion à Vault"""
    try:
        vault = get_vault()

        # Tester la connexion à Vault
        secrets_list = vault.list_secrets('api')

        return {
            "status": "healthy",
            "vault_connected": True,
            "vault_secrets_count": len(secrets_list),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "vault_connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# ═══════════════════════════════════════════════════════════════════════
# EXEMPLE 5: Configuration chargée depuis Vault
# ═══════════════════════════════════════════════════════════════════════

@app.get("/config")
def get_config():
    """Récupérer la configuration depuis Vault"""
    try:
        vault = get_vault()

        # Charger différentes configurations
        mlflow_config = vault.get_secret('mlflow/config')

        # Liste des secrets disponibles
        api_secrets = vault.list_secrets('api')

        return {
            "mlflow_uri": mlflow_config.get('tracking_uri'),
            "available_api_secrets": api_secrets,
            "environment": "development"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# EXEMPLE 6: Notification avec webhook Discord
# ═══════════════════════════════════════════════════════════════════════

@app.post("/notify")
def send_notification(message: str):
    """Envoyer une notification Discord en utilisant le webhook de Vault"""
    try:
        import requests

        vault = get_vault()

        # Récupérer le webhook Discord
        discord_config = vault.get_secret('api/discord')
        webhook_url = discord_config['webhook_url']

        # Envoyer la notification
        response = requests.post(
            webhook_url,
            json={
                "content": f"🤖 OrionTrader: {message}",
                "embeds": [{
                    "title": "Notification",
                    "description": message,
                    "color": 3066993,
                    "timestamp": datetime.now().isoformat()
                }]
            }
        )

        return {
            "status": "sent" if response.status_code == 204 else "failed",
            "message": message
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
