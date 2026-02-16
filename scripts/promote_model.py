#!/usr/bin/env python3
"""
Script de promotion de modèle MLflow
Permet de promouvoir un modèle entre les stages (None → Staging → Production)

Usage:
 python scripts/promote_model.py --model-name classification_model --to-stage Production
 python scripts/promote_model.py --model-name classification_model --version 5 --to-stage Staging
 python scripts/promote_model.py --model-name classification_model --from-stage Staging --to-stage Production --auto-archive
"""

import argparse
import sys
import os
from datetime import datetime
from typing import Optional

try:
 import mlflow
 from mlflow.tracking import MlflowClient
 from mlflow.exceptions import MlflowException
except ImportError:
 print(" MLflow n'est pas installé. Installer avec: pip install mlflow")
 sys.exit(1)


# ============================================================================
# FONCTIONS PRINCIPALES
# ============================================================================

def get_mlflow_client(tracking_uri: Optional[str] = None) -> MlflowClient:
 """
 Créer un client MLflow

 Args:
 tracking_uri: URI du serveur MLflow (ou variable d'environnement MLFLOW_TRACKING_URI)

 Returns:
 Client MLflow
 """
 if tracking_uri:
 mlflow.set_tracking_uri(tracking_uri)
 elif os.getenv("MLFLOW_TRACKING_URI"):
 mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))
 else:
 print(" MLFLOW_TRACKING_URI non défini, utilisation de l'URI par défaut")

 return MlflowClient()


def list_model_versions(
 client: MlflowClient,
 model_name: str,
 stage: Optional[str] = None
):
 """
 Lister les versions d'un modèle

 Args:
 client: Client MLflow
 model_name: Nom du modèle
 stage: Filtrer par stage (None, Staging, Production, Archived)
 """
 try:
 versions = client.search_model_versions(f"name='{model_name}'")

 if not versions:
 print(f" Aucune version trouvée pour le modèle '{model_name}'")
 return []

 # Filtrer par stage si spécifié
 if stage:
 versions = [v for v in versions if v.current_stage == stage]

 # Trier par version (descendant)
 versions = sorted(versions, key=lambda x: int(x.version), reverse=True)

 return versions

 except MlflowException as e:
 print(f" Erreur MLflow: {e}")
 return []


def promote_model_version(
 client: MlflowClient,
 model_name: str,
 version: Optional[str] = None,
 from_stage: Optional[str] = None,
 to_stage: str = "Production",
 auto_archive: bool = False
) -> bool:
 """
 Promouvoir une version de modèle

 Args:
 client: Client MLflow
 model_name: Nom du modèle
 version: Version spécifique à promouvoir (optionnel)
 from_stage: Stage source (si version non spécifiée)
 to_stage: Stage cible (Staging, Production)
 auto_archive: Archiver automatiquement les versions existantes

 Returns:
 True si succès, False sinon
 """
 try:
 # Déterminer la version à promouvoir
 if version:
 # Version spécifique fournie
 target_version = version
 print(f" Promotion de la version {version} de '{model_name}'")

 elif from_stage:
 # Prendre la dernière version du stage source
 versions = list_model_versions(client, model_name, stage=from_stage)

 if not versions:
 print(f" Aucune version en stage '{from_stage}' pour '{model_name}'")
 return False

 target_version = versions[0].version
 print(f" Promotion de la version {target_version} depuis {from_stage}")

 else:
 print(" Fournir --version ou --from-stage")
 return False

 # Vérifier que la version existe
 try:
 model_version = client.get_model_version(model_name, target_version)
 except MlflowException:
 print(f" Version {target_version} introuvable pour '{model_name}'")
 return False

 # Afficher les métriques de la version
 print(f"\n Métriques de la version {target_version}:")
 run_id = model_version.run_id
 run = client.get_run(run_id)
 metrics = run.data.metrics

 for metric_name in ['balanced_accuracy', 'f1_score', 'roc_auc']:
 if metric_name in metrics:
 print(f" - {metric_name}: {metrics[metric_name]:.4f}")

 # Vérifier les versions existantes dans le stage cible
 existing_versions = list_model_versions(client, model_name, stage=to_stage)

 if existing_versions and not auto_archive:
 print(f"\n {len(existing_versions)} version(s) déjà en {to_stage}:")
 for v in existing_versions:
 print(f" - Version {v.version}")

 if to_stage == "Production":
 confirm = input(f"\n Archiver automatiquement et promouvoir ? (y/N): ")
 if confirm.lower() != 'y':
 print(" Promotion annulée")
 return False
 auto_archive = True

 # Promouvoir la version
 print(f"\n Promotion de {model_name} v{target_version} vers {to_stage}...")

 client.transition_model_version_stage(
 name=model_name,
 version=target_version,
 stage=to_stage,
 archive_existing_versions=auto_archive
 )

 print(f" Version {target_version} promue avec succès vers {to_stage}!")

 # Ajouter une description
 timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 description = f"Promoted to {to_stage} on {timestamp}"

 client.update_model_version(
 name=model_name,
 version=target_version,
 description=description
 )

 return True

 except MlflowException as e:
 print(f" Erreur lors de la promotion: {e}")
 return False


