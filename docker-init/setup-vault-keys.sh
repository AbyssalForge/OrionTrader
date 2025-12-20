#!/bin/bash

# Script pour créer le fichier .vault-keys si nécessaire
# À exécuter AVANT le premier démarrage de Vault

VAULT_KEYS_FILE="vault/.vault-keys"

echo "=== Configuration des clés Vault ==="

# Vérifier si le fichier existe et est bien un fichier (pas un dossier)
if [ -d "$VAULT_KEYS_FILE" ]; then
    echo "⚠️  $VAULT_KEYS_FILE est un dossier, suppression..."
    rm -rf "$VAULT_KEYS_FILE"
fi

if [ ! -f "$VAULT_KEYS_FILE" ]; then
    echo "📝 Création du fichier $VAULT_KEYS_FILE..."
    touch "$VAULT_KEYS_FILE"
    echo "✓ Fichier créé"
    echo ""
    echo "⚠️  Le fichier est vide. Vous devez le remplir avec vos clés Vault :"
    echo "   VAULT_UNSEAL_KEY=votre_clé_unseal"
    echo "   VAULT_ROOT_TOKEN=votre_token_root"
    echo ""
    echo "Pour initialiser Vault, exécutez :"
    echo "   1. docker-compose up -d vault"
    echo "   2. docker exec orion_vault vault operator init -key-shares=1 -key-threshold=1"
    echo "   3. Copiez les clés dans $VAULT_KEYS_FILE"
    echo "   4. docker-compose restart vault"
else
    echo "✓ Le fichier $VAULT_KEYS_FILE existe déjà"

    # Vérifier si le fichier contient les clés
    if grep -q "VAULT_UNSEAL_KEY" "$VAULT_KEYS_FILE" && grep -q "VAULT_ROOT_TOKEN" "$VAULT_KEYS_FILE"; then
        echo "✓ Le fichier contient les clés Vault"
    else
        echo "⚠️  Le fichier existe mais ne contient pas les clés nécessaires"
        echo "   Ajoutez les clés suivantes :"
        echo "   VAULT_UNSEAL_KEY=votre_clé_unseal"
        echo "   VAULT_ROOT_TOKEN=votre_token_root"
    fi
fi

echo ""
echo "=== Configuration terminée ==="
