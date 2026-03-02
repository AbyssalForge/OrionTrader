#!/bin/sh

# Lancer Vault en arrière-plan
vault server -config=/vault/config/vault.hcl &
VAULT_PID=$!

# Attendre un peu que Vault démarre
sleep 5

# Vérifier si Vault est déjà initialisé
vault status 2>&1 | grep -q "Initialized.*false"
NOT_INITIALIZED=$?

if [ $NOT_INITIALIZED -eq 0 ]; then
 echo " Vault n'est pas initialisé - Initialisation automatique..."

 # Initialiser et sauvegarder les clés dans un fichier (dans le dossier data monté)
 vault operator init -key-shares=1 -key-threshold=1 > /vault/data/init-output.txt 2>&1

 if [ $? -eq 0 ]; then
 echo " Vault initialisé avec succès!"
 echo " Les clés sont sauvegardées dans vault/data/init-output.txt"
 echo ""
 echo " IMPORTANT: Copiez les clés suivantes dans votre fichier .env:"
 echo ""
 cat /vault/data/init-output.txt
 echo ""
 echo "Puis redémarrez Vault: docker-compose down vault && docker-compose up -d vault"
 else
 echo " Échec de l'initialisation de Vault"
 fi
else
 echo " Vault est déjà initialisé"

 # Lancer le script de déverrouillage automatique en arrière-plan
 if [ -f /vault/auto-unseal.sh ]; then
 sh /vault/auto-unseal.sh &
 fi
fi

# Attendre le processus Vault
wait $VAULT_PID