def display_model_summary(client: MlflowClient, model_name: str):
 """
 Afficher un résumé du modèle et de ses versions

 Args:
 client: Client MLflow
 model_name: Nom du modèle
 """
 print(f"\n{'='*80}")
 print(f"RÉSUMÉ DU MODÈLE: {model_name}")
 print(f"{'='*80}\n")

 # Compter les versions par stage
 all_versions = list_model_versions(client, model_name)

 if not all_versions:
 print(" Aucune version trouvée")
 return

 stages_count = {}
 for v in all_versions:
 stage = v.current_stage
 stages_count[stage] = stages_count.get(stage, 0) + 1

 print(f" Total versions: {len(all_versions)}")
 print(f"\nRépartition par stage:")
 for stage, count in sorted(stages_count.items()):
 print(f" - {stage:15s}: {count} version(s)")

 # Afficher les versions en Production
 print(f"\n{''*80}")
 print(" VERSIONS EN PRODUCTION:")
 print(f"{''*80}")

 prod_versions = [v for v in all_versions if v.current_stage == "Production"]

 if prod_versions:
 for v in prod_versions:
 print(f"\n Version {v.version}:")
 print(f" - Run ID: {v.run_id}")
 print(f" - Created: {v.creation_timestamp}")
 if v.description:
 print(f" - Description: {v.description}")
 else:
 print(" Aucune version en Production")

 # Afficher les versions en Staging
 print(f"\n{''*80}")
 print(" VERSIONS EN STAGING:")
 print(f"{''*80}")

 staging_versions = [v for v in all_versions if v.current_stage == "Staging"]

 if staging_versions:
 for v in staging_versions:
 print(f"\n Version {v.version}:")
 print(f" - Run ID: {v.run_id}")
 print(f" - Created: {v.creation_timestamp}")
 if v.description:
 print(f" - Description: {v.description}")
 else:
 print(" Aucune version en Staging")

 print(f"\n{'='*80}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
 parser = argparse.ArgumentParser(
 description="Promotion de modèle MLflow",
 formatter_class=argparse.RawDescriptionHelpFormatter,
 epilog="""
Exemples:
 # Afficher le résumé d'un modèle
 python promote_model.py --model-name classification_model --summary

 # Promouvoir la dernière version de Staging vers Production
 python promote_model.py --model-name classification_model --from-stage Staging --to-stage Production

 # Promouvoir une version spécifique vers Production
 python promote_model.py --model-name classification_model --version 5 --to-stage Production

 # Promouvoir avec archivage automatique des anciennes versions
 python promote_model.py --model-name classification_model --from-stage Staging --to-stage Production --auto-archive
 """
 )

 parser.add_argument(
 "--model-name",
 required=True,
 help="Nom du modèle MLflow"
 )

 parser.add_argument(
 "--version",
 help="Version spécifique à promouvoir"
 )

 parser.add_argument(
 "--from-stage",
 choices=["None", "Staging", "Production", "Archived"],
 help="Stage source (si version non spécifiée)"
 )

 parser.add_argument(
 "--to-stage",
 choices=["Staging", "Production", "Archived"],
 default="Production",
 help="Stage cible (défaut: Production)"
 )

 parser.add_argument(
 "--auto-archive",
 action="store_true",
 help="Archiver automatiquement les versions existantes"
 )

 parser.add_argument(
 "--tracking-uri",
 help="URI du serveur MLflow (défaut: MLFLOW_TRACKING_URI)"
 )

 parser.add_argument(
 "--summary",
 action="store_true",
 help="Afficher uniquement le résumé du modèle"
 )

 args = parser.parse_args()

 # Créer client MLflow
 client = get_mlflow_client(args.tracking_uri)

 # Mode résumé
 if args.summary:
 display_model_summary(client, args.model_name)
 return 0

 # Promotion
 success = promote_model_version(
 client=client,
 model_name=args.model_name,
 version=args.version,
 from_stage=args.from_stage,
 to_stage=args.to_stage,
 auto_archive=args.auto_archive
 )

 if success:
 print("\n" + "="*80)
 display_model_summary(client, args.model_name)
 return 0
 else:
 return 1


if __name__ == "__main__":
 sys.exit(main())
