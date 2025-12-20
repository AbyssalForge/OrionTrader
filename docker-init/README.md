# Scripts d'initialisation Docker - OrionTrader

Ce dossier `docker-init` contient tous les scripts d'initialisation et de configuration des conteneurs Docker du projet.

## Scripts PostgreSQL

### `init-db.sh`
Script d'initialisation de la base de données PostgreSQL. S'exécute automatiquement au premier démarrage du conteneur PostgreSQL.

**Fonctionnalités:**
- Crée les bases de données nécessaires (Airflow, MLflow)
- Configure les utilisateurs et permissions

### `init-postgres.sh`
Script post-initialisation pour finaliser la configuration PostgreSQL.

**Fonctionnalités:**
- Vérifie que les bases de données sont créées
- Configure les paramètres supplémentaires
- S'exécute via le service `postgres-init` dans docker-compose

## Scripts Vault

### `setup-vault-keys.sh`
Crée le fichier `vault/.vault-keys` s'il n'existe pas (prévient la création d'un dossier par Docker).

**Usage :**
```bash
bash docker-init/setup-vault-keys.sh
```

### `init-vault-production.sh`
Initialise Vault en mode production et génère les clés d'accès.

**Usage (première initialisation) :**

⚠️ **IMPORTANT** : Le fichier `vault/.vault-keys` doit **exister AVANT** de démarrer Docker, sinon Docker créera un dossier au lieu d'un fichier.

```bash
# 1. S'assurer que vault/.vault-keys existe (copier depuis le template)
cp vault/.vault-keys.example vault/.vault-keys

# 2. Démarrer Vault
docker-compose up -d vault

# 3. Attendre 5 secondes puis initialiser
sleep 5
docker exec orion_vault vault operator init -key-shares=1 -key-threshold=1

# 4. Copier les clés affichées dans vault/.vault-keys
nano vault/.vault-keys
# Remplacer les valeurs par celles affichées

# 5. Mettre à jour le token dans .env
nano .env
# VAULT_ROOT_TOKEN=<votre_token>

# 6. Redémarrer Vault (il se déverrouillera automatiquement)
docker-compose restart vault
```

### `vault-entrypoint.sh`
Script d'entrée pour le conteneur Vault. Lance Vault et le script de déverrouillage automatique.

### `vault-auto-unseal.sh`
Déverrouille automatiquement Vault au démarrage en utilisant les clés dans `vault/.vault-keys`.

## ⚠️ IMPORTANT

### Fichiers sensibles
- `vault/.vault-keys` : **NE JAMAIS COMMITTER** - Contient les clés de déverrouillage Vault
- `vault/.vault-keys.example` : **À COMMITTER** - Template vide pour créer .vault-keys
- `.env` : **NE JAMAIS COMMITTER** - Contient le token root Vault

Ces fichiers sont protégés par `.gitignore`.

### Sauvegarde des clés
**Sauvegardez vos clés Vault dans un endroit sûr** (gestionnaire de mots de passe, coffre-fort numérique) :
- Sans la `VAULT_UNSEAL_KEY`, vous ne pourrez plus déverrouiller Vault
- Sans le `VAULT_ROOT_TOKEN`, vous ne pourrez plus accéder aux secrets

## Utilisation quotidienne

Une fois Vault initialisé, le déverrouillage est automatique :

```bash
# Démarrer tous les services
docker-compose up -d --build

# Vault se déverrouille automatiquement grâce aux scripts
# Vérifier que Vault est déverrouillé
docker exec orion_vault vault status
```

## Accès à Vault

- **UI Web** : http://localhost:8200/ui
- **Token** : Celui défini dans `.env` (variable `VAULT_ROOT_TOKEN`)

## ⚠️ IMPORTANT : Redémarrage de Vault

**NE JAMAIS utiliser `docker restart orion_vault`** car cela transforme `.vault-keys` en dossier !

**Toujours utiliser** :
```bash
docker-compose down vault
docker-compose up -d vault
```

Ou utilisez le script helper :
```bash
bash docker-init/restart-vault.sh
```

## Résolution de problèmes

### Le fichier .vault-keys se transforme en dossier
Cela arrive si vous utilisez `docker restart`. Solution :

```bash
# 1. Arrêter Vault
docker-compose down vault

# 2. Supprimer le dossier
rm -rf vault/.vault-keys

# 3. Créer le fichier depuis le template
cp vault/.vault-keys.example vault/.vault-keys

# 4. Remplir avec vos clés
nano vault/.vault-keys

# 5. Redémarrer
docker-compose up -d vault
```

### Vault ne se déverrouille pas automatiquement
Vérifiez que `vault/.vault-keys` contient les bonnes clés :
```bash
cat vault/.vault-keys
```
