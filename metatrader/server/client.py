import pandas as pd
import Pyro5.api

ns = Pyro5.api.locate_ns(port=9001)
uri = ns.lookup("forex.server")
server = Pyro5.api.Proxy(uri)

data = server.get_last_tick()

#df_train = pd.DataFrame(data["df_train"])
#df_test = pd.DataFrame(data["df_test"])

print(len(data["df_train"]))

#print(len(df_train))
#print(len(df_test))