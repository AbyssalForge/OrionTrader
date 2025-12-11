# 🛰️ OrionTrader

🧠 Architecture du Projet OrionTrader (Forex RL + ML)

La solution utilise 3 modèles complémentaires, chacun spécialisé dans une tâche précise.

1️⃣ Modèle ML de Classification → "Doit-on trader ?"

🎯 Rôle : Filtrer les trades
Évite de trader dans les zones où le marché est :

trop neutre

trop bruité

sans tendance

vol faible / spread trop large

risque de faux-signaux

📘 Type de modèle :

LightGBMClassifier (recommandé)

ou XGBoostClassifier

ou CatBoost (bon pour données non normalisées)

📤 Sortie du modèle :

prob_buy

prob_sell

prob_hold

label_final = argmax(prob)
(ou seuils de confiance)

📌 Entrée :
➡️ tes 100+ features (MAs, RSI, volatility, microstructure…)
➡️ labels générés via future return labeling

2️⃣ Modèle ML de Régression → "Quelle amplitude du mouvement ?"

🎯 Rôle : prédire les cibles futures
Ce modèle ne décide pas d’acheter/vendre, mais prédit le potentiel du mouvement :

📤 Sorties :

volatility_future

expected_return (target en pips)

expected_duration

éventuellement profit_ratio

📘 Type de modèle :

LightGBMRegressor (le plus robuste FX)

ou XGBoostRegressor

ou un petit réseau MLP 2-3 couches

📌 Entrée :
➡️ les mêmes features que le classif
➡️ labels comme future_return, future_volatility

📌 Utilité :

si volatilité prévue < seuil → pas de trade

si target < spread → pas de trade

RL utilise ça pour le sizing dynamique

3️⃣ Modèle RL (Reinforcement Learning) → "Gestion des trades"

🎯 C’est le cerveau du trader.
Il prend les décisions finales :

📤 Actions du RL :

Buy

Sell

Hold

Close trade

Increase size (+)

Decrease size (-)

📘 Algorithme RL recommandé :

PPO (Stable-Baselines3) → stable, robuste

OU SAC (si tu veux actions continues pour sizing)

OU TD3 (actions continues, volatilité stable)

📌 Entrée :

features du marché

sorties (ou encapsulation) des 2 modèles ML :

prob_buy / prob_sell / prob_hold

expected_return (régression)

expected_volatility

position actuelle

pnl

spread

etc.

📌 Reward :

profit normalisé par volatilité

pénalité overtrading

pénalité position trop grosse

récompense bonne sortie

🎯 Vision d’ensemble (architecture complète)

```
          ┌────────────────────────────┐
          │      Données Forex         │
          │  ticks → features (100+)   │
          └───────────────┬────────────┘
                          ▼
           ┌──────────────────────────┐
           │ ML Classification         │
           │ BUY / SELL / HOLD        │
           └──────────────┬───────────┘
                          ▼
           ┌──────────────────────────┐
           │ ML Régression             │
           │ volatilité & target       │
           └──────────────┬───────────┘
                          ▼
                +─────────┴─────────+
                |                   |
                ▼                   ▼
        Features marché       Conseils ML
                \              /
                 \            /
                  \          /
                   ▼        ▼
             ┌───────────────────┐
             │        RL          │
             │ Gestion des trades │
             └───────────────────┘
                     │
                     ▼
             Exécute sur MetaTrader5

```

## 💱 FOREX = Foreign Exchange (marché des devises)

Le ForeX est le marché mondial où s’échangent les monnaies, par exemple :

EUR → USD

USD → JPY

GBP → USD

etc.

C’est le plus grand marché financier du monde :
👉 + 7 500 milliards de dollars échangés chaque jour
(plus que les actions, crypto, obligations… réunis).

🧠 Comment ça fonctionne ?

Quand tu trades sur le Forex, tu ne traites jamais une seule devise.
Tu trades toujours une paire, par exemple :

EURUSD

Tu achètes l’euro contre le dollar.

Si tu achètes EURUSD :
👉 tu paries que l'Euro va monter par rapport au Dollar

Si tu vends EURUSD :
👉 tu paries que l'Euro va baisser par rapport au Dollar

---

## 🔐 Gestion des Secrets avec HashiCorp Vault

OrionTrader utilise **HashiCorp Vault** pour gérer de manière sécurisée tous les secrets et clés API.

### Services configurés

- **Vault UI**: http://localhost:8200/ui
- **Token Root**: `orion-root-token` (configurable via `.env`)
- **Policies**: Accès contrôlé pour Airflow et FastAPI

### Démarrage rapide

```bash
# 1. Démarrer Vault
docker-compose up -d vault

# 2. Initialiser (créer policies et tokens)
./init-vault.sh

# 3. Créer vos secrets via l'UI Web
# → http://localhost:8200/ui (token: orion-root-token)
```

### Documentation et exemples

- 📖 [VAULT_QUICKSTART.md](VAULT_QUICKSTART.md) - Guide complet d'utilisation
- 💻 [airflow/dags/example_vault_usage.py](airflow/dags/example_vault_usage.py) - Exemple de DAG
- 🔐 [vault/examples/](vault/examples/) - Exemples de code Python

### Utilisation dans un DAG Airflow

```python
import hvac
import os

def ma_fonction():
    # Se connecter à Vault
    client = hvac.Client(
        url='http://vault:8200',
        token=os.getenv('VAULT_TOKEN', 'orion-root-token')
    )

    # Lire un secret
    secret = client.secrets.kv.v2.read_secret_version(path='api/binance')
    api_key = secret['data']['data']['api_key']

    # Utiliser la clé
    print(f"API Key: {api_key[:5]}...")
```

⚠️ **Note**: Configuration en mode développement. Pour la production, désactiver le mode `-dev` et activer TLS.