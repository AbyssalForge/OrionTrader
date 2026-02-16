"""
Configuration centralisée pour les sources de données
Utilise HashiCorp Vault pour récupérer les secrets
"""


class DataSourcesConfig:
    """Classe pour gérer les configurations des sources de données via Vault"""

    def __init__(self):
        # Import lazy pour éviter les dépendances circulaires
        from clients.vault_helper import get_vault
        self.vault = get_vault()

    # ==================== METATRADER 5 ====================

    def get_mt5_config(self) -> dict:
        """
        Récupère la configuration MetaTrader5 depuis Vault

        Returns:
            dict: Configuration MT5 (login, password, server)
        """
        return self.vault.get_secret('api/MetaTrader')

    def get_mt5_login(self) -> str:
        """Récupère le login MT5"""
        return self.vault.get_secret('api/MetaTrader', 'MT5_LOGIN')

    def get_mt5_password(self) -> str:
        """Récupère le mot de passe MT5"""
        return self.vault.get_secret('api/MetaTrader', 'MT5_PASSWORD')

    def get_mt5_server(self) -> str:
        """Récupère le serveur MT5"""
        return self.vault.get_secret('api/MetaTrader', 'MT5_SERVER')

    # ==================== YAHOO FINANCE ====================

    def get_yahoo_config(self) -> dict:
        """
        Récupère la configuration Yahoo Finance depuis Vault

        Returns:
            dict: Configuration Yahoo Finance (URL)
        """
        return self.vault.get_secret('Yahoo_finance')

    def get_yahoo_base_url(self) -> str:
        """Récupère l'URL de base pour Yahoo Finance"""
        return self.vault.get_secret('Yahoo_finance', 'URL')

    # ==================== EUROSTAT / SOURCES ECONOMIQUES ====================

    def get_eurostat_config(self) -> dict:
        """
        Récupère la configuration des sources économiques depuis Vault

        Returns:
            dict: Configuration Eurostat (URLs pour ECB, OECD, WorldBank, Investing)
        """
        return self.vault.get_secret('Eurostat')

    def get_ecb_url(self) -> str:
        """Récupère l'URL ECB pour le CPI"""
        return self.vault.get_secret('Eurostat', 'URL_ecb_eurozone_cpi')

    def get_oecd_url(self) -> str:
        """Récupère l'URL OECD"""
        return self.vault.get_secret('Eurostat', 'URL_oecd_eurozonne')

    def get_worldbank_url(self) -> str:
        """Récupère l'URL World Bank"""
        return self.vault.get_secret('Eurostat', 'URL_worldbank_eurozone_gdp')

    def get_investing_url(self) -> str:
        """Récupère l'URL Investing.com"""
        return self.vault.get_secret('Eurostat', 'URL_investing_economic_calendar')


# Singleton pour accès facile
_config_instance = None

def get_config() -> DataSourcesConfig:
    """
    Retourne une instance singleton de DataSourcesConfig

    Returns:
        DataSourcesConfig: Instance de configuration

    Example:
        from config.data_sources import get_config

        config = get_config()
        mt5_login = config.get_mt5_login()
        yahoo_url = config.get_yahoo_base_url()
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = DataSourcesConfig()
    return _config_instance
