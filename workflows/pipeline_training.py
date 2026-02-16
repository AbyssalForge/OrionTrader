from prefect import flow, task, get_run_logger
import mlflow
import json
import os
import numpy as np
from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5
from dotenv import load_dotenv

# === Imports internes ===
from data.mt5_loader import MT5DataLoader
from models.environment import TradingEnvBuilder
from models.trainer import PPOTrainer
from utils.metric import evaluate_model, show_gain
from util.io_utils import save_best_config
from stable_baselines3 import PPO

load_dotenv()

# === Configuration ===
SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2025-11-01")
PARQUET_PATH = f"data/{SYMBOL.lower()}_{TIMEFRAME}.parquet"

MT5_LOGIN = int(os.environ.get("MT5_LOGIN"))
MT5_PASSWORD = os.environ.get("MT5_PASSWORD")
MT5_SERVER = os.environ.get("MT5_SERVER")

ppo_trainer = PPOTrainer()


# === 1️⃣ Chargement des données ===
@task(name="📊 Data recovery and separation", retries=3, retry_delay_seconds=10)
def fetch_data_task():
    logger = get_run_logger()
    loader = MT5DataLoader(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        start=START,
        end=END,
        parquet_path=PARQUET_PATH,
        login=MT5_LOGIN,
        password=MT5_PASSWORD,
        server=MT5_SERVER,
    )
    df_train, df_test = loader.load_data()

    if df_train is None or df_test is None or df_train.empty or df_test.empty:
        raise ValueError("❌ Aucune donnée importée ou DataFrame vide !")

    logger.info(f"✅ Données : {len(df_train)} train / {len(df_test)} test")
    return df_train, df_test


# === 2️⃣ Recherche d’hyperparamètres ===
@task(name="🔍 Searching for optimal hyperparameters")
def hyperparam_optimization_task(df_train, n_trials: int = 20):
    logger = get_run_logger()
    cache_path = "artifacts/best_hyperparams.json"
    os.makedirs("artifacts", exist_ok=True)

    ppo_trainer.df_train = df_train

    if os.path.exists(cache_path):
        logger.info("⚡ Chargement des hyperparamètres depuis le cache.")
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["best_params"], data["config"]

    best_params, config = ppo_trainer.find_best_hyperparams(n_trials=n_trials)
    logger.info(f"🏆 Meilleurs hyperparamètres : {best_params}")

    save_best_config(best_params, config)
    if mlflow.active_run():
        mlflow.log_params(best_params)

    return best_params, config


# === 3️⃣ Entraînement du modèle PPO ===
@task(name="🤖 Model training", retries=2, retry_delay_seconds=30)
def train_model_task(best_params, df_train, total_timesteps: int = 500_000):
    logger = get_run_logger()

    env_builder = TradingEnvBuilder.make_env(df_train, seed=42, if_train=True)
    model = ppo_trainer.train_final_model(total_timesteps=total_timesteps)

    logger.info("📈 Entraînement terminé avec succès.")
    return model


# === 4️⃣ Évaluation sur les données de test ===
@task(name="🧪 Model evaluation on test data")
def test_model_task(model, df_test):
    logger = get_run_logger()
    required_cols = ["close", "high", "low", "open"]

    if not all(c in df_test.columns for c in required_cols):
        raise ValueError(f"Le DataFrame de test doit contenir : {required_cols}")

    env_fn = TradingEnvBuilder.make_env(df_test, seed=42, if_train=False)
    env_instance = env_fn()

    config_test = {
        "price_array": env_instance.env.price_ary,
        "tech_array": env_instance.env.tech_ary,
        "turbulence_array": env_instance.env.turbulence_ary,
        "if_train": False,
    }

    actions_list, total_assets, env_test = evaluate_model(model, config_test)
    gain_pct = (env_test.total_asset / env_test.initial_capital - 1) * 100
    logger.info(f"💰 Gain total sur test : {gain_pct:.2f}%")

    if mlflow.active_run():
        mlflow.log_metric("gain_pct", float(gain_pct))

    return actions_list, total_assets, env_test


# === 5️⃣ Affichage des résultats ===
@task(name="📊 Earnings display")
def show_profit_task(actions_list, total_assets, env_test, show_plot: bool = True):
    show_gain(actions_list, total_assets, env_test, show_plot)


# === 6️⃣ Sauvegarde et enregistrement MLflow ===
@task(name="💾 Save and register PPO model")
def save_model_task(model, model_name: str = None):
    logger = get_run_logger()
    if model_name is None:
        model_name = f"ppo_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 1️⃣ Sauvegarde locale (.zip)
    os.makedirs("models", exist_ok=True)
    local_path = os.path.join("models", f"{model_name}.zip")
    model.save(local_path)
    logger.info(f"💾 Modèle PPO sauvegardé : {local_path}")

    if mlflow.active_run():
        try:
            # 2️⃣ Log dans le run MLflow actif
            mlflow.log_artifact(local_path, artifact_path="models")

            # 3️⃣ Enregistrement dans le registre (si backend supporté)
            run_id = mlflow.active_run().info.run_id
            artifact_uri = f"runs:/{run_id}/models/{model_name}.zip"

            try:
                result = mlflow.register_model(
                    model_uri=artifact_uri,
                    name="orion_model"
                )
                logger.info(f"✅ Nouveau modèle enregistré : version {result.version}")
            except Exception as reg_err:
                logger.warning(f"⚠️ Impossible d’enregistrer dans le registre MLflow : {reg_err}")

        except Exception as exc:
            logger.warning(f"⚠️ Erreur lors du log du modèle dans MLflow : {exc}")

    return local_path

# === 🚀 Flow Principal ===
@flow(name="🏗️ Pipeline de Training Forex Metrics PRO")
def training_pipeline(show_plot: bool = True, n_trials: int = 1, total_timesteps: int = 500_000):
    logger = get_run_logger()

    # Configuration MLflow
    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("OrionTrader")
    run_name = f"model_train_{datetime.now():%Y%m%d_%H%M%S}"

    with mlflow.start_run(run_name=run_name):
        logger.info(f"🚀 Démarrage du run MLflow : {run_name}")

        # Étape 1
        df_train, df_test = fetch_data_task()

        # Log data range
        if "time" in df_train.columns:
            mlflow.log_param("data_start", str(df_train["time"].min()))
            mlflow.log_param("data_end", str(df_train["time"].max()))

        mlflow.log_param("n_trials", n_trials)

        # Étape 2
        best_params, config = hyperparam_optimization_task(df_train, n_trials)

        # Étape 3
        model = train_model_task(best_params, df_train, total_timesteps)

        # Étape 4
        actions_list, total_assets, env_test = test_model_task(model, df_test)

        # Étape 5
        show_profit_task(actions_list, total_assets, env_test, show_plot)

        # Étape 6
        save_model_task(model, model_name="orion_model")

        logger.info("🎯 Pipeline terminée avec succès ✅")


if __name__ == "__main__":
    training_pipeline()
