import Pyro5.api
import MetaTrader5 as mt5
import pandas as pd
from utils.data_loader import import_data

@Pyro5.api.expose
class PriceServer:
    def get_last_tick(self, start=None, end=None, symbol="EURUSD"):
        """
        Récupère les données MT5 pour une période donnée.

        Args:
            start: Date de début (str ISO format ou None pour valeur par défaut)
            end: Date de fin (str ISO format ou None pour valeur par défaut)
            symbol: Symbole à récupérer (par défaut: EURUSD)

        Returns:
            dict: {"df": données au format dict}
        """
        print(f"[SERVER] Requête reçue - start: {start} (type: {type(start)})")
        print(f"[SERVER] Requête reçue - end: {end} (type: {type(end)})")

        # Convertir les dates ISO en Timestamp si fournies
        if start:
            start = pd.Timestamp(start)
            print(f"[SERVER] start converti: {start}")
        if end:
            end = pd.Timestamp(end)
            print(f"[SERVER] end converti: {end}")

        df = import_data(start=start, end=end, symbol=symbol)
        return {
            "df": df.to_dict(orient="list")
        }

daemon = Pyro5.api.Daemon(host="0.0.0.0", port=5000, nathost="host.docker.internal", natport=5000)
ns = Pyro5.api.locate_ns(host="127.0.0.1", port=9001)

uri = daemon.register(PriceServer)
ns.register("forex.server", uri)

print("Server registered as 'forex.server'")
daemon.requestLoop()
