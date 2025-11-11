import os
import datetime
import random
import numpy as np
import torch
import optuna
import matplotlib.pyplot as plt
from functools import partial
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.callbacks import BaseCallback, CallbackList
from finrl.meta.env_stock_trading.env_stocktrading_np import StockTradingEnv
from .hallucination import HallucinationCallback
import uuid
import numpy as np
import json
import pandas as pd

# === CALLBACKS ===

class NaNStopCallback(BaseCallback):
    """Stoppe l'entraînement si des NaN apparaissent dans les poids du modèle."""
    def _on_step(self):
        for param in self.model.policy.parameters():
            if torch.isnan(param).any():
                print("❌ NaN détecté — arrêt de l'entraînement.")
                return False
        return True


class EarlyStoppingCallback(BaseCallback):
    """Arrête l'entraînement si les récompenses stagnent."""
    def __init__(self, check_freq=5000, min_improvement=0.02, lookback=5):
        super().__init__()
        self.check_freq = check_freq
        self.min_improvement = min_improvement
        self.lookback = lookback
        self.rewards = []

    def _on_step(self):
        if self.n_calls % self.check_freq == 0 and len(self.model.ep_info_buffer) > 0:
            current_reward = np.mean([ep_info["r"] for ep_info in self.model.ep_info_buffer])
            self.rewards.append(current_reward)
            if len(self.rewards) > self.lookback:
                old_mean = np.mean(self.rewards[-self.lookback-1:-1])
                new_mean = np.mean(self.rewards[-self.lookback:])
                if (new_mean - old_mean) < self.min_improvement:
                    print(f"⚠️ Early stopping triggered: reward stagnante ({new_mean:.2f})")
                    return False
        return True


class EquityVisualizerCallback(BaseCallback):
    """Trace la balance et les positions pendant l'entraînement."""
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.equity, self.prices, self.positions = [], [], []

    def _on_step(self):
        infos = self.locals.get("infos")
        if infos:
            info = infos[0] if isinstance(infos, (list, tuple)) else infos
            if isinstance(info, dict):
                bal, pos, close = info.get("balance"), info.get("position"), info.get("close")
                if bal is not None: self.equity.append(bal)
                if pos is not None: self.positions.append(pos)
                if close is not None: self.prices.append(close)
        return True

    def plot_results(self):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[2, 1])
        ax1.plot(self.equity, color="blue"); ax1.set_title("💰 Évolution de la balance"); ax1.grid(True)
        ax2.plot(self.prices, color="gray", alpha=0.6)
        for i in range(1, len(self.positions)):
            color = "green" if self.positions[i] == 1 else "red" if self.positions[i] == -1 else None
            if color: ax2.axvspan(i-1, i, color=color, alpha=0.3)
        ax2.set_title("📈 Prix et positions"); ax2.grid(True)
        plt.tight_layout(); plt.show()


# === ENVIRONNEMENT ===

def make_env(df, seed=None, if_train=True):
    """Construit un environnement StockTradingEnv avec les bons arrays."""
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
        try:
            env.reset(seed=seed)
        except TypeError:
            pass
        return Monitor(env)
    return _init


# === OPTIMISATION AVEC OPTUNA ===

