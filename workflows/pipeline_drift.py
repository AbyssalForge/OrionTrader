from prefect import flow, task, get_run_logger
import pandas as pd
import numpy as np
import os
from scipy.stats import ks_2samp

# --- Paramètres ---
TRAINING_DATA_PATH = "data/training_data.parquet"
LIVE_DATA_PATH = "data/latest_data.parquet"
DRIFT_THRESHOLD = 0.1  # seuil KS pour considérer qu'il y a un drift
PERFORMANCE_METRICS_PATH = "data/training_metrics.csv"

@task
def load_data():
    logger = get_run_logger()
    if not os.path.exists(TRAINING_DATA_PATH) or not os.path.exists(LIVE_DATA_PATH):
        raise FileNotFoundError("⚠️ Données manquantes pour le monitoring drift.")
    df_train = pd.read_parquet(TRAINING_DATA_PATH)
    df_live = pd.read_parquet(LIVE_DATA_PATH)
    logger.info(f"✅ Données chargées : {len(df_train)} lignes training, {len(df_live)} lignes live")
    return df_train, df_live


@task
def compute_data_drift(df_train, df_live):
    """Compare la distribution des features avec KS test"""
    logger = get_run_logger()
    drift_report = {}
    features = ["open", "high", "low", "close"]

    for feat in features:
        stat, p_value = ks_2samp(df_train[feat].values, df_live[feat].values)
        drift_report[feat] = {"ks_stat": stat, "p_value": p_value, "drift": stat > DRIFT_THRESHOLD}
        if stat > DRIFT_THRESHOLD:
            logger.warning(f"⚠️ Drift détecté sur {feat} (KS stat={stat:.3f})")
        else:
            logger.info(f"✅ {feat} stable (KS stat={stat:.3f})")

    drift_detected = any([v["drift"] for v in drift_report.values()])
    return drift_detected, drift_report


@task
def check_performance_drift():
    """Vérifie si les métriques RL sont en baisse"""
    logger = get_run_logger()
    if not os.path.exists(PERFORMANCE_METRICS_PATH):
        logger.warning("⚠️ Fichier de métriques non trouvé.")
        return True  # considérer qu'on doit réentraîner

    df = pd.read_csv(PERFORMANCE_METRICS_PATH)
    if "reward_mean" not in df.columns:
        logger.warning("⚠️ Pas de colonne reward_mean dans métriques.")
        return True

    last_reward = df["reward_mean"].iloc[-1]
    avg_reward = df["reward_mean"].mean()
    logger.info(f"🎯 Dernier reward = {last_reward:.3f}, moyenne = {avg_reward:.3f}")
    drift = last_reward < 0.9 * avg_reward  # seuil de tolérance
    if drift:
        logger.warning("⚠️ Performance drift détecté !")
    return drift


@task
def trigger_retraining():
    """Relance la pipeline d'entraînement si nécessaire"""
    logger = get_run_logger()
    from pipeline_training import training_pipeline
    logger.info("🚀 Drift détecté, lancement du réentraînement...")
    training_pipeline()
    logger.info("✅ Réentraînement terminé.")


@flow(name="Drift Monitoring Flow")
def drift_monitoring_pipeline():
    logger = get_run_logger()
    logger.info("🔎 Début du monitoring de drift")

    df_train, df_live = load_data()
    data_drift, drift_report = compute_data_drift(df_train, df_live)
    perf_drift = check_performance_drift()

    if data_drift or perf_drift:
        logger.info("♻️ Drift détecté, déclenchement du réentraînement")
        trigger_retraining()
    else:
        logger.info("✅ Pas de drift détecté, modèle stable")

    logger.info("🧭 Monitoring drift terminé")
    return data_drift, perf_drift, drift_report
