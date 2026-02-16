"""
Helper simplifié pour accéder à HashiCorp Vault dans les notebooks Marimo
"""

import hvac
import os
from functools import lru_cache


class VaultHelper:
    """Helper pour simplifier l'accès à Vault dans les notebooks"""

    def __init__(self):
        """Initialise la connexion à Vault"""
        self.vault_addr = os.getenv('VAULT_ADDR')
        self.vault_token = os.getenv('VAULT_TOKEN')
        self.mount_point = os.getenv('VAULT_MOUNT', 'OrionTrader')

        print(f"[INFO] Vault Address: {self.vault_addr}")

        self.client = hvac.Client(
            url=self.vault_addr,
            token=self.vault_token
        )

        if not self.client.is_authenticated():
            raise Exception("Failed to authenticate with Vault")

    def get_secret(self, path: str, key: str = None):
        """
        Récupère un secret depuis Vault (KV v2)

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
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path, mount_point=self.mount_point
            )
            data = response['data']['data']

            if key:
                return data.get(key)
            return data

        except Exception as e:
            raise Exception(f"Failed to read secret at {path}: {str(e)}")

    def set_secret(self, path: str, **kwargs):
        """
        Crée ou met à jour un secret dans Vault (KV v2)

        Args:
            path: Chemin du secret
            **kwargs: Paires clé-valeur à stocker
        """
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=kwargs,
                mount_point=self.mount_point
            )
        except Exception as e:
            raise Exception(f"Failed to write secret at {path}: {str(e)}")

    def list_secrets(self, path: str = ''):
        """
        Liste les secrets à un chemin donné (KV v2)

        Args:
            path: Chemin à lister

        Returns:
            Liste des noms de secrets
        """
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path=path, mount_point=self.mount_point
            )
            return response['data']['keys']
        except Exception as e:
            raise Exception(f"Failed to list secrets at {path}: {str(e)}")


@lru_cache()
def get_vault() -> VaultHelper:
    """
    Retourne une instance singleton de VaultHelper

    Example dans un notebook:
        from vault_helper import get_vault

        vault = get_vault()
        creds = vault.get_secret('Database')
    """
    return VaultHelper()
