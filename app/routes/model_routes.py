from fastapi import APIRouter, Body, HTTPException, BackgroundTasks
from app.model.agent import TradingAgent
from app.model.monitor import DriftMonitor
from app.utils.env_utils import DummyTradingEnv
from datetime import datetime
from typing import Dict
import numpy as np
from app.utils.trading_graph import app_trading_graph

router = APIRouter(prefix="/model", tags=["Model"])

# Initialisation des composants
try:
    env = DummyTradingEnv()
    agent = TradingAgent(env)
    monitor = DriftMonitor()
    print("✅ Composants initialisés avec succès")
except Exception as e:
    print(f"❌ Erreur d'initialisation: {e}")
    raise

from fastapi import Request

@router.post("/execute")
async def execute_strategy(request: Request):
    raw_body = await request.body()
    print("📦 Corps brut reçu:", raw_body.decode("utf-8", errors="ignore"))

    try:
        data = await request.json()
    except Exception as e:
        return {"error": "Invalid JSON", "details": str(e)}

    print("📥 Données JSON:", data)
    result = app_trading_graph.invoke(data)
    print("📤 Résultat:", result)
    return result


@router.post("/predict")
async def predict(data: dict = Body(...)) -> Dict:
    """Prédit une action et monitore l'observation"""
    try:
        # Validation des données
        if "observation" not in data:
            raise HTTPException(status_code=400, detail="Observation manquante")
        
        obs = np.array(data["observation"], dtype=np.float32)
        action = agent.predict(obs)
        
        # Monitoring en arrière-plan si reward disponible
        if "reward" in data:
            monitor.add_observation(obs, action, data["reward"])
        
        return {
            "status": "success",
            "action": int(action),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_status() -> Dict:
    """Vérifie l'état du système"""
    try:
        metrics = monitor.get_latest_metrics()
        return {
            "status": "active",
            "model_loaded": agent is not None,
            "monitoring_active": monitor is not None,
            "latest_metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))