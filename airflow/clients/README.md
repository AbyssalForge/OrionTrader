# Clients Module

Ce dossier contient les classes clientes pour interagir avec les services externes.

## Structure

- **mt5_api_client.py** - Client pour l'API MetaTrader 5 via FastAPI
  - `MT5APIClient`: Client HTTP pour communiquer avec le serveur MT5 FastAPI
  - `MT5Timeframe`: Constantes pour les timeframes MT5
  - `get_mt5_data()`: Fonction helper pour récupérer rapidement des données

- **mt5_client.py** - Client pour MetaTrader 5 via RPyC
  - `MT5Client`: Client pour communiquer avec MT5 via RPyC (remote procedure call)
  - `MT5Timeframe`: Constantes pour les timeframes MT5 (version RPyC)

- **vault_helper.py** - Client pour HashiCorp Vault
  - `VaultHelper`: Classe pour gérer les secrets avec Vault
  - `get_vault()`: Fonction singleton pour obtenir une instance de VaultHelper

## Usage

```python
# Import depuis clients
from clients.vault_helper import get_vault
from clients.mt5_api_client import MT5APIClient, MT5Timeframe
from clients.mt5_client import MT5Client

# Utiliser Vault
vault = get_vault()
api_key = vault.get_secret('MetaTrader', 'API_KEY')

# Utiliser MT5 API Client
client = MT5APIClient(host="localhost", port=8001)
df = client.get_rates("EURUSD", MT5Timeframe.M15, "2023-01-01", "2024-01-01")

# Utiliser MT5 RPyC Client
with MT5Client(host="metatrader5", port=8001) as client:
    client.initialize()
    rates = client.copy_rates_range("EURUSD", MT5Timeframe.M15, start, end)
```

## Différence avec utils/

- **clients/** contient les **classes** pour interagir avec les services externes
- **utils/** contient les **fonctions utilitaires** qui utilisent ces clients

Cette séparation améliore:
- La lisibilité du code
- La maintenabilité
- La réutilisabilité des composants
