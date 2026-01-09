"""
Module pour récupérer les données MT5 via FastAPI
=================================================

Version utilisant le serveur FastAPI au lieu de RPyC.
Plus simple, plus rapide pour gros volumes, plus facile à déboguer.

Usage:
    from utils.metatrader_data_fastapi import import_data

    df_train, df_test = import_data()
"""

import pandas as pd
import os
from clients.mt5_api_client import MT5APIClient, MT5Timeframe
from clients.vault_helper import get_vault


# Configuration
vault = get_vault()

SYMBOL = "EURUSD"
TIMEFRAME = MT5Timeframe.M15  # 15 minutes
START = "2023-01-01"
END = "2025-11-01"
PARQUET_PATH = f"data/{SYMBOL.lower()}_m15.parquet"

# Récupérer l'adresse du serveur API depuis Vault
MT5_API_HOST = vault.get_secret('MetaTrader', 'MT5_HOST')  # host.docker.internal
MT5_API_PORT = int(vault.get_secret('MetaTrader', 'MT5_PORT'))  # 8001


def import_data():
    """
    Télécharge les données depuis MT5 FastAPI ou charge depuis cache local.
    Retourne deux DataFrames: train et test

    Returns:
        tuple: (df_train, df_test)
    """

    # 🔹 Si fichier cache existe → le réutiliser
    if os.path.exists(PARQUET_PATH):
        print(f"📦 Chargement depuis le cache: {PARQUET_PATH}")
        df = pd.read_parquet(PARQUET_PATH)

    else:
        print(f"📥 Téléchargement depuis le serveur FastAPI MT5...")
        print(f"   Serveur: {MT5_API_HOST}:{MT5_API_PORT}")

        # Créer le client API
        client = MT5APIClient(host=MT5_API_HOST, port=MT5_API_PORT)

        # Vérifier que le serveur est accessible
        if not client.health_check():
            raise RuntimeError(
                f"❌ Impossible de se connecter au serveur MT5 FastAPI à {MT5_API_HOST}:{MT5_API_PORT}\n"
                f"   Assurez-vous que le serveur est démarré:\n"
                f"   python mt5_fastapi_server_optimized.py"
            )

        try:
            # Récupérer les données
            df = client.get_rates(
                symbol=SYMBOL,
                timeframe=TIMEFRAME,
                date_from=START,
                date_to=END,
                format="json"  # ou "msgpack" pour encore plus de vitesse
            )

            # Sauvegarder en cache
            print(f"💾 Sauvegarde en cache: {PARQUET_PATH}")
            os.makedirs(os.path.dirname(PARQUET_PATH), exist_ok=True)
            df.to_parquet(PARQUET_PATH, index=False)
            print(f"✅ Cache sauvegardé!")

        except Exception as e:
            raise RuntimeError(f"❌ Erreur lors du téléchargement: {e}")

    # 🔹 Garder seulement les colonnes nécessaires
    df = df[["time", "open", "high", "low", "close"]].dropna().reset_index(drop=True)

    print(f"✅ {len(df):,} barres chargées")

    # 🔹 Séparer en train / test
    split_date = pd.Timestamp("2024-01-01")

    df_train = df[df['time'] < split_date].reset_index(drop=True)
    df_test = df[df['time'] >= split_date].reset_index(drop=True)

    print(f"   📊 Train: {len(df_train):,} barres (avant {split_date.date()})")
    print(f"   📊 Test:  {len(df_test):,} barres (après {split_date.date()})")

    return df_train, df_test


def clear_cache():
    """Supprimer le cache pour forcer un nouveau téléchargement"""
    if os.path.exists(PARQUET_PATH):
        os.remove(PARQUET_PATH)
        print(f"🗑️  Cache supprimé: {PARQUET_PATH}")
    else:
        print(f"ℹ️  Aucun cache à supprimer")
