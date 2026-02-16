#!/bin/bash

echo "========================================"
echo "Initialisation de HashiCorp Vault"
echo "========================================"
echo ""

docker-compose exec -T vault sh -c '
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="orion-root-token"

echo "Activating KV v2 engine..."
vault secrets enable -version=2 -path=secret kv 2>/dev/null || echo " KV engine already enabled"

echo ""
echo "Creating policies..."
vault policy write airflow /vault/policies/airflow-policy.hcl
vault policy write fastapi /vault/policies/fastapi-policy.hcl

echo ""
echo "Creating service tokens..."
AIRFLOW_TOKEN=$(vault token create -policy=airflow -format=json | jq -r ".auth.client_token")
FASTAPI_TOKEN=$(vault token create -policy=fastapi -format=json | jq -r ".auth.client_token")

echo ""
echo "========================================="
echo " Vault initialisé avec succès!"
echo "========================================="
echo ""
echo " Tokens des services (SAUVEGARDEZ-LES):"
echo "-------------------------------------------"
echo "Airflow Token: $AIRFLOW_TOKEN"
echo "FastAPI Token: $FASTAPI_TOKEN"
echo "Root Token: orion-root-token"
echo "========================================="
echo ""
echo " Interface Web: http://localhost:8200/ui"
echo " Token de connexion: orion-root-token"
echo ""
echo " Vous pouvez maintenant créer vos secrets via:"
echo " - Interface Web: http://localhost:8200/ui"
echo " - CLI: docker-compose exec vault vault kv put secret/mon-app/config key=value"
echo ""
'

echo ""
echo " Vault est prêt à l'emploi!"
