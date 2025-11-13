from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List
import pandas as pd
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from finrl.meta.env_stock_trading.env_stocktrading_np import StockTradingEnv
import mlflow

app = FastAPI(
    title="OrionTrader Inference API",
    description="API pour exécuter le dernier modèle Orion PPO depuis MLflow.",
    version="1.0.0"
)

# -----------------------------
# 1️⃣ Charger le dernier modèle PPO depuis MLflow
# -----------------------------
def load_latest_ppo_model(model_name: str = "orion_model"):
    mlflow.set_tracking_uri("file:./mlruns")
    model_uri = f"models:/{model_name}/latest"
    print(f"🔄 Chargement du modèle PPO depuis MLflow : {model_uri}")
    local_path = mlflow.artifacts.download_artifacts(model_uri)
    model = PPO.load(local_path)
    print("✅ Modèle PPO chargé avec succès.")
    return model

model = load_latest_ppo_model()


# -----------------------------
# 2️⃣ Recréation de l’environnement identique à l’entraînement
# -----------------------------
def make_env(df, if_train=False):
    """Construit un environnement identique à celui d'entraînement."""
    def _init():
        price_array = df[["close"]].values
        tech_array = np.column_stack([
            df["close"].pct_change().fillna(0),
            df["close"].rolling(5).mean().bfill()
        ])
        turbulence_array = np.zeros(len(df))
        config = {
            "price_array": price_array,
            "tech_array": tech_array,
            "turbulence_array": turbulence_array,
            "if_train": if_train
        }
        env = StockTradingEnv(config=config)
        return Monitor(env)
    return _init


# -----------------------------
# 3️⃣ Endpoint de prédiction
# -----------------------------
class PredictRequest(BaseModel):
    data: Dict[str, List[float]]  # exemple: colonnes = close, open, high, low, volume


@app.post("/predict")
def predict(request: PredictRequest):
    """Fait tourner le modèle PPO sur les données fournies."""
    df = pd.DataFrame(request.data)
    if df.empty:
        return {"status": "error", "message": "Les données fournies sont vides."}

    env = DummyVecEnv([make_env(df, if_train=False)])
    obs = env.reset()
    done = False
    actions, rewards = [], []

    try:
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, info = env.step(action)
            actions.append(float(action))
            rewards.append(float(reward))
            done = done[0] if isinstance(done, np.ndarray) else done
    except Exception as e:
        return {"status": "error", "message": f"Erreur pendant la simulation : {e}"}

    total_reward = np.sum(rewards)
    last_action = actions[-1] if actions else 0
    action_label = {1.0: "BUY", -1.0: "SELL", 0.0: "HOLD"}.get(last_action, "HOLD")

    return {
        "status": "success",
        "action": action_label,
        "action_code": last_action,
        "total_reward": total_reward,
        "n_steps": len(actions)
    }


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": True}
