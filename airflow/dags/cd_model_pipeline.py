"""
CD Model Pipeline - Continuous Delivery du modèle de classification

Pipeline MLOps automatisé :
  1. Validation  → compare métriques du nouveau modèle vs seuils minimaux + modèle en prod
  2. Test        → inference sur données récentes (holdout)
  3. Packaging   → enregistrement en "Staging" dans MLflow Registry
  4. Déploiement → promotion "Staging" → alias "production" dans MLflow Registry

Déclenchement :
  - Automatique : quotidien à 22h00 UTC (après ETL 18h + entraînement)
  - Manuel      : via Airflow UI (trigger DAG)
"""

import os
import json
import logging
from datetime import datetime, timedelta

import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient
from airflow.sdk import dag, task

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = "classification_model"
EXPERIMENT_NAME = "OrionTrader_classification"

# Seuils minimaux pour accepter le modèle
MIN_BALANCED_ACCURACY = 0.30
MIN_MACRO_F1 = 0.40
MAX_OVERFITTING = 0.15  # diff max entre train et test balanced_accuracy

DEFAULT_ARGS = {
    "owner": "orion",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# ─────────────────────────────────────────────
# DAG
# ─────────────────────────────────────────────
@dag(
    dag_id="cd_model_pipeline",
    description="CD pipeline : validation → test → packaging → déploiement du modèle",
    schedule="0 22 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["mlops", "cd", "classification"],
)
def cd_model_pipeline():

    @task
    def get_candidate_model() -> dict:
        """
        Cherche le dernier modèle enregistré dans MLflow.
        Retourne les infos de la version candidate (la plus récente).
        """
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = MlflowClient()

        versions = client.search_model_versions(f"name='{MODEL_NAME}'")
        if not versions:
            raise ValueError(f"Aucun modèle '{MODEL_NAME}' trouvé dans MLflow Registry")

        # Trier par version décroissante → prendre la plus récente
        latest = sorted(versions, key=lambda v: int(v.version), reverse=True)[0]

        # Récupérer les métriques du run associé
        run = mlflow.get_run(latest.run_id)
        metrics = run.data.metrics
        params = run.data.params

        log.info(f"Modèle candidat : version={latest.version}, run_id={latest.run_id}")
        log.info(f"Métriques : {metrics}")

        return {
            "version": latest.version,
            "run_id": latest.run_id,
            "current_stage": latest.current_stage,
            "balanced_accuracy": metrics.get("best_balanced_accuracy", 0),
            "macro_f1": metrics.get("best_macro_f1", 0),
            "accuracy": metrics.get("best_accuracy", 0),
            "overfitting": metrics.get("overfitting", 0),
            "n_features": int(params.get("n_features", 0)),
        }

    @task
    def validate_model(candidate: dict) -> dict:
        """
        Étape 1 : Validation
        Compare les métriques du candidat vs :
          - Seuils minimaux absolus
          - Modèle actuellement en production
        """
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = MlflowClient()

        errors = []
        warnings = []

        # ── Validation contre seuils minimaux ──
        if candidate["balanced_accuracy"] < MIN_BALANCED_ACCURACY:
            errors.append(
                f"balanced_accuracy {candidate['balanced_accuracy']:.3f} "
                f"< seuil {MIN_BALANCED_ACCURACY}"
            )
        if candidate["macro_f1"] < MIN_MACRO_F1:
            errors.append(
                f"macro_f1 {candidate['macro_f1']:.3f} "
                f"< seuil {MIN_MACRO_F1}"
            )

        # ── Détection d'overfitting ──
        overfitting = candidate["overfitting"]
        if overfitting > MAX_OVERFITTING:
            errors.append(
                f"Overfitting détecté : diff={overfitting:.3f} > max={MAX_OVERFITTING}"
            )

        # ── Comparaison avec le modèle en production ──
        prod_metrics = {}
        try:
            prod_version = client.get_model_version_by_alias(MODEL_NAME, "production")
            prod_run = mlflow.get_run(prod_version.run_id)
            prod_metrics = prod_run.data.metrics
            prod_balanced_acc = prod_metrics.get("test_balanced_accuracy", 0)

            if candidate["balanced_accuracy"] < prod_balanced_acc - 0.02:
                warnings.append(
                    f"Candidat moins bon que la prod : "
                    f"{candidate['balanced_accuracy']:.3f} vs {prod_balanced_acc:.3f}"
                )
                errors.append("Régression de performance vs modèle en production")
        except Exception:
            log.info("Aucun modèle en production — premier déploiement")

        passed = len(errors) == 0

        if not passed:
            raise ValueError(f"Validation échouée :\n" + "\n".join(f"  - {e}" for e in errors))

        log.info(f"Validation réussie pour version {candidate['version']}")
        return {**candidate, "validation_passed": True, "warnings": warnings}

    @task
    def test_model(candidate: dict) -> dict:
        """
        Étape 2 : Test sur données récentes
        Charge le modèle et fait une inference sur les 500 dernières bougies.
        Vérifie que la distribution des prédictions est cohérente.
        """
        from clients.vault_helper import get_vault
        from urllib.parse import quote_plus
        from sqlalchemy import create_engine, text

        mlflow.set_tracking_uri(MLFLOW_URI)
        os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"

        # ── Charger le modèle depuis MLflow ──
        model_uri = f"runs:/{candidate['run_id']}/model"
        model = mlflow.pyfunc.load_model(model_uri)

        # ── Récupérer les features depuis la DB ──
        vault = get_vault()
        db_host = os.getenv("POSTGRES_HOST") or vault.get_secret("Database", "POSTGRES_HOST")
        db_port = os.getenv("POSTGRES_PORT") or vault.get_secret("Database", "POSTGRES_PORT")
        db_name = vault.get_secret("Database", "POSTGRES_DB")
        db_user = vault.get_secret("Database", "POSTGRES_USER")
        db_pass = vault.get_secret("Database", "POSTGRES_PASSWORD")

        conn_str = (
            f"postgresql://{quote_plus(db_user)}:{quote_plus(db_pass)}"
            f"@{db_host}:{db_port}/{db_name}"
        )
        engine = create_engine(conn_str)

        with engine.connect() as conn:
            df = pd.read_sql(
                text("SELECT * FROM market_snapshot_m15 ORDER BY time DESC LIMIT 500"),
                conn
            )

        if df.empty:
            raise ValueError("Aucune donnée dans market_snapshot_m15 pour le test")

        # ── Préparer les features (exclure colonnes non-features) ──
        exclude_cols = {"time", "target", "symbol"}
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        X_test = df[feature_cols].fillna(0)

        # ── Inference ──
        predictions = model.predict(X_test)
        pred_series = pd.Series(predictions)
        distribution = pred_series.value_counts(normalize=True).to_dict()

        log.info(f"Distribution des prédictions : {distribution}")

        # Vérification : aucune classe ne doit dépasser 90% (modèle dégénéré)
        max_class_pct = max(distribution.values()) if distribution else 1.0
        if max_class_pct > 0.90:
            raise ValueError(
                f"Distribution dégénérée : une classe représente {max_class_pct:.1%} des prédictions"
            )

        n_predictions = len(predictions)
        log.info(f"Test réussi : {n_predictions} prédictions, distribution OK")

        return {
            **candidate,
            "test_passed": True,
            "n_predictions": n_predictions,
            "pred_distribution": {str(k): float(v) for k, v in distribution.items()},
        }

    @task
    def package_model(candidate: dict) -> dict:
        """
        Étape 3 : Packaging
        Transite le modèle vers le stage "Staging" dans MLflow Registry.
        """
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = MlflowClient()

        client.transition_model_version_stage(
            name=MODEL_NAME,
            version=candidate["version"],
            stage="Staging",
            archive_existing_versions=False,
        )

        log.info(f"Modèle version {candidate['version']} → Staging")

        return {**candidate, "package_stage": "Staging"}

    @task
    def deploy_model(candidate: dict) -> dict:
        """
        Étape 4 : Déploiement
        Promeut le modèle de Staging vers l'alias "production" dans MLflow Registry.
        Archive l'ancienne version en production.
        """
        mlflow.set_tracking_uri(MLFLOW_URI)
        client = MlflowClient()

        # Archiver l'ancienne version en production
        try:
            old_prod = client.get_model_version_by_alias(MODEL_NAME, "production")
            if old_prod.version != candidate["version"]:
                client.transition_model_version_stage(
                    name=MODEL_NAME,
                    version=old_prod.version,
                    stage="Archived",
                )
                log.info(f"Ancienne version {old_prod.version} → Archived")
        except Exception:
            log.info("Aucune version en production à archiver")

        # Promouvoir la nouvelle version
        client.set_registered_model_alias(
            name=MODEL_NAME,
            alias="production",
            version=candidate["version"],
        )

        client.transition_model_version_stage(
            name=MODEL_NAME,
            version=candidate["version"],
            stage="Production",
            archive_existing_versions=True,
        )

        log.info(f"Modèle version {candidate['version']} → Production (alias: production)")

        return {
            **candidate,
            "deployed": True,
            "deployed_at": datetime.utcnow().isoformat(),
        }

    @task
    def notify(result: dict):
        """
        Notification Discord (optionnelle, via Vault)
        """
        try:
            from clients.vault_helper import get_vault
            import urllib.request

            vault = get_vault()
            webhook_url = vault.get_secret("Discord", "WEBHOOK_URL")

            message = (
                f"✅ **CD Model Pipeline — Déploiement réussi**\n"
                f"```\n"
                f"Modèle     : {MODEL_NAME}\n"
                f"Version    : {result['version']}\n"
                f"Bal. Acc   : {result['balanced_accuracy']:.3f}\n"
                f"Macro F1   : {result['macro_f1']:.3f}\n"
                f"Préd. test : {result['n_predictions']}\n"
                f"Déployé le : {result['deployed_at']}\n"
                f"```"
            )

            payload = json.dumps({"content": message}).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req)
            log.info("Notification Discord envoyée")
        except Exception as e:
            log.warning(f"Notification Discord ignorée : {e}")

    # ─────────────────────────────────────────────
    # Pipeline (séquentiel : chaque étape dépend de la précédente)
    # ─────────────────────────────────────────────
    candidate = get_candidate_model()
    validated = validate_model(candidate)
    tested = test_model(validated)
    packaged = package_model(tested)
    deployed = deploy_model(packaged)
    notify(deployed)


cd_model_pipeline()
