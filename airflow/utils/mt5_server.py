import pandas as pd
import Pyro5.api




#print(len(df_train))
#print(len(df_test))

def import_data():
    ns = Pyro5.api.locate_ns(host="host.docker.internal", port=9001)
    uri = ns.lookup("forex.server")
    server = Pyro5.api.Proxy(uri)

    data = server.get_last_tick()

    #df_train = pd.DataFrame(data["df_train"])
    #df_test = pd.DataFrame(data["df_test"])

    return(data["df"])