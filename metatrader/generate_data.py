import os
import time
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
import MetaTrader5 as mt5


class MT5DataLoader:
    """
    Classe pour charger des données MT5 et les sauvegarder en format Parquet.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: int,
        start: datetime,
        end: datetime,
        output_dir: str = "airflow/data",
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None
    ):
        """
        Args:
            symbol: Symbole à télècharger (ex: "EURUSD")
            timeframe: Timeframe MT5 (ex: mt5.TIMEFRAME_H1)
            start: Date de début (datetime)
            end: Date de fin (datetime)
            output_dir: Dossier de sortie pour les fichiers parquet
            login: Login MT5 (optionnel)
            password: Mot de passe MT5 (optionnel)
            server: Serveur MT5 (optionnel)
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.start = pd.Timestamp(start)
        self.end = pd.Timestamp(end)
        self.output_dir = output_dir
        self.login = login
        self.password = password
        self.server = server

        # Cr�er le nom du fichier parquet
        timeframe_name = self._get_timeframe_name(timeframe)
        self.parquet_path = os.path.join(
            output_dir,
            f"{symbol}_{timeframe_name}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.parquet"
        )

    def _get_timeframe_name(self, timeframe: int) -> str:
        """Convertit le timeframe MT5 en nom lisible."""
        timeframe_map = {
            mt5.TIMEFRAME_M1: "M1",
            mt5.TIMEFRAME_M5: "M5",
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30",
            mt5.TIMEFRAME_H1: "H1",
            mt5.TIMEFRAME_H4: "H4",
            mt5.TIMEFRAME_D1: "D1",
            mt5.TIMEFRAME_W1: "W1",
            mt5.TIMEFRAME_MN1: "MN1",
        }
        return timeframe_map.get(timeframe, f"TF{timeframe}")

    def connect(self, max_retries: int = 3, wait_time: int = 2) -> bool:
        """
        Connexion à MT5 avec gestion des tentatives.

        Args:
            max_retries: Nombre maximum de tentatives
            wait_time: Temps d'attente entre les tentatives (secondes)

        Returns:
            True si la connexion réussit, False sinon
        """
        mt5.shutdown()
        time.sleep(1)

        for attempt in range(1, max_retries + 1):
            print(f"Tentative {attempt}/{max_retries}")

            if not mt5.initialize():
                print(f"Erreur MT5 : {mt5.last_error()}")
                time.sleep(wait_time)
                continue

            if self.login:
                if not mt5.login(
                    login=self.login,
                    password=self.password,
                    server=self.server
                ):
                    print(f"Connexion échouée : {mt5.last_error()}")
                    mt5.shutdown()
                    time.sleep(wait_time)
                    continue

            print(" Connexion MT5 réussie")
            return True

        print("L Impossible de se connecter à MT5")
        return False

    def load_data(self, force_download: bool = False) -> pd.DataFrame:
        """
        Charge les données depuis le cache parquet ou MT5.

        Args:
            force_download: Force le t�l�chargement m�me si le fichier existe

        Returns:
            DataFrame avec les colonnes: time, open, high, low, close
        """
        if os.path.exists(self.parquet_path) and not force_download:
            print(f"=� Chargement depuis {self.parquet_path}")
            df = pd.read_parquet(self.parquet_path)
        else:
            print("<T�l�chargement depuis MT5...")
            if not self.connect():
                raise RuntimeError("Impossible de se connecter � MT5")

            rates = mt5.copy_rates_range(
                self.symbol,
                self.timeframe,
                self.start.to_pydatetime(),
                self.end.to_pydatetime()
            )

            if rates is None or len(rates) == 0:
                mt5.shutdown()
                raise ValueError(f"Aucune donn�e re�ue pour {self.symbol}")

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.columns = df.columns.str.lower()

            # Sauvegarder dans le cache
            os.makedirs(os.path.dirname(self.parquet_path), exist_ok=True)
            df.to_parquet(self.parquet_path, index=False)
            print(f"=� Donn�es sauvegard�es dans {self.parquet_path}")

            mt5.shutdown()

        # Nettoyer les donn�es
        print(f"colonne: {df.columns}")
        df = df.dropna().reset_index(drop=True)
        return df

    def load_and_split(
        self,
        split_date: datetime,
        force_download: bool = False
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Charge les donn�es et les split en train/test.

        Args:
            split_date: Date de s�paration train/test
            force_download: Force le t�l�chargement

        Returns:
            Tuple (df_train, df_test)
        """
        df = self.load_data(force_download=force_download)
        split_date = pd.Timestamp(split_date)

        df_train = df[df['time'] < split_date].reset_index(drop=True)
        df_test = df[df['time'] >= split_date].reset_index(drop=True)

        print(f"=� Train: {len(df_train)} lignes | Test: {len(df_test)} lignes")

        return df_train, df_test


def generate_data(
    symbol: str = "EURUSD",
    timeframe: int = mt5.TIMEFRAME_H1,
    start: str = "2020-01-01",
    end: str = "2024-12-31",
    output_dir: str = "airflow/data",
    login: Optional[int] = None,
    password: Optional[str] = None,
    server: Optional[str] = None,
    force_download: bool = False
) -> str:
    """
    Fonction helper pour g�n�rer rapidement des donn�es.

    Args:
        symbol: Symbole � t�l�charger
        timeframe: Timeframe MT5
        start: Date de d�but (format: "YYYY-MM-DD")
        end: Date de fin (format: "YYYY-MM-DD")
        output_dir: Dossier de sortie
        login: Login MT5
        password: Mot de passe MT5
        server: Serveur MT5
        force_download: Force le t�l�chargement

    Returns:
        Chemin du fichier parquet g�n�r�

    Example:
        parquet_file = generate_data(
            symbol="EURUSD",
            start="2023-01-01",
            end="2024-01-01",
            timeframe=mt5.TIMEFRAME_H1
        )
    """
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    end_dt = datetime.strptime(end, "%Y-%m-%d")

    loader = MT5DataLoader(
        symbol=symbol,
        timeframe=timeframe,
        start=start_dt,
        end=end_dt,
        output_dir=output_dir,
        login=login,
        password=password,
        server=server
    )

    loader.load_data(force_download=force_download)
    return loader.parquet_path


if __name__ == "__main__":
    
    print("Generate trading data...")

    parquet_file = generate_data(
        symbol="EURUSD",
        timeframe=mt5.TIMEFRAME_M15,
        start="2023-01-01",
        end="2024-01-01",
        output_dir="airflow/data"
    )
    print(f"file generate: {parquet_file}")