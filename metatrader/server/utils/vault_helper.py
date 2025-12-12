"""
Helper simplifié pour accéder à HashiCorp Vault dans Airflow
"""

import hvac
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

class VaultHelper:
    """Helper pour simplifier l'accès à Vault dans vos DAGs"""

    def __init__(self):
        """Initialise la connexion à Vault"""
        self.vault_addr = os.getenv('VAULT_ADDR')
        self.vault_token = os.getenv('VAULT_ROOT_TOKEN')

        print(self.vault_addr)
        print(self.vault_token)

        self.client = hvac.Client(
            url=self.vault_addr,
            token=self.vault_token
        )

        if not self.client.is_authenticated():
            raise Exception("Failed to authenticate with Vault")

    def get_secret(self, path: str, key: str = None):
        """
        Récupère un secret depuis Vault

        Args:
            path: Chemin du secret (ex: 'api/binance')
            key: Clé spécifique (optionnel, retourne tout si None)

        Returns:
            La valeur du secret ou dict de toutes les valeurs

        Example:
            vault = get_vault()

            # Récupérer toutes les clés
            creds = vault.get_secret('api/binance')
            # {'api_key': '...', 'api_secret': '...'}

            # Récupérer une clé spécifique
            api_key = vault.get_secret('api/binance', 'api_key')
            # 'votre-clé'
        """
        try:
            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            data = response['data']['data']

            if key:
                return data.get(key)
            return data

        except Exception as e:
            raise Exception(f"Failed to read secret at {path}: {str(e)}")

    def set_secret(self, path: str, **kwargs):
        """
        Crée ou met à jour un secret dans Vault

        Args:
            path: Chemin du secret (ex: 'airflow/results')
            **kwargs: Paires clé-valeur à stocker

        Example:
            vault = get_vault()
            vault.set_secret('airflow/last-run',
                timestamp='2024-01-01',
                status='success',
                profit=1234.56
            )
        """
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=kwargs
            )
        except Exception as e:
            raise Exception(f"Failed to write secret at {path}: {str(e)}")

    def list_secrets(self, path: str = ''):
        """
        Liste les secrets à un chemin donné

        Args:
            path: Chemin à lister (ex: 'api')

        Returns:
            Liste des noms de secrets

        Example:
            vault = get_vault()
            secrets = vault.list_secrets('api')
            # ['binance', 'mt5', 'discord']
        """
        try:
            response = self.client.secrets.kv.v2.list_secrets(path=path)
            return response['data']['keys']
        except Exception as e:
            raise Exception(f"Failed to list secrets at {path}: {str(e)}")


@lru_cache()
def get_vault() -> VaultHelper:
    """
    Retourne une instance singleton de VaultHelper

    Example dans un DAG:
        from utils.vault_helper import get_vault

        def ma_fonction():
            vault = get_vault()
            api_key = vault.get_secret('api/binance', 'api_key')
            print(f"API Key: {api_key[:5]}...")
    """
    return VaultHelper()
