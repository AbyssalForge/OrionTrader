from prefect import flow, task, get_run_logger
from utils.data_loader import import_data
from utils.model import find_best_hyperparams, train_final_model, save_trained_model, save_best_config
from utils.metric import evaluate_model, show_gain
import pandas as pd
import mlflow
import mlflow.sklearn
import json
import os
import numpy as np


# Chargement des données
@task(name="Récupération et séparation des données", retries=3, retry_delay_seconds=10)
def fetch_data_task():
    logger = get_run_logger()
    df_train, df_test = import_data()

    if df_train is None or df_test is None or df_train.empty or df_test.empty:
        raise ValueError("Aucune donnée importée ou DataFrame vide !")

    logger.info(f"✅ Données importées : {len(df_train)} train / {len(df_test)} test")
    return df_train, df_test


# Recherche des hyperparamètres avec mise en cache locale (JSON)
@task(name="Recherche des hyperparamètres optimaux")
def hyperparam_optimization_task(df_train, n_trials: int = 20):
    logger = get_run_logger()
    cache_path = "artifacts/best_hyperparams.json"
    os.makedirs("artifacts", exist_ok=True)

    # 🔹 Si un cache existe, on le charge pour éviter de relancer l'optimisation
    if os.path.exists(cache_path):
        logger.info("⚡ Chargement des hyperparamètres depuis le cache local.")
        with open(cache_path, "r") as f:
            data = json.load(f)
        best_params, config = data["best_params"], data["config"]
        return best_params, config

    # 🔹 Sinon, on lance l’optimisation
    best_params, config = find_best_hyperparams(df_train, n_trials)
    logger.info(f"🏆 Meilleurs hyperparamètres trouvés : {best_params}")

    # 🔸 Sauvegarde locale + MLflow
    save_best_config(best_params, config)
    if mlflow.active_run() is not None:
        mlflow.log_params(best_params)

    return best_params, config


# Entraînement du modèle
@task(name="Entraînement du modèle", retries=2, retry_delay_seconds=30)
def train_model_task(best_params, df_train):
    logger = get_run_logger()
    model = train_final_model(best_params, df_train)
    logger.info("📈 Modèle entraîné avec succès.")

    if mlflow.active_run() is not None:
        mlflow.sklearn.log_model(model, artifact_path="final_model")

    return model

# Évaluation du modèle de test
@task(name="Évaluation du modèle sur données de test")
def test_model_task(model, df_test):
    logger = get_run_logger()
    if not all(col in df_test.columns for col in ["close"]):
        raise ValueError("Le DataFrame de test doit contenir la colonne 'close'.")

    price_array = df_test[["close"]].values
    tech_array = np.column_stack([
        df_test["close"].pct_change().fillna(0),
        df_test["close"].rolling(5).mean().bfill()
    ])
    turbulence_array = np.zeros(len(df_test))

    config_test = {
        "price_array": price_array,
        "tech_array": tech_array,
        "turbulence_array": turbulence_array,
        "if_train": False
    }

    actions_list, total_assets, env_test = evaluate_model(model, config_test)
    gain_pct = (env_test.total_asset / env_test.initial_capital - 1) * 100
    logger.info(f"💰 Gain total : {gain_pct:.2f}%")

    if mlflow.active_run() is not None:
        mlflow.log_metric("gain_pct", gain_pct)

    return actions_list, total_assets, env_test


# Visualisation des gains
@task(name="Affichage des gains")
def show_profit_task(actions_list, total_assets, env_test, show_plot=True):
    show_gain(actions_list, total_assets, env_test, show_plot)


# Sauvegarde du modèle
@task(name="Sauvegarde du modèle")
def save_model_task(model):
    logger = get_run_logger()
    path = save_trained_model(model)
    logger.info(f"💾 Modèle sauvegardé sous : {path}")

    if mlflow.active_run() is not None:
        mlflow.log_artifact(path, artifact_path="saved_models")

    return path


# Flow principal Prefect
@flow(name="Pipeline de Training Forex Metrics PRO")
def training_pipeline(show_plot=True, n_trials=1):
    """
    Pipeline d'entraînement complet :
      1. Chargement des données
      2. Recherche des hyperparamètres
      3. Entraînement
      4. Évaluation
      5. Visualisation
      6. Sauvegarde
    """
    logger = get_run_logger()

    mlflow.set_tracking_uri("file:./mlruns")
    mlflow.set_experiment("ForexMetricsPro")

    with mlflow.start_run():
        df_train, df_test = fetch_data_task()

        mlflow.log_param("data_start", str(df_train["time"].min()))
        mlflow.log_param("data_end", str(df_train["time"].max()))
        mlflow.log_param("n_trials", n_trials)

        # Hyperparamètres
        best_params, config = hyperparam_optimization_task(df_train, n_trials)

        # Entraînement
        model = train_model_task(best_params, df_train)

        # Test & Visualisation
        actions_list, total_assets, env_test = test_model_task(model, df_test)
        show_profit_task(actions_list, total_assets, env_test, show_plot)

        # Sauvegarde finale
        save_model_task(model)

        logger.info("🎯 Pipeline terminé avec succès.")


if __name__ == "__main__":
    training_pipeline()
