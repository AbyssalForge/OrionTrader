import numpy as np
import os
import datetime
import optuna
from functools import partial
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from finrl.meta.env_stock_trading.env_stocktrading_np import StockTradingEnv
from utils.hallucination import HallucinationCallback
from utils.model import optimize_model
from utils.test_model import test_action_model
from utils.metric import show_gain


def find_best_hyperparams_core(df, n_trials=20):
    price_array = df[['close']].values
    tech_array = np.column_stack([
        df['close'].pct_change().fillna(0),
        df['close'].rolling(5).mean().fillna(method='bfill')
    ])
    turbulence_array = np.zeros(len(df))
    config = {
        "price_array": price_array,
        "tech_array": tech_array,
        "turbulence_array": turbulence_array,
        "if_train": True
    }

    study = optuna.create_study(direction="maximize")
    objective = partial(optimize_model, config=config)
    study.optimize(objective, n_trials=n_trials, n_jobs=-1)

    return study.best_params, config


def train_model_core(best_params, config):
    env_train = DummyVecEnv([lambda: StockTradingEnv(config=config)])
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
    callback = HallucinationCallback(env_train, verbose=1)
    model.learn(total_timesteps=500_000, callback=callback)
    return model


def test_model_core(model, config):
    actions_list, total_assets, env_test = test_action_model(model, config)
    return actions_list, total_assets, env_test


def save_model_core(model, base_path="models"):
    os.makedirs(base_path, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(base_path, f"ppo_forex_{timestamp}.zip")
    model.save(path)
    return path


def show_profit_core(actions_list, total_assets, env_test, show_plot=True):
    if show_plot:
        show_gain(actions_list, total_assets, env_test)
