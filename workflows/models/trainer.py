import random
import uuid
import numpy as np
import torch
from functools import partial
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import CallbackList
from stable_baselines3.common.evaluation import evaluate_policy
import optuna

from .callbacks import NaNStopCallback, EarlyStoppingCallback
from .environment import TradingEnvBuilder
from util.io_utils import save_best_config, save_trained_model

class PPOTrainer:
    """
    Classe pour gérer l'optimisation des hyperparamètres et l'entraînement final
    d'un modèle PPO pour un environnement StockTradingEnv.
    """
    def __init__(self, df_train= None, df_test=None):
        self.df_train = df_train
        self.df_test = df_test
        self.best_params = None
        self.env_config = None

    def _optimize_model(self, trial, training_steps=200_000):
        seed = 1000 + trial.number
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

        # Hyperparamètres à optimiser
        learning_rate = trial.suggest_float("learning_rate", 1e-5, 3e-4, log=True)
        batch_size = trial.suggest_categorical("batch_size", [64, 128, 256])
        n_steps = max(batch_size, trial.suggest_categorical("n_steps", [1024, 2048, 4096]))
        gamma = trial.suggest_float("gamma", 0.90, 0.9999)
        clip_range = trial.suggest_float("clip_range", 0.1, 0.3)
        gae_lambda = trial.suggest_float("gae_lambda", 0.9, 0.99)
        ent_coef = trial.suggest_float("ent_coef", 1e-5, 0.01, log=True)
        vf_coef = trial.suggest_float("vf_coef", 0.4, 0.8)
        max_grad_norm = trial.suggest_float("max_grad_norm", 0.3, 0.8)

        # Environnements train/val
        train_env = DummyVecEnv([TradingEnvBuilder.make_env(self.df_train, seed, if_train=True)])
        eval_env = DummyVecEnv([TradingEnvBuilder.make_env(self.df_train, seed + 9999, if_train=False)])

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
            verbose=0
        )

        callbacks = CallbackList([NaNStopCallback(), EarlyStoppingCallback()])
        model.learn(total_timesteps=training_steps, callback=callbacks)

        mean_reward, std_reward = evaluate_policy(model, eval_env, n_eval_episodes=10)
        trial.set_user_attr("mean_reward", float(mean_reward))
        trial.set_user_attr("std_reward", float(std_reward))
        return float(mean_reward - std_reward * 0.1)

    def find_best_hyperparams(self, n_trials:int = 20):
        """
        Recherche des meilleurs hyperparamètres via Optuna.
        """
        sampler = optuna.samplers.TPESampler(multivariate=True, seed=42)
        pruner = optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1000)
        study = optuna.create_study(
            direction="maximize",
            sampler=sampler,
            pruner=pruner,
            study_name=f"ppo_{uuid.uuid4()}"
        )
        study.optimize(partial(self._optimize_model, training_steps=200_000), n_trials=n_trials)

        self.best_params = study.best_params
        # Configuration minimale de l'environnement pour sauvegarde / réutilisation
        self.env_config = {
            "price_array": self.df_train[['close']].values,
            "tech_array": np.column_stack([
                self.df_train['close'].pct_change().fillna(0),
                self.df_train['close'].rolling(5).mean().bfill()
            ]),
            "turbulence_array": np.zeros(len(self.df_train)),
            "if_train": True
        }
        return study.best_params, self.env_config

    def train_final_model(self, total_timesteps=500_000, halluc_cb=None):
        """
        Entraîne le modèle final PPO avec les meilleurs hyperparamètres.
        """
        if self.best_params is None:
            raise ValueError("⚠️ find_best_hyperparams doit être appelé avant l'entraînement final.")

        env_train = DummyVecEnv([TradingEnvBuilder.make_env(self.df_train, if_train=True)])
        model = PPO(
            "MlpPolicy",
            env_train,
            learning_rate=self.best_params["learning_rate"],
            n_steps=self.best_params["n_steps"],
            gamma=self.best_params["gamma"],
            clip_range=self.best_params["clip_range"],
            ent_coef=self.best_params.get("ent_coef", 0.0),
            verbose=1
        )

        callbacks = [halluc_cb] if halluc_cb else []
        if callbacks:
            model.learn(total_timesteps=total_timesteps, callback=callbacks)
        else:
            model.learn(total_timesteps=total_timesteps)

        return model

    def save_model_and_config(self, model, path_model="models", path_config="artifacts/best_config.json"):
        """
        Sauvegarde le modèle entraîné et la configuration.
        """
        save_best_config(self.best_params, self.env_config, path=path_config)
        return save_trained_model(model, base_path=path_model)
