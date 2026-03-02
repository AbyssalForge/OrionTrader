"""
Client MT5 pour se connecter au serveur MetaTrader5 via RPyC.
Utilisé par les DAGs Airflow pour accéder aux données de trading.
Utilise HashiCorp Vault pour récupérer les credentials.
"""
import os
import rpyc
from typing import Optional, List, Dict, Any
from datetime import datetime
from config.data_sources import get_config


class MT5Client:
    """Client pour interagir avec MetaTrader5 via RPyC."""

    def __init__(self, host: str = "metatrader5", port: int = 8001, use_vault: bool = True):
        """
        Initialise le client MT5.

        Args:
            host: Hostname du serveur MT5 (par défaut: metatrader5)
            port: Port du serveur RPyC (par défaut: 8001)
            use_vault: Utiliser Vault pour récupérer les credentials (par défaut: True)
        """
        self.host = host
        self.port = port
        self.connection = None
        self.mt5 = None
        self.use_vault = use_vault

        # Récupérer les credentials depuis Vault si activé
        if self.use_vault:
            config = get_config()
            self.credentials = config.get_mt5_config()
        else:
            self.credentials = None

    def connect(self):
        """Établit la connexion au serveur MT5."""
        if self.connection is None:
            print(f"Connecting to MT5 server at {self.host}:{self.port}...")
            self.connection = rpyc.connect(
                self.host,
                self.port,
                config={
                    'allow_public_attrs': True,
                    'sync_request_timeout': 300
                }
            )
            self.mt5 = self.connection.root
            print("Connected to MT5 server successfully!")
        return self

    def disconnect(self):
        """Ferme la connexion au serveur MT5."""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.mt5 = None
            print("Disconnected from MT5 server")

    def __enter__(self):
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()

    def initialize(self, login: Optional[int] = None,
                   password: Optional[str] = None,
                   server: Optional[str] = None) -> bool:
        """
        Initialise la connexion à MetaTrader5.
        Si les credentials ne sont pas fournis, utilise ceux de Vault.

        Args:
            login: Numéro de compte (optionnel, utilise Vault si non fourni)
            password: Mot de passe (optionnel, utilise Vault si non fourni)
            server: Serveur de trading (optionnel, utilise Vault si non fourni)

        Returns:
            True si succès, False sinon
        """
        if not self.connection:
            self.connect()

        # Utiliser les credentials de Vault si disponibles et non fournis
        if not (login and password and server) and self.credentials:
            login = login or int(self.credentials.get('MT5_LOGIN'))
            password = password or self.credentials.get('MT5_PASSWORD')
            server = server or self.credentials.get('MT5_SERVER')
            print(f"[MT5] Using credentials from Vault: {login}@{server}")

        if login and password and server:
            return self.mt5.initialize(login, password, server)
        return self.mt5.initialize()

    def version(self) -> tuple:
        """Retourne la version de MetaTrader5."""
        return self.mt5.version()

    def terminal_info(self) -> Optional[Dict]:
        """Retourne les informations du terminal."""
        return self.mt5.terminal_info()

    def account_info(self) -> Optional[Dict]:
        """Retourne les informations du compte."""
        return self.mt5.account_info()

    def symbols_get(self, group: str = "*") -> Optional[List[Dict]]:
        """
        Retourne la liste des symboles.

        Args:
            group: Groupe de symboles (par défaut: tous)

        Returns:
            Liste des symboles ou None
        """
        return self.mt5.symbols_get(group)

    def symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Retourne les informations d'un symbole.

        Args:
            symbol: Nom du symbole (ex: "EURUSD")

        Returns:
            Informations du symbole ou None
        """
        return self.mt5.symbol_info(symbol)

    def symbol_info_tick(self, symbol: str) -> Optional[Dict]:
        """
        Retourne le dernier tick d'un symbole.

        Args:
            symbol: Nom du symbole

        Returns:
            Dernières données de tick ou None
        """
        return self.mt5.symbol_info_tick(symbol)

    def copy_rates_from_pos(self, symbol: str, timeframe: int,
                            start_pos: int, count: int) -> Optional[List]:
        """
        Récupère les barres depuis une position.

        Args:
            symbol: Nom du symbole
            timeframe: Timeframe (ex: mt5.TIMEFRAME_H1)
            start_pos: Position de départ
            count: Nombre de barres

        Returns:
            Liste des barres ou None
        """
        return self.mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)

    def copy_rates_from(self, symbol: str, timeframe: int,
                        date_from: datetime, count: int) -> Optional[List]:
        """
        Récupère les barres depuis une date.

        Args:
            symbol: Nom du symbole
            timeframe: Timeframe
            date_from: Date de départ
            count: Nombre de barres

        Returns:
            Liste des barres ou None
        """
        return self.mt5.copy_rates_from(symbol, timeframe, date_from, count)

    def copy_rates_range(self, symbol: str, timeframe: int,
                        date_from: datetime, date_to: datetime) -> Optional[List]:
        """
        Récupère les barres dans une plage de dates.

        Args:
            symbol: Nom du symbole
            timeframe: Timeframe
            date_from: Date de début
            date_to: Date de fin

        Returns:
            Liste des barres ou None
        """
        return self.mt5.copy_rates_range(symbol, timeframe, date_from, date_to)

    def positions_get(self, symbol: Optional[str] = None,
                     group: Optional[str] = None,
                     ticket: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Retourne les positions ouvertes.

        Args:
            symbol: Filtrer par symbole (optionnel)
            group: Filtrer par groupe (optionnel)
            ticket: Filtrer par ticket (optionnel)

        Returns:
            Liste des positions ou None
        """
        return self.mt5.positions_get(symbol, group, ticket)

    def orders_get(self, symbol: Optional[str] = None,
                  group: Optional[str] = None,
                  ticket: Optional[int] = None) -> Optional[List[Dict]]:
        """
        Retourne les ordres actifs.

        Args:
            symbol: Filtrer par symbole (optionnel)
            group: Filtrer par groupe (optionnel)
            ticket: Filtrer par ticket (optionnel)

        Returns:
            Liste des ordres ou None
        """
        return self.mt5.orders_get(symbol, group, ticket)

    def history_deals_get(self, date_from: datetime, date_to: datetime,
                         group: Optional[str] = None) -> Optional[List[Dict]]:
        """
        Retourne les deals de l'historique.

        Args:
            date_from: Date de début
            date_to: Date de fin
            group: Filtrer par groupe (optionnel)

        Returns:
            Liste des deals ou None
        """
        return self.mt5.history_deals_get(date_from, date_to, group)

    def history_orders_get(self, date_from: datetime, date_to: datetime,
                          group: Optional[str] = None) -> Optional[List[Dict]]:
        """
        Retourne les ordres de l'historique.

        Args:
            date_from: Date de début
            date_to: Date de fin
            group: Filtrer par groupe (optionnel)

        Returns:
            Liste des ordres ou None
        """
        return self.mt5.history_orders_get(date_from, date_to, group)

    def order_send(self, request: Dict) -> Optional[Dict]:
        """
        Envoie un ordre de trading.

        Args:
            request: Dictionnaire contenant les paramètres de l'ordre

        Returns:
            Résultat de l'ordre ou None
        """
        return self.mt5.order_send(request)

    def order_check(self, request: Dict) -> Optional[Dict]:
        """
        Vérifie un ordre de trading sans l'envoyer.

        Args:
            request: Dictionnaire contenant les paramètres de l'ordre

        Returns:
            Résultat de la vérification ou None
        """
        return self.mt5.order_check(request)

    def last_error(self) -> tuple:
        """Retourne la dernière erreur."""
        return self.mt5.last_error()


# Constantes de timeframe (pour référence)
class MT5Timeframe:
    """Constantes pour les timeframes MetaTrader5."""
    M1 = 1          # 1 minute
    M2 = 2          # 2 minutes
    M3 = 3          # 3 minutes
    M4 = 4          # 4 minutes
    M5 = 5          # 5 minutes
    M6 = 6          # 6 minutes
    M10 = 10        # 10 minutes
    M12 = 12        # 12 minutes
    M15 = 15        # 15 minutes
    M20 = 20        # 20 minutes
    M30 = 30        # 30 minutes
    H1 = 16385      # 1 heure
    H2 = 16386      # 2 heures
    H3 = 16387      # 3 heures
    H4 = 16388      # 4 heures
    H6 = 16390      # 6 heures
    H8 = 16392      # 8 heures
    H12 = 16396     # 12 heures
    D1 = 16408      # 1 jour
    W1 = 32769      # 1 semaine
    MN1 = 49153     # 1 mois
