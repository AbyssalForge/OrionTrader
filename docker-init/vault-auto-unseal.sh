#!/bin/sh

# Script de déverrouillage automatique de Vault au démarrage
# Ce script attend que Vault soit prêt puis le déverrouille automatiquement

echo "Attente du démarrage de Vault..."
sleep 5

# Vérifier si VAULT_UNSEAL_KEY est déjà défini (via docker-compose env)
if [ -z "$VAULT_UNSEAL_KEY" ]; then
    # Sinon, essayer de charger depuis vault/.vault-keys
    if [ -f /vault/.vault-keys ]; then
        . /vault/.vault-keys
    else
        echo "⚠ VAULT_UNSEAL_KEY non défini - Vault ne sera pas déverrouillé automatiquement"
        exit 0
    fi
fi

# Vérifier que la variable est maintenant définie
if [ -z "$VAULT_UNSEAL_KEY" ]; then
    echo "⚠ VAULT_UNSEAL_KEY non défini - impossible de déverrouiller Vault"
    exit 0
fi

echo "✓ Clé de déverrouillage trouvée"

# Attendre que Vault soit accessible (scellé ou non)
i=1
while [ $i -le 30 ]; do
    # vault status retourne 0 si unsealed, 2 si sealed, autre si non accessible
    vault status >/dev/null 2>&1
    STATUS=$?
    if [ $STATUS -eq 0 ] || [ $STATUS -eq 2 ]; then
        echo "✓ Vault est accessible"
        break
    fi
    echo "En attente de Vault... ($i/30)"
    sleep 2
    i=$((i + 1))
done

# Vérifier si Vault est scellé
vault status 2>&1 | grep -q "Sealed.*true"
IS_SEALED=$?

if [ $IS_SEALED -eq 0 ]; then
    echo "Déverrouillage de Vault..."
    vault operator unseal "$VAULT_UNSEAL_KEY"

    if [ $? -eq 0 ]; then
        echo "✓ Vault déverrouillé avec succès"
    else
        echo "✗ Échec du déverrouillage de Vault"
        exit 1
    fi
else
    echo "✓ Vault est déjà déverrouillé"
fi
