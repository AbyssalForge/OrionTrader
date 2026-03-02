"""
Configuration MLflow pour désactiver la vérification du Host header
"""
import os
from mlflow.server.auth import NO_PERMISSIONS

# Désactiver la protection Host header
os.environ["MLFLOW_DISABLE_HOST_HEADER_CHECK"] = "true"
