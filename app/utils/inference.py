# inference.py
import pandas as pd
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from finrl.meta.env_stock_trading.env_stocktrading_np import StockTradingEnv
from stable_baselines3.common.monitor import Monitor

# --- fonction utilitaire ---
def make_env(df, if_train=False):
    """Construit un environnement identique à celui d’entraînement."""
    def _init():
        price_array = df[['close']].values
        tech_array = np.column_stack([
            df['close'].pct_change().fillna(0),
            df['close'].rolling(5).mean().bfill()
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


def load_model(model_path="../../models/orion_model.zip"):
    """Charge le modèle PPO sauvegardé."""
    model = PPO.load(model_path)
    return model


def run_inference(model, df):
    """
    Fait tourner le modèle sur un nouvel ensemble de données.
    Retourne la liste des actions et récompenses.
    """
    env = DummyVecEnv([make_env(df, if_train=False)])
    obs = env.reset()
    done = False
    actions, rewards = [], []

    while not done:
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        actions.append(float(action))
        rewards.append(float(reward))
        done = done[0] if isinstance(done, np.ndarray) else done

    total_reward = np.sum(rewards)
    return {
        "total_reward": total_reward,
        "actions": actions[-10:],  # dernieres 10 actions pour résumé
        "n_steps": len(actions)
    }
