#!/bin/bash

# Script d'initialisation et configuration de Vault en mode production
# Ce script doit être exécuté une seule fois après le premier démarrage de Vault

echo "=== Initialisation de Vault en mode production ==="

# S'assurer que le fichier .vault-keys existe (et n'est pas un dossier)
if [ -d "vault/.vault-keys" ]; then
 echo " vault/.vault-keys est un dossier, suppression..."
 rm -rf "vault/.vault-keys"
fi

if [ ! -f "vault/.vault-keys" ]; then
 echo " Création du fichier vault/.vault-keys..."
 touch "vault/.vault-keys"
fi

# Attendre que Vault soit prêt
echo "Attente du démarrage de Vault..."
sleep 5

# Initialiser Vault (seulement si pas déjà initialisé)
INIT_OUTPUT=$(docker exec orion_vault vault operator init -key-shares=1 -key-threshold=1 -format=json 2>/dev/null)

if [ $? -eq 0 ]; then
 echo " Vault initialisé avec succès"

 # Extraire les clés
 UNSEAL_KEY=$(echo $INIT_OUTPUT | grep -o '"unseal_keys_b64":\["[^"]*"' | cut -d'"' -f4)
 ROOT_TOKEN=$(echo $INIT_OUTPUT | grep -o '"root_token":"[^"]*"' | cut -d'"' -f4)

 echo ""
 echo " IMPORTANT - SAUVEGARDEZ CES CLÉS DANS UN ENDROIT SÛR "
 echo ""
 echo "Unseal Key: $UNSEAL_KEY"
 echo "Root Token: $ROOT_TOKEN"
 echo ""
 echo "Ces clés sont également sauvegardées dans vault/.vault-keys (NE PAS COMMITTER)"

 # Sauvegarder dans un fichier (à ne pas committer)
 cat > vault/.vault-keys <<EOF
VAULT_UNSEAL_KEY=$UNSEAL_KEY
VAULT_ROOT_TOKEN=$ROOT_TOKEN
EOF

 chmod 600 vault/.vault-keys

 # Unsealer Vault
 echo ""
 echo "Déverrouillage de Vault..."
 docker exec orion_vault vault operator unseal $UNSEAL_KEY

 echo ""
 echo " Vault est maintenant déverrouillé et prêt"
 echo ""
 echo "Pour utiliser Vault, définissez ces variables d'environnement:"
 echo "export VAULT_ADDR=http://localhost:8200"
 echo "export VAULT_TOKEN=$ROOT_TOKEN"
 echo ""
 echo "Ou mettez à jour votre fichier .env:"
 echo "VAULT_ADDR=http://localhost:8200"
 echo "VAULT_ROOT_TOKEN=$ROOT_TOKEN"

else
 echo " Vault est déjà initialisé"
 echo ""
 echo "Si Vault est scellé, déverrouillez-le avec:"
 echo "docker exec orion_vault vault operator unseal <UNSEAL_KEY>"
 echo ""
 echo "Vos clés sont dans vault/.vault-keys"

 # Vérifier si on a les clés sauvegardées
 if [ -f vault/.vault-keys ]; then
 source vault/.vault-keys
 echo ""
 echo "Tentative de déverrouillage automatique..."
 docker exec orion_vault vault operator unseal $VAULT_UNSEAL_KEY

 if [ $? -eq 0 ]; then
 echo " Vault déverrouillé avec succès"
 fi
 fi
fi

echo ""
echo "=== Initialisation terminée ==="
