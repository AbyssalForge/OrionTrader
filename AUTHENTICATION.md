# 🔐 Authentification API - OrionTrader

Ce document explique comment utiliser le système d'authentification par API Token pour sécuriser l'accès à l'API FastAPI.

## 📋 Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Configuration](#configuration)
3. [Master Token (Méthode simple)](#master-token-méthode-simple)
4. [Tokens en base de données](#tokens-en-base-de-données)
5. [Intégration avec Streamlit](#intégration-avec-streamlit)

---

## 🎯 Vue d'ensemble

L'API supporte **deux modes d'authentification** :

### 1. Master Token (Recommandé pour commencer)

- Token défini dans le fichier `.env` via `FASTAPI_MASTER_TOKEN`
- Accès complet avec tous les droits (read, write, admin)
- Pas stocké en base de données
- Idéal pour le développement et l'administration

### 2. Database Tokens

- Tokens stockés dans la base de données `fastapi`
- Gérables via l'API `/auth/tokens`
- Différents niveaux de permissions (scopes)
- Idéal pour les services externes et la production

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Base de données                         │
├─────────────────────────┬───────────────────────────────────┤
│  postgres (trading)     │  fastapi (authentification)       │
│  - mt5_eurusd_m15       │  - api_tokens                     │
│  - yahoo_finance_daily  │                                   │
│  - documents_macro      │                                   │
│  - market_snapshot_m15  │                                   │
└─────────────────────────┴───────────────────────────────────┘

Client → Header: X-API-Key → FastAPI
                               ↓
                    1. Vérifie Master Token (.env)
                               ↓
                    2. Si non, cherche en DB fastapi
                               ↓
                    ✅ Valide → Accès autorisé
                    ❌ Invalide → 401 Unauthorized
```

---

## ⚙️ Configuration

### Variables d'environnement requises dans `.env`

```bash
# Base de données FastAPI (pour les tokens)
FASTAPI_DB_NAME=fastapi
FASTAPI_DB_USER=fastapi
FASTAPI_DB_PASSWORD=your_secure_password

# Master Token (token principal avec tous les droits)
FASTAPI_MASTER_TOKEN=your_secure_master_token_here_64_chars_minimum

# Token pour Streamlit (optionnel, peut utiliser le master token)
FASTAPI_API_TOKEN=your_token_for_streamlit
```

### Générer un token sécurisé

```bash
# Avec Python
python -c "import secrets; print(secrets.token_urlsafe(48)[:64])"

# Avec openssl
openssl rand -base64 48 | head -c 64
```

---

## 🔑 Master Token (Méthode simple)

### Étape 1 : Définir le Master Token

Dans votre fichier `.env` :

```bash
FASTAPI_MASTER_TOKEN=votre_token_super_securise_de_64_caracteres_minimum
```

### Étape 2 : Redémarrer FastAPI

```bash
docker-compose up -d --build fastapi
```

### Étape 3 : Utiliser le token

```bash
# Test de connexion
curl -H "X-API-Key: votre_token_super_securise_de_64_caracteres_minimum" \
     http://localhost:8000/market/latest
```

**C'est tout !** Le Master Token a automatiquement tous les droits (read, write, admin).

---

## 🗄️ Tokens en base de données

Pour une gestion plus fine des accès, vous pouvez créer des tokens en base de données.

### Prérequis : Créer la base de données `fastapi`

La base est créée automatiquement si vous avez les bonnes variables dans `.env`. Sinon :

```bash
# Recréer les containers postgres
docker-compose down
docker volume rm oriontrader_postgres-db-volume  # ⚠️ Supprime toutes les données !
docker-compose up -d postgres
```

### Créer la table et un premier token admin

```bash
docker exec -it orion_fastapi python create_tokens_table.py
```

**Sortie attendue** :
```
Création de la table api_tokens dans la base 'fastapi'...
✅ Table créée avec succès!

🎉 Token admin créé avec succès!
Nom: Admin Token (Default)
Token: abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx1234yzab5678cdef
```

### Créer un nouveau token via l'API

```bash
curl -X POST http://localhost:8000/auth/tokens \
  -H "X-API-Key: VOTRE_MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Streamlit Dashboard",
    "description": "Token pour le dashboard Streamlit",
    "scopes": "read,write"
  }'
```

### Lister tous les tokens

```bash
curl -H "X-API-Key: VOTRE_MASTER_TOKEN" http://localhost:8000/auth/tokens
```

### Révoquer un token

```bash
curl -X DELETE http://localhost:8000/auth/tokens/2 \
  -H "X-API-Key: VOTRE_MASTER_TOKEN"
```

---

## 📊 Intégration avec Streamlit

### Option 1 : Utiliser le Master Token (Simple)

Dans `.env` :
```bash
FASTAPI_MASTER_TOKEN=votre_master_token
FASTAPI_API_TOKEN=votre_master_token  # Même token pour Streamlit
```

### Option 2 : Token dédié pour Streamlit (Plus sécurisé)

1. **Créer un token dédié** :
```bash
curl -X POST http://localhost:8000/auth/tokens \
  -H "X-API-Key: VOTRE_MASTER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Streamlit Dashboard",
    "scopes": "read,write"
  }'
```

2. **Ajouter dans `.env`** :
```bash
FASTAPI_API_TOKEN=le_token_genere_pour_streamlit
```

3. **Redémarrer Streamlit** :
```bash
docker-compose up -d streamlit
```

---

## 🔒 Types de permissions (scopes)

| Scope | Description | Endpoints |
|-------|-------------|-----------|
| `read` | Lecture seule | GET /market/*, GET /data/*, GET /signals/* |
| `write` | Lecture + Écriture | POST /model/predict, POST /model/predict/batch |
| `admin` | Toutes les opérations | POST/GET/DELETE /auth/tokens |

**Exemples de combinaisons** :
- `read` : Tableaux de bord en lecture seule
- `read,write` : Applications de trading (recommandé pour Streamlit)
- `read,write,admin` : Administration complète

---

## 🚨 En cas de problème

### Erreur 401: "Token d'API manquant"

**Cause** : Header `X-API-Key` non fourni

**Solution** :
```bash
curl -H "X-API-Key: your_token" http://localhost:8000/endpoint
```

### Erreur 401: "Token d'API invalide"

**Cause** : Token incorrect ou inexistant

**Solution** :
- Vérifier que `FASTAPI_MASTER_TOKEN` est défini dans `.env`
- Ou créer un token en base de données

### Erreur lors de la connexion à la base "fastapi"

**Cause** : La base de données `fastapi` n'existe pas

**Solution** :
```bash
# Vérifier que les variables sont dans .env
FASTAPI_DB_NAME=fastapi
FASTAPI_DB_USER=fastapi
FASTAPI_DB_PASSWORD=fastapi

# Recréer les containers
docker-compose down
docker-compose up -d
```

---

## ✅ Checklist rapide

### Développement (Master Token)

- [x] Définir `FASTAPI_MASTER_TOKEN` dans `.env`
- [x] Définir `FASTAPI_API_TOKEN` dans `.env` (même valeur que master)
- [x] Redémarrer : `docker-compose up -d --build fastapi streamlit`
- [x] Tester : `curl -H "X-API-Key: TOKEN" http://localhost:8000/health`

### Production (Tokens séparés)

- [ ] Master Token généré et stocké en sécurité
- [ ] Base de données `fastapi` créée
- [ ] Tokens créés pour chaque service
- [ ] Streamlit utilise un token dédié (pas le master)
- [ ] Tokens de développement révoqués
- [ ] HTTPS activé

---

**🎉 Votre API est maintenant sécurisée !**
