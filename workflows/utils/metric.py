import numpy as np
import matplotlib.pyplot as plt
from prefect import get_run_logger

def show_gain(actions_list, total_assets, env, show_plot=True):
    logger = get_run_logger()
    
    actions_list = np.array(actions_list)
    buy_points = np.where(actions_list > 0)[0]
    sell_points = np.where(actions_list < 0)[0]

    if show_plot:
        plt.figure(figsize=(12, 6))
        plt.plot(total_assets, label="Valeur du portefeuille", color="blue")
        plt.scatter(buy_points, np.array(total_assets)[buy_points], color="green", label="Achat", marker="^", alpha=0.8)
        plt.scatter(sell_points, np.array(total_assets)[sell_points], color="red", label="Vente", marker="v", alpha=0.8)
        plt.title("📈 Performance du modèle FinRL sur EUR/USD")
        plt.xlabel("Étapes (jours)")
        plt.ylabel("Valeur du portefeuille (€)")
        plt.legend()
        plt.grid(True)
        plt.show()

    initial = env.initial_capital
    final = env.total_asset
    gain_pct = (final / initial - 1) * 100

    logger.info(f"💰 Solde initial : {initial:.2f}")
    logger.info(f"💰 Solde final : {final:.2f}")
    logger.info(f"📈 Gain total : {gain_pct:.2f}%")
