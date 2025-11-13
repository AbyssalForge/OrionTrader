from prefect import flow, task, get_run_logger
import mlflow
import mlflow.sklearn
import json
import os
import numpy as np
from datetime import datetime

from data.mt5_loader import MT5DataLoader
from models.environment import TradingEnvBuilder
from models.trainer import PPOTrainer

from utils.model import find_best_hyperparams, train_final_model
from util.io_utils import save_trained_model, save_best_config
from utils.metric import evaluate_model, show_gain
from models.environment import TradingEnvBuilder
from models.trainer import PPOTrainer
import os
import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2025-11-01")
PARQUET_PATH = f"data/{SYMBOL.lower()}_{TIMEFRAME}.parquet"

MT5_LOGIN = int(os.environ.get('MT5_LOGIN'))
MT5_PASSWORD = os.environ.get('MT5_PASSWORD')
MT5_SERVER = os.environ.get('MT5_SERVER')

ppo_trainer = PPOTrainer()

# Chargement des données
@task(name="Data recovery and separation", retries=3, retry_delay_seconds=10)
def fetch_data_task():
    logger = get_run_logger()
    mt5_data_loader = MT5DataLoader(symbol= SYMBOL, timeframe= TIMEFRAME, start= START, end= END, parquet_path= PARQUET_PATH, login= MT5_LOGIN, password= MT5_PASSWORD, server= MT5_SERVER)
    df_train, df_test = mt5_data_loader.load_data()  # utilise ta fonction existante

    if df_train is None or df_test is None or df_train.empty or df_test.empty:
        raise ValueError("Aucune donnée importée ou DataFrame vide !")

    logger.info(f"✅ Données importées : {len(df_train)} train / {len(df_test)} test")
    
    return df_train, df_test

# Recherche des hyperparamètres (cache)
@task(name="Searching for optimal hyperparameters")
def hyperparam_optimization_task(df_train, n_trials: int = 20):
    logger = get_run_logger()
    cache_path = "artifacts/best_hyperparams.json"
    os.makedirs("artifacts", exist_ok=True)

    ppo_trainer.df_train = df_train

    # Chargement cache si présent
    if os.path.exists(cache_path):
        logger.info("⚡ Chargement des hyperparamètres depuis le cache local.")
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["best_params"], data["config"]

    # Lancer la recherche (ta fonction existante)
    best_params, config = ppo_trainer.find_best_hyperparams(n_trials = n_trials)
    logger.info(f"🏆 Meilleurs hyperparamètres trouvés : {best_params}")

    # Sauvegarde locale + MLflow
    save_best_config(best_params, config)
    if mlflow.active_run():
        mlflow.log_params(best_params)

    return best_params, config


# Entraînement du modèle
@task(name="Model training", retries=2, retry_delay_seconds=30)
def train_model_task(best_params, df_train, total_timesteps: int = 500_000):
    logger = get_run_logger()
    env_builder = TradingEnvBuilder.make_env(df_train, seed=42, if_train=True)
    model = ppo_trainer.train_final_model(total_timesteps=total_timesteps)

    logger.info("📈 Modèle entraîné avec succès.")

    if mlflow.active_run():
        try:
            mlflow.sklearn.log_model(model, name="orion_model")
        except Exception as exc:
            logger.warning(f"Impossible de logguer le modèle via mlflow.sklearn : {exc}")

    return model


# Évaluation sur les données de test
@task(name="Model evaluation on test data")
def test_model_task(model, df_test):
    logger = get_run_logger()
    required_cols = ["close", "high", "low", "open"]
    
    ppo_trainer.df_test = df_test
    
    if not all(c in df_test.columns for c in required_cols):
        raise ValueError(f"Le DataFrame de test doit contenir : {required_cols}")

    # Créer l'environnement de test via make_env
    env_fn = TradingEnvBuilder.make_env(df_test, seed=42, if_train=False)
    env_instance = env_fn()  # Monitor wrapping StockTradingEnv

    # Construction des features technique comme environment
    dir(env_instance.env)
    config_test = {
        "price_array": env_instance.env.price_ary,
        "tech_array": env_instance.env.tech_ary,
        "turbulence_array": env_instance.env.turbulence_ary,
        "if_train": False
    }

    actions_list, total_assets, env_test = evaluate_model(model, config_test)
    gain_pct = (env_test.total_asset / env_test.initial_capital - 1) * 100
    logger.info(f"💰 Gain total : {gain_pct:.2f}%")

    if mlflow.active_run():
        mlflow.log_metric("gain_pct", float(gain_pct))

    return actions_list, total_assets, env_test


# Visualisation (optionnelle)
@task(name="Earnings display")
def show_profit_task(actions_list, total_assets, env_test, show_plot: bool = True):
    show_gain(actions_list, total_assets, env_test, show_plot)


# Sauvegarde du modèle
@task(name="Saving the model")
def save_model_task(model, model_name: str = None):
    logger = get_run_logger()
    if model_name is None:
        model_name = f"orion_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    model_path, metrics_path = save_trained_model(model, base_path="models", model_name=model_name)
    logger.info(f"💾 Modèle sauvegardé sous : {model_path}")

    if mlflow.active_run():
        try:
            mlflow.log_artifact(model_path, name="saved_models")
        except Exception as exc:
            logger.warning(f"Impossible de log l'artifact: {exc}")

    return model_path, metrics_path


# Flow principal Prefect
@flow(name="Pipeline de Training Forex Metrics PRO")
def training_pipeline(show_plot: bool = True, n_trials: int = 20, total_timesteps: int = 500_000):
    logger = get_run_logger()

    # MLflow setup
    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("OrionTrader")
    run_name = f"model_train_{datetime.now().strftime('%Y/%m/%d_%H:%M:%S')}"

    with mlflow.start_run(run_name=run_name):
        logger.info(f"🚀 Démarrage du run MLflow : {run_name}")

        # 1) Données
        df_train, df_test = fetch_data_task()

        # Log data range
        try:
            mlflow.log_param("data_start", str(df_train["time"].min()))
            mlflow.log_param("data_end", str(df_train["time"].max()))
        except Exception:
            logger.debug("Impossible de logger data_start/data_end (colonnes time absentes ou format inattendu).")

        mlflow.log_param("n_trials", n_trials)        

        # 2) Hyperparam search
        best_params, config = hyperparam_optimization_task(df_train, n_trials)

        # 3) Training
        model = train_model_task(best_params, df_train, total_timesteps)

        # 4) Test / Eval
        actions_list, total_assets, env_test = test_model_task(model, df_test)

        # 5) Visualisation
        show_profit_task(actions_list, total_assets, env_test, show_plot)

        # 6) Sauvegarde
        model_name = f"ppo_orion_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        model_path, metrics_path = save_model_task(model, model_name)

        logger.info("🎯 Pipeline terminé avec succès.")


if __name__ == "__main__":
    training_pipeline()
