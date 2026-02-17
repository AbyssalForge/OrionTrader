"""
Script pour vérifier les runs MLflow récents
"""
import mlflow
from mlflow.tracking import MlflowClient
from datetime import datetime
import os

# Configuration MLflow
MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(MLFLOW_URI)

# Désactiver la vérification SSL pour certificat auto-signé
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ["MLFLOW_TRACKING_INSECURE_TLS"] = "true"

client = MlflowClient()

print(f"MLflow Tracking URI: {MLFLOW_URI}")
print("="*70)

# Lister tous les experiments
print("\nEXPERIMENTS:")
print("-"*70)
experiments = client.search_experiments()
for exp in experiments:
    print(f"ID: {exp.experiment_id:3s} | Name: {exp.name:40s} | Lifecycle: {exp.lifecycle_stage}")

print("\n" + "="*70)

# Chercher l'experiment OrionTrader_classification
try:
    experiment = client.get_experiment_by_name("OrionTrader_classification")
    if not experiment:
        print("ERREUR: Experiment 'OrionTrader_classification' non trouve")
        exit(1)

    exp_id = experiment.experiment_id
    print(f"\nExperiment 'OrionTrader_classification' trouve (ID: {exp_id})")
    print("-"*70)

    # Récupérer les 5 derniers runs
    runs = client.search_runs(
        experiment_ids=[exp_id],
        order_by=["start_time DESC"],
        max_results=5
    )

    if not runs:
        print("Aucun run trouve dans cet experiment")
    else:
        print(f"\n{len(runs)} RUNS RECENTS:")
        print("-"*70)

        for i, run in enumerate(runs, 1):
            print(f"\n[{i}] Run ID: {run.info.run_id}")
            print(f"    Status: {run.info.status}")
            print(f"    Start: {datetime.fromtimestamp(run.info.start_time/1000).strftime('%Y-%m-%d %H:%M:%S')}")

            if run.info.end_time:
                end = datetime.fromtimestamp(run.info.end_time/1000)
                duration = (run.info.end_time - run.info.start_time) / 1000 / 60
                print(f"    End: {end.strftime('%Y-%m-%d %H:%M:%S')} (duree: {duration:.1f} min)")

            # Métriques importantes
            metrics = run.data.metrics
            params = run.data.params

            print(f"\n    METRIQUES:")
            if "best_balanced_accuracy" in metrics:
                print(f"      Balanced Accuracy: {metrics['best_balanced_accuracy']:.3f}")
            if "best_macro_f1" in metrics:
                print(f"      Macro F1: {metrics['best_macro_f1']:.3f}")
            if "best_accuracy" in metrics:
                print(f"      Accuracy: {metrics['best_accuracy']:.3f}")
            if "overfitting" in metrics:
                print(f"      Overfitting: {metrics['overfitting']:.3f}")

            print(f"\n    PARAMETRES:")
            if "n_estimators" in params:
                print(f"      n_estimators: {params['n_estimators']}")
            if "max_depth" in params:
                print(f"      max_depth: {params['max_depth']}")
            if "learning_rate" in params:
                print(f"      learning_rate: {params['learning_rate']}")
            if "n_features" in params:
                print(f"      n_features: {params['n_features']}")

            print("-"*70)

        # Vérifier le modèle enregistré
        print("\n" + "="*70)
        print("MODELES ENREGISTRES:")
        print("-"*70)

        try:
            model_versions = client.search_model_versions("name='classification_model'")

            if model_versions:
                print(f"\nNombre de versions: {len(model_versions)}")

                # Dernière version
                latest = sorted(model_versions, key=lambda v: int(v.version), reverse=True)[0]
                print(f"\nDerniere version: {latest.version}")
                print(f"  Stage: {latest.current_stage}")
                print(f"  Run ID: {latest.run_id}")
                print(f"  Created: {latest.creation_timestamp}")

                # Version en production
                try:
                    prod_version = client.get_model_version_by_alias("classification_model", "production")
                    print(f"\nVersion en PRODUCTION:")
                    print(f"  Version: {prod_version.version}")
                    print(f"  Run ID: {prod_version.run_id}")
                except:
                    print(f"\nAucune version en production (alias 'production' non trouve)")

            else:
                print("Aucun modele 'classification_model' enregistre dans MLflow Registry")

        except Exception as e:
            print(f"Erreur lors de la recherche des modeles: {e}")

except Exception as e:
    print(f"ERREUR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("Verification terminee")
