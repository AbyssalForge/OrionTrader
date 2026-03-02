import os
import json
import numpy as np


def make_serializable(obj):
    """
    Convertit récursivement les objets non JSON-serializable en types standard.
    Exemple :
    - np.ndarray -> list
    - dict -> dict récursif
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    return obj


def save_best_config(best_params, config, path="artifacts/best_config.json"):
    """
    Sauvegarde les meilleurs hyperparamètres et la configuration de l'environnement
    dans un fichier JSON.
    
    Args:
        best_params (dict): Dictionnaire des meilleurs hyperparamètres (Optuna ou manuel)
        config (dict): Configuration de l'environnement (state, actions, reward, etc.)
        path (str): Chemin complet du fichier de sortie
    """
    serializable_config = make_serializable(config)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "best_params": best_params,
            "config": serializable_config
        }, f, indent=2, ensure_ascii=False)

    print(f"✅ Configuration sauvegardée : {path}")


def save_trained_model(model, metrics=None, base_path="models", model_name="orion_model"):
    """
    Sauvegarde le modèle entraîné et ses métriques éventuelles.
    
    Args:
        model: Modèle Stable-Baselines3 (PPO, A2C, DQN, etc.)
        metrics (dict, optional): Métriques à sauvegarder avec le modèle.
        base_path (str): Dossier de sauvegarde.
        model_name (str): Nom du fichier modèle.
    
    Returns:
        tuple: (model_path, metrics_path)
    """
    os.makedirs(base_path, exist_ok=True)

    model_path = os.path.join(base_path, f"{model_name}.zip")
    metrics_path = os.path.join(base_path, f"{model_name}_metrics.json")

    # Sauvegarde du modèle
    model.save(model_path)
    print(f"✅ Modèle sauvegardé : {model_path}")

    # Sauvegarde optionnelle des métriques
    if metrics:
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(make_serializable(metrics), f, indent=2, ensure_ascii=False)
        print(f"📊 Métriques sauvegardées : {metrics_path}")

    return model_path, metrics_path
