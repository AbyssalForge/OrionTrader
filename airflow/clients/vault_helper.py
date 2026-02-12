"""
Helper simplifié pour accéder à HashiCorp Vault dans Airflow
"""

import hvac
import os
from functools import lru_cache


class VaultHelper:
    """Helper pour simplifier l'accès à Vault dans vos DAGs"""

    def __init__(self):
        """Initialise la connexion à Vault"""
        self.vault_addr = os.getenv('VAULT_ADDR')
        self.vault_token = os.getenv('VAULT_TOKEN')
        self.mount_point = os.getenv('VAULT_MOUNT', 'secrets')
        self.path_prefix = os.getenv('VAULT_PATH_PREFIX', '')

        print(self.vault_addr)
        print(self.vault_token)

        self.client = hvac.Client(
            url=self.vault_addr,
            token=self.vault_token
        )

        if not self.client.is_authenticated():
            raise Exception("Failed to authenticate with Vault")

    def _full_path(self, path: str) -> str:
        """Construit le chemin complet avec le préfixe"""
        if self.path_prefix:
            return f"{self.path_prefix}/{path}"
        return path

    def get_secret(self, path: str, key: str = None):
        """
        Récupère un secret depuis Vault (KV v1)

        Args:
            path: Chemin du secret (ex: 'Database', 'api/binance')
            key: Clé spécifique (optionnel, retourne tout si None)

        Returns:
            La valeur du secret ou dict de toutes les valeurs

        Example:
            vault = get_vault()
            creds = vault.get_secret('Database')
            api_key = vault.get_secret('api/binance', 'api_key')
        """
        try:
            response = self.client.secrets.kv.v1.read_secret(
                path=self._full_path(path),
                mount_point=self.mount_point
            )
            data = response['data']

            if key:
                return data.get(key)
            return data

        except Exception as e:
            raise Exception(f"Failed to read secret at {path}: {str(e)}")

    def set_secret(self, path: str, **kwargs):
        """
        Crée ou met à jour un secret dans Vault (KV v1)

        Args:
            path: Chemin du secret (ex: 'airflow/last-run')
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
            self.client.secrets.kv.v1.create_or_update_secret(
                path=self._full_path(path),
                secret=kwargs,
                mount_point=self.mount_point
            )
        except Exception as e:
            raise Exception(f"Failed to write secret at {path}: {str(e)}")

    def list_secrets(self, path: str = ''):
        """
        Liste les secrets à un chemin donné (KV v1)

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
            response = self.client.secrets.kv.v1.list_secrets(
                path=self._full_path(path),
                mount_point=self.mount_point
            )
            return response['data']['keys']
        except Exception as e:
            raise Exception(f"Failed to list secrets at {path}: {str(e)}")


@lru_cache()
def get_vault() -> VaultHelper:
    """
    Retourne une instance singleton de VaultHelper

    Example dans un DAG:
        from clients.vault_helper import get_vault

        vault = get_vault()
        api_key = vault.get_secret('api/binance', 'api_key')
    """
    return VaultHelper()
