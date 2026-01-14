import pandas as pd
import Pyro5.api


def import_data(start, end):
    """
    Importe les données MT5 via Pyro5 pour une période donnée.

    Args:
        start: Date de début (datetime ou Timestamp)
        end: Date de fin (datetime ou Timestamp)

    Returns:
        dict: Données au format dict (colonnes: listes de valeurs)
    """
    ns = Pyro5.api.locate_ns(host="host.docker.internal", port=9001)
    uri = ns.lookup("forex.server")
    server = Pyro5.api.Proxy(uri)

    # Convertir les dates en string ISO pour le transfert Pyro5
    # Pyro5 ne peut pas sérialiser les objets datetime/Timestamp directement
    start_str = pd.Timestamp(start).isoformat()
    end_str = pd.Timestamp(end).isoformat()

    print(f"[MT5_SERVER] Envoi requête: {start_str} -> {end_str}")

    data = server.get_last_tick(start=start_str, end=end_str)

    return data["df"]