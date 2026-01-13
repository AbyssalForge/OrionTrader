#!/bin/bash

# Configurer PYTHONPATH pour accéder aux models Airflow
export PYTHONPATH="/app:/opt/airflow:${PYTHONPATH}"

echo "[INFO] PYTHONPATH: $PYTHONPATH"

# Configuration du mode de démarrage (development ou production)
RELOAD_FLAG=""

if [ "$ENVIRONMENT" = "development" ] || [ "$RELOAD" = "true" ]; then
    echo "[INFO] Mode développement: Auto-reload activé"
    RELOAD_FLAG="--reload"
else
    echo "[INFO] Mode production: Auto-reload désactivé"
fi

# Démarrer Uvicorn avec app.main:app
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 $RELOAD_FLAG
