import Pyro5.api
import MetaTrader5 as mt5
from utils.data_loader import import_data

@Pyro5.api.expose
class PriceServer:
    def get_last_tick(self, symbol="EURUSD"):
        df = import_data()
        return {
            "df": df.to_dict(orient="list")
        }

daemon = Pyro5.api.Daemon(host="0.0.0.0", port=5000, nathost="host.docker.internal", natport=5000)
ns = Pyro5.api.locate_ns(host="127.0.0.1", port=9001)

uri = daemon.register(PriceServer)
ns.register("forex.server", uri)

print("Server registered as 'forex.server'")
daemon.requestLoop()
