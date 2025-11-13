import os, time
import pandas as pd
import MetaTrader5 as mt5
from prefect import get_run_logger

class MT5DataLoader:
    def __init__(self, symbol, timeframe, start, end, parquet_path, login, password, server):
        self.symbol = symbol
        self.timeframe = timeframe
        self.start = start
        self.end = end
        self.parquet_path = parquet_path
        self.login = login
        self.password = password
        self.server = server
        self.logger = get_run_logger()

    def connect(self, max_retries=3, wait_time=2):
        mt5.shutdown()
        time.sleep(1)
        for attempt in range(1, max_retries + 1):
            self.logger.info(f"Tentative {attempt}/{max_retries}")
            if not mt5.initialize():
                self.logger.error(f"Erreur MT5 : {mt5.last_error()}")
                time.sleep(wait_time)
                continue
            if self.login:
                if not mt5.login(login=self.login, password=self.password, server=self.server):
                    self.logger.error(f"Connexion échouée : {mt5.last_error()}")
                    mt5.shutdown(); time.sleep(wait_time)
                    continue
            self.logger.info("✅ Connexion MT5 réussie")
            return True
        self.logger.error("❌ Impossible de se connecter à MT5")
        return False

    def load_data(self):
        if os.path.exists(self.parquet_path):
            self.logger.info(f"📁 Chargement depuis {self.parquet_path}")
            df = pd.read_parquet(self.parquet_path)
        else:
            self.logger.info("🌐 Téléchargement depuis MT5...")
            if not self.connect(): raise RuntimeError("Impossible de se connecter à MT5")
            rates = mt5.copy_rates_range(self.symbol, self.timeframe, self.start.to_pydatetime(), self.end.to_pydatetime())
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.columns = df.columns.str.lower()
            os.makedirs(os.path.dirname(self.parquet_path), exist_ok=True)
            df.to_parquet(self.parquet_path, index=False)
            mt5.shutdown()
        df = df[["time","open","high","low","close"]].dropna().reset_index(drop=True)
        return df[df['time']<'2024-01-01'], df[df['time']>='2024-01-01']
