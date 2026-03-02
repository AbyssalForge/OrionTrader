from prefect import flow, task, get_run_logger
from datetime import datetime
import os
import json

# CONFIGURATION GLOBALE
MODEL_PATH = "models/ppo_forex.zip"           # modèle entraîné
CONFIG_PATH = "artifacts/best_config.json"    # hyperparamètres et score
MAX_AGE_DAYS = 7                              # âge max avant réentraînement
MIN_PERFORMANCE = 0.55                        # seuil de performance minimale


@task(name="Vérification de l'âge du modèle")
def check_model_age(model_path: str = MODEL_PATH, max_age_days: int = MAX_AGE_DAYS) -> bool:
    """
    Vérifie si le modèle existe et s’il est trop ancien.
    Retourne True si un réentraînement est nécessaire.
    """
    logger = get_run_logger()

    if not os.path.exists(model_path):
        logger.warning("⚠️ Aucun modèle trouvé — entraînement requis.")
        return True

    mod_time = datetime.fromtimestamp(os.path.getmtime(model_path))
    age_days = (datetime.now() - mod_time).days
    logger.info(f"🧩 Âge du modèle : {age_days} jour(s)")

    if age_days > max_age_days:
        logger.info("⏳ Modèle trop ancien — réentraînement nécessaire.")
        return True

    logger.info("✅ Modèle récent, aucune action requise.")
    return False


@task(name="Vérification des performances (best_config.json)")
def check_model_performance(config_path: str = CONFIG_PATH, threshold: float = MIN_PERFORMANCE) -> bool:
    """
    Vérifie les performances du modèle via le fichier best_config.json dans /artifacts.
    Retourne True si un réentraînement est nécessaire.
    """
    logger = get_run_logger()

    if not os.path.exists(config_path):
        logger.warning("📉 Aucun fichier best_config.json trouvé — réentraînement requis.")
        return True

    try:
        with open(config_path, "r") as f:
            data = json.load(f)

        # Extraction du score depuis le JSON
        meta = data.get("config", {})
        best_params = data.get("best_params", {})
        last_score = meta.get("last_score") or meta.get("mean_reward")  # selon ton pipeline

        logger.info(f"🎯 Dernier score connu : {last_score}")
        logger.info(f"⚙️ Hyperparamètres : {best_params}")

        if last_score is None or last_score < threshold:
            logger.warning(f"📉 Performance sous le seuil ({threshold}) — réentraînement nécessaire.")
            return True

        logger.info("✅ Performance satisfaisante.")
        return False

    except Exception as e:
        logger.error(f"❌ Erreur lecture de {config_path} : {e}")
        return True


@task(name="Déclenchement du pipeline d'entraînement")
def trigger_training():
    """
    Déclenche la pipeline d'entraînement principale (Prefect + MLflow).
    """
    logger = get_run_logger()
    logger.info("🚀 Lancement du pipeline d'entraînement principal...")

    try:
        from pipeline_training import training_pipeline
        training_pipeline(show_plot=False)
        logger.info("✅ Entraînement terminé avec succès.")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur pendant l'entraînement : {e}")
        return False


# PIPELINE DE MONITORING
@flow(name="Monitoring du modèle Forex Metrics PRO")
def monitoring_pipeline():
    """
    Supervision du modèle Forex :
      - Vérifie l'âge du modèle
      - Vérifie les performances dans best_config.json
      - Déclenche un réentraînement si nécessaire
    """
    logger = get_run_logger()
    logger.info("🔎 Démarrage du pipeline de monitoring...")

    age_check = check_model_age()
    perf_check = check_model_performance()

    need_retrain = age_check or perf_check

    if need_retrain:
        logger.info("♻️ Conditions de réentraînement remplies — déclenchement du pipeline.")
        trigger_training()
    else:
        logger.info("✅ Modèle à jour et performant — aucune action requise.")

    logger.info("🧭 Monitoring terminé.")


if __name__ == "__main__":
    monitoring_pipeline()
