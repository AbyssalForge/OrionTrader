import matplotlib.pyplot as plt
from .test_model import test_action_model
import matplotlib.pyplot as plt
import tempfile
import mlflow

def evaluate_model(model, config):
    """
    Évalue les performances d’un modèle entraîné sur un environnement de trading.

    Args:
        model: modèle RL (PPO ou autre)
        config (dict): configuration contenant price_array, tech_array, turbulence_array...

    Returns:
        tuple: (actions_list, total_assets, env_test)
    """
    # Exécute ton test déjà défini dans test_model.py
    actions_list, total_assets, env_test = test_action_model(model, config)

    # Log simple côté console pour suivi (utile si lancé sans Prefect)
    print("=== Résultats du test ===")
    print(f"💰 Solde initial : {env_test.initial_capital:.2f}")
    print(f"💰 Solde final   : {env_test.total_asset:.2f}")
    print(f"📈 Gain total    : {(env_test.total_asset/env_test.initial_capital - 1)*100:.2f}%")

    return actions_list, total_assets, env_test


def show_gain(actions_list, total_assets, env_test, show_plot=True):
    """
    Affiche ou trace les gains réalisés pendant le test.

    Args:
        actions_list (list): actions effectuées par le modèle (buy/sell/hold)
        total_assets (list): évolution du portefeuille dans le temps
        env_test: environnement de test (pour contexte)
        show_plot (bool): afficher ou non le graphique
    """   
    gain_pct = (env_test.total_asset / env_test.initial_capital - 1) * 100

    plt.figure(figsize=(10, 5))
    plt.plot(total_assets, label="Valeur du portefeuille", linewidth=2)
    plt.title(f"Performance du modèle — Gain total : {(env_test.total_asset/env_test.initial_capital - 1)*100:.2f}%")
    plt.xlabel("Période")
    plt.ylabel("Valeur (USD)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
        plt.savefig(tmpfile.name)
        mlflow.log_artifact(tmpfile.name, artifact_path="plots")
    
    mlflow.log_metric("final_gain", gain_pct)
    
    if show_plot:
        plt.show()
    plt.close()