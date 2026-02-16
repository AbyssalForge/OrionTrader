"""
Client Python pour l'API MetaTrader5 FastAPI
=============================================

Ce module fournit un client simple pour interroger le serveur FastAPI MT5.
Il gère automatiquement la décompression et les différents formats.

Usage dans Airflow:
 from utils.mt5_api_client import MT5APIClient

 client = MT5APIClient(host="host.docker.internal", port=8001)
 df = client.get_rates("EURUSD", timeframe=16, date_from="2023-01-01", date_to="2025-11-01")
"""

import requests
import pandas as pd
import msgpack
from datetime import datetime
from typing import Optional, Dict, Any
import time


class MT5APIClient:
 """Client pour l'API MT5 FastAPI"""

 def __init__(self, host: str = "localhost", port: int = 8001, timeout: int = 300):
 """
 Initialiser le client API

 Args:
 host: Hostname du serveur (ex: "localhost", "host.docker.internal")
 port: Port du serveur (défaut: 8001)
 timeout: Timeout des requêtes en secondes (défaut: 300)
 """
 self.base_url = f"http://{host}:{port}"
 self.timeout = timeout
 self.session = requests.Session()
 # Activer la décompression automatique
 self.session.headers.update({"Accept-Encoding": "gzip"})

 def _get(self, endpoint: str, **params) -> requests.Response:
 """
 Effectuer une requête GET

 Args:
 endpoint: Endpoint API (ex: "/rates/EURUSD")
 **params: Paramètres query string

 Returns:
 Response object
 """
 url = f"{self.base_url}{endpoint}"

 try:
 response = self.session.get(url, params=params, timeout=self.timeout)
 response.raise_for_status()
 return response
 except requests.exceptions.Timeout:
 raise Exception(f"Timeout après {self.timeout}s")
 except requests.exceptions.ConnectionError:
 raise Exception(f"Impossible de se connecter à {self.base_url}")
 except requests.exceptions.HTTPError as e:
 raise Exception(f"Erreur HTTP {e.response.status_code}: {e.response.text}")

 def health_check(self) -> bool:
 """
 Vérifier que le serveur est accessible

 Returns:
 True si le serveur répond
 """
 try:
 response = self._get("/health")
 data = response.json()
 return data.get("status") == "healthy"
 except:
 return False

 def get_version(self) -> Dict[str, Any]:
 """Récupérer la version MT5"""
 response = self._get("/version")
 return response.json()

 def get_account(self) -> Dict[str, Any]:
 """Récupérer les informations du compte"""
 response = self._get("/account")
 return response.json()

 def get_symbols(self) -> list:
 """Récupérer la liste des symboles"""
 response = self._get("/symbols")
 data = response.json()
 return data.get("symbols", [])

 def get_tick(self, symbol: str) -> Dict[str, Any]:
 """Récupérer le dernier tick d'un symbole"""
 response = self._get(f"/tick/{symbol}")
 return response.json()

 def get_rates(
 self,
 symbol: str,
 timeframe: int,
 date_from: str,
 date_to: str,
 format: str = "json"
 ) -> pd.DataFrame:
 """
 Récupérer les données OHLC et les retourner sous forme de DataFrame

 Args:
 symbol: Symbole (ex: "EURUSD")
 timeframe: Timeframe MT5 (ex: 16 pour M15, voir MT5Timeframe)
 date_from: Date de début (format: "YYYY-MM-DD")
 date_to: Date de fin (format: "YYYY-MM-DD")
 format: Format de données ("json" ou "msgpack")

 Returns:
 DataFrame pandas avec colonnes: time, open, high, low, close, tick_volume, spread, real_volume

 Example:
 client = MT5APIClient(host="host.docker.internal")
 df = client.get_rates("EURUSD", 16, "2023-01-01", "2025-11-01")
 print(df.head())
 """
 print(f" Téléchargement {symbol} depuis {date_from} jusqu'à {date_to}...")

 start_time = time.time()

 # Faire la requête
 response = self._get(
 f"/rates/{symbol}",
 timeframe=timeframe,
 date_from=date_from,
 date_to=date_to,
 format=format,
 compress=True
 )

 # Parser selon le format
 if format == "msgpack":
 # Décoder msgpack
 data = msgpack.unpackb(response.content, raw=False)
 rates = data["data"]
 count = data["count"]
 else:
 # JSON (déjà décompressé automatiquement par requests)
 data = response.json()
 rates = data["data"]
 count = data["count"]

 # Créer le DataFrame
 df = pd.DataFrame(rates)

 # Convertir le timestamp en datetime
 df["time"] = pd.to_datetime(df["time"], unit="s")

 elapsed = time.time() - start_time
 size_mb = len(response.content) / (1024 * 1024)

 print(f" {count:,} barres téléchargées en {elapsed:.2f}s ({size_mb:.2f} MB)")

 return df


# Timeframes MT5 (constantes)
class MT5Timeframe:
 """Constantes pour les timeframes MT5"""
 M1 = 1 # 1 minute
 M2 = 2 # 2 minutes
 M3 = 3 # 3 minutes
 M4 = 4 # 4 minutes
 M5 = 5 # 5 minutes
 M6 = 6 # 6 minutes
 M10 = 10 # 10 minutes
 M12 = 12 # 12 minutes
 M15 = 16 # 15 minutes (attention: 16, pas 15!)
 M20 = 20 # 20 minutes
 M30 = 30 # 30 minutes
 H1 = 16385 # 1 heure
 H2 = 16386 # 2 heures
 H3 = 16387 # 3 heures
 H4 = 16388 # 4 heures
 H6 = 16390 # 6 heures
 H8 = 16392 # 8 heures
 H12 = 16396 # 12 heures
 D1 = 16408 # 1 jour
 W1 = 32769 # 1 semaine
 MN1 = 49153 # 1 mois


# Fonction helper pour faciliter l'utilisation
def get_mt5_data(
 symbol: str,
 timeframe: int,
 date_from: str,
 date_to: str,
 host: str = "host.docker.internal",
 port: int = 8001
) -> pd.DataFrame:
 """
 Fonction helper pour récupérer rapidement des données MT5

 Args:
 symbol: Symbole (ex: "EURUSD")
 timeframe: Timeframe (utiliser MT5Timeframe.M15, etc.)
 date_from: Date début "YYYY-MM-DD"
 date_to: Date fin "YYYY-MM-DD"
 host: Host du serveur API
 port: Port du serveur API

 Returns:
 DataFrame avec les données OHLC

 Example:
 df = get_mt5_data("EURUSD", MT5Timeframe.M15, "2023-01-01", "2025-11-01")
 """
 client = MT5APIClient(host=host, port=port)
 return client.get_rates(symbol, timeframe, date_from, date_to)
