from typing import List, Dict
from fastapi import APIRouter, Body, HTTPException
from utils.env_utils import DummyTradingEnv
from app.model.agent import TradingAgent
from app.model.monitor import DriftMonitor
import pandas as pd
from datetime import datetime
import numpy as np


router = APIRouter(prefix="/model", tags=["Model"])

def make_mt5_env():
    return lambda: Monitor(ForexEnv(df_mt5))

# Initialisation des composants
env = DummyTradingEnv()
agent = TradingAgent(env)
monitor = DriftMonitor()

@router.post("/predict")
async def predict(data: dict = Body(...)) -> Dict:
    """
    Prédit une action et monitore l'observation pour le drift
    """
    try:
        obs = data.get("observation")
        if not obs:
            raise HTTPException(status_code=400, detail="Observation manquante")

        # Prédiction
        action = agent.predict(obs)
        
        # Ajout au monitoring si reward disponible
        if "reward" in data:
            monitor.add_observation(
                observation=obs,
                action=action,
                reward=data["reward"]
            )
        
        return {
            "action": int(action),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retrain")
async def retrain(data: dict = Body(...)) -> Dict:
    """
    Ré-entraîne le modèle et vérifie les performances
    """
    try:
        steps = data.get("steps", 10000)
        initial_performance = agent.evaluate()
        
        # Ré-entraînement
        training_info = agent.retrain(total_timesteps=steps)
        
        # Évaluation post-entraînement
        final_performance = agent.evaluate()
        
        return {
            "status": "success",
            "steps_trained": steps,
            "initial_performance": initial_performance,
            "final_performance": final_performance,
            "training_info": training_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monitor/metrics")
async def get_monitoring_metrics() -> Dict:
    """
    Récupère les métriques actuelles du monitoring
    """
    metrics = monitor.get_latest_metrics()
    if not metrics:
        return {"status": "no_data"}
    return metrics

@router.post("/monitor/drift")
async def check_drift(data: dict = Body(...)) -> Dict:
    """
    Lance une détection de dérive et retourne les résultats
    """
    try:
        # Vérifie si suffisamment de données
        if len(monitor.observations_buffer) < 100:  # minimum arbitraire
            return {
                "status": "insufficient_data",
                "message": "Pas assez de données pour l'analyse de drift"
            }
        
        # Force la création d'un rapport
        drift_results = monitor._create_drift_report()
        
        # Si drift détecté, suggère un retraining
        if drift_results.get("drift_score", 0) > 0.7:
            return {
                "status": "drift_detected",
                "drift_score": drift_results["drift_score"],
                "recommendation": "Retraining recommandé",
                "details": drift_results
            }
            
        return {
            "status": "ok",
            "drift_score": drift_results.get("drift_score", 0),
            "details": drift_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_model_status() -> Dict:
    """
    Retourne l'état global du modèle
    """
    return {
        "model_loaded": agent is not None,
        "monitoring_active": monitor is not None,
        "observations_collected": len(monitor.observations_buffer),
        "last_training": agent.last_training_time if hasattr(agent, "last_training_time") else None,
        "env_status": env.get_info() if hasattr(env, "get_info") else {}
    }