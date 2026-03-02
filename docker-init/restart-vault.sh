#!/bin/bash

# Script pour redémarrer Vault correctement
# NE PAS utiliser "docker restart" car cela transforme .vault-keys en dossier !

echo " Redémarrage de Vault..."

# Arrêter proprement
docker-compose down vault

# Vérifier que .vault-keys est bien un fichier (pas un dossier)
if [ -d "vault/.vault-keys" ]; then
 echo " .vault-keys est un dossier, correction en cours..."

 # Sauvegarder les clés si possible
 if [ -f "vault/.vault-keys/VAULT_UNSEAL_KEY" ]; then
 UNSEAL_KEY=$(cat vault/.vault-keys/VAULT_UNSEAL_KEY)
 ROOT_TOKEN=$(cat vault/.vault-keys/VAULT_ROOT_TOKEN)
 else
 echo " Impossible de récupérer les clés depuis le dossier"
 echo " Veuillez les saisir manuellement"
 read -p "VAULT_UNSEAL_KEY: " UNSEAL_KEY
 read -p "VAULT_ROOT_TOKEN: " ROOT_TOKEN
 fi

 # Supprimer le dossier
 rm -rf vault/.vault-keys

 # Recréer le fichier
 echo "VAULT_UNSEAL_KEY=$UNSEAL_KEY" > vault/.vault-keys
 echo "VAULT_ROOT_TOKEN=$ROOT_TOKEN" >> vault/.vault-keys

 echo " Fichier .vault-keys recréé"
fi

# Redémarrer
docker-compose up -d vault

echo "⏳ Attente du démarrage (10 secondes)..."
sleep 10

# Vérifier le statut
echo ""
echo " Statut de Vault:"
docker exec orion_vault vault status 2>&1 | head -10

echo ""
echo " Redémarrage terminé"