def optimize_model(trial, df_train, training_steps=200_000):
    """Optimisation d’un modèle PPO via Optuna."""
    seed = 1000 + trial.number
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)

    # --- Recherche simple ---
    learning_rate = trial.suggest_float("learning_rate", 1e-5, 3e-4, log=True)
    batch_size = trial.suggest_categorical("batch_size", [64, 128, 256])
    n_steps = max(batch_size, trial.suggest_categorical("n_steps", [1024, 2048, 4096]))
    gamma = trial.suggest_float("gamma", 0.90, 0.9999)
    clip_range = trial.suggest_float("clip_range", 0.1, 0.3)
    gae_lambda = trial.suggest_float("gae_lambda", 0.9, 0.99)
    ent_coef = trial.suggest_float("ent_coef", 1e-5, 0.01, log=True)
    vf_coef = trial.suggest_float("vf_coef", 0.4, 0.8)
    max_grad_norm = trial.suggest_float("max_grad_norm", 0.3, 0.8)

    # --- Environnements train/validation ---
    train_env = DummyVecEnv([make_env(df_train, seed, if_train=True)])
    eval_env = DummyVecEnv([make_env(df_train, seed + 9999, if_train=False)])

    model = PPO(
        "MlpPolicy",
        train_env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        gamma=gamma,
        clip_range=clip_range,
        gae_lambda=gae_lambda,
        ent_coef=ent_coef,
        vf_coef=vf_coef,
        max_grad_norm=max_grad_norm,
        verbose=0,
    )

    callbacks = CallbackList([NaNStopCallback(), EarlyStoppingCallback()])
    model.learn(total_timesteps=training_steps, callback=callbacks)

    mean_reward, std_reward = evaluate_policy(model, eval_env, n_eval_episodes=10)
    trial.set_user_attr("mean_reward", float(mean_reward))
    trial.set_user_attr("std_reward", float(std_reward))
    return float(mean_reward - std_reward * 0.1)


def find_best_hyperparams(df_train, n_trials=20):
    """Recherche des hyperparamètres optimaux (sans raffinement)."""
    # --- Config de base pour l'environnement ---
    price_array = df_train[['close']].values
    tech_array = np.column_stack([
        df_train['close'].pct_change().fillna(0),
        df_train['close'].rolling(5).mean().bfill()
    ])
    turbulence_array = np.zeros(len(df_train))
    config = {
        "price_array": price_array,
        "tech_array": tech_array,
        "turbulence_array": turbulence_array,
        "if_train": True
    }

    sampler = optuna.samplers.TPESampler(multivariate=True, seed=42)
    pruner = optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1000)

    # --- Recherche simple ---
    study = optuna.create_study(
        direction="maximize",
        sampler=sampler,
        pruner=pruner,
        study_name=f"ppo_{uuid.uuid4()}",  # nom unique
        storage=None                       # pas de persistance
    )
    study.optimize(partial(optimize_model, df_train=df_train), n_trials=n_trials)
    best_params = study.best_params

    return best_params, config


# === ENTRAÎNEMENT FINAL ===

def train_final_model(best_params, df_train):
    """Entraîne le modèle final PPO avec les meilleurs hyperparamètres."""
    env_train = DummyVecEnv([make_env(df_train, if_train=True)])
    model = PPO(
        "MlpPolicy",
        env_train,
        learning_rate=best_params["learning_rate"],
        n_steps=best_params["n_steps"],
        gamma=best_params["gamma"],
        clip_range=best_params["clip_range"],
        ent_coef=best_params["ent_coef"],
        verbose=1
    )
    halluc_cb = HallucinationCallback(env_train, verbose=1)
    model.learn(total_timesteps=500_000, callback=halluc_cb)
    return model


# === SAUVEGARDE ===

def save_best_config(best_params, config, path="artifacts/best_config.json"):
    # Conversion des ndarrays en listes
    def make_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        return obj

    serializable_config = make_serializable(config)

    with open(path, "w") as f:
        json.dump({"best_params": best_params, "config": serializable_config}, f, indent=2)

def save_trained_model(model, metrics=None, base_path="models"):
    """
    Sauvegarde le modèle entraîné + ses métriques associées dans un JSON à part.
    """
    os.makedirs(base_path, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Nom du modèle et du JSON
    model_name = f"ppo_forex_{timestamp}"
    model_path = os.path.join(base_path, f"{model_name}.zip")
    metrics_path = os.path.join(base_path, f"{model_name}_metrics.json")

    # Sauvegarde du modèle
    model.save(model_path)

    # Sauvegarde des métriques dans un JSON
    if metrics:
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

    print(f"✅ Modèle sauvegardé : {model_path}")
    if metrics:
        print(f"📊 Métriques sauvegardées : {metrics_path}")

    return model_path, metrics_path
