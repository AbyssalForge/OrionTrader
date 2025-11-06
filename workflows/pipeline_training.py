from prefect import flow, get_run_logger
from utils.data_loader import import_data
from utils.model import optimize_model
from utils.hallucination import HallucinationCallback
from utils.test_model import test_action_model
from utils.metric import show_gain

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from finrl.meta.env_stock_trading.env_stocktrading_np import StockTradingEnv
from functools import partial
import numpy as np
import pandas as pd
import optuna
import os
import datetime
from prefect import task

# ---------------------------
# TASKS
# ---------------------------

@task(name="Récupération et nettoyage des données", retries=3, retry_delay_seconds=10)
def fetch_data() -> pd.DataFrame:
    logger = get_run_logger()
    df = import_data()
    if df.empty:
        raise ValueError("Aucune donnée importée !")
    logger.info(f"✅ Données importées : {len(df)} lignes")
    return df


@task(name="Recherche des hyperparamètres optimaux", cache_key_fn=lambda _, __: "optuna_cache", persist_result=True)
def find_hyperparametre(df: pd.DataFrame, n_trials: int = 20):
    logger = get_run_logger()

    price_array = df[['close']].values
    tech_array = np.column_stack([
        df['close'].pct_change().fillna(0),
        df['close'].rolling(5).mean().fillna(method='bfill')
    ])
    turbulence_array = np.zeros(len(df))
    if_train = True

    config = {
        "price_array": price_array,
        "tech_array": tech_array,
        "turbulence_array": turbulence_array,
        "if_train": if_train
    }

    study = optuna.create_study(direction="maximize")
    objective = partial(optimize_model, config=config)
    logger.info(f"🧪 Début optimisation avec {n_trials} essais (parallélisé) ...")
    study.optimize(objective, n_trials=n_trials, n_jobs=-1)

    logger.info(f"🏆 Meilleur params : {study.best_params}")
    return study.best_params, config


@task(name="Entraînement du modèle", retries=2, retry_delay_seconds=30)
def train_model(best_params: dict, config: dict):
    logger = get_run_logger()
    logger.info(f"🔧 Entraînement avec paramètres : {best_params}")

    env_train = DummyVecEnv([lambda: StockTradingEnv(config=config)])
    final_model = PPO(
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
    final_model.learn(total_timesteps=500_000, callback=halluc_cb)
    logger.info("✅ Entraînement terminé")
    return final_model


@task(name="Test du modèle")
def test_model(model, config: dict):
    actions_list, total_assets, env_test = test_action_model(model, config)
    
    # Tracking dans Prefect UI
    logger = get_run_logger()
    if len(total_assets) > 0:
        logger.info(f"💰 Solde initial : {env_test.initial_capital:.2f}")
        logger.info(f"💰 Solde final : {env_test.total_asset:.2f}")
        logger.info(f"📈 Gain total : {(env_test.total_asset/env_test.initial_capital - 1)*100:.2f}%")
        logger.record("final_gain_pct", (env_test.total_asset/env_test.initial_capital - 1)*100)
    logger.record("actions_count", len(actions_list))
    
    return actions_list, total_assets, env_test


@task(name="Afficher les gains")
def show_profit(actions_list, total_assets, env_test, show_plot: bool = True):
    if show_plot:
        show_gain(actions_list, total_assets, env_test)


@task(name="Sauvegarde du modèle")
def save_model(model, base_path: str = "models") -> str:
    logger = get_run_logger()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(base_path, f"ppo_forex_{timestamp}.zip")
    os.makedirs(base_path, exist_ok=True)
    model.save(path)
    logger.info(f"💾 Modèle sauvegardé : {path}")
    return path


# ---------------------------
# FLOW PRINCIPAL
# ---------------------------

@flow(name="Pipeline de Training Forex Metrics PRO")
def training_pipeline(show_plot: bool = True, n_trials: int = 20):
    df = fetch_data()
    best_params, config = find_hyperparametre(df, n_trials=n_trials)
    final_model = train_model(best_params, config)
    actions_list, total_assets, env_test = test_model(final_model, config)
    show_profit(actions_list, total_assets, env_test, show_plot)
    save_model(final_model)


# ---------------------------
# Lancer le flow
# ---------------------------
if __name__ == "__main__":
    training_pipeline()
