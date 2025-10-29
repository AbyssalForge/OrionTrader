import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
import os

MODEL_PATH = "models/metatrader_ppo_final.zip"

class TradingAgent:
    def __init__(self, env):
        self.env = env
        self.model = None
        self.load_model()

    def load_model(self):
        if os.path.exists(MODEL_PATH):
            print("✅ Chargement du modèle RL existant...")
            self.model = PPO.load(MODEL_PATH, env=self.env)
        else:
            print("⚙️ Création d’un nouveau modèle PPO...")
            self.model = PPO("MlpPolicy", self.env, verbose=1)

    def predict(self, observation):
        obs = np.array(observation).reshape(1, -1)
        action, _ = self.model.predict(obs, deterministic=True)
        return int(action)

    def retrain(self, total_timesteps=10_000):
        print(f"🔄 Réentraînement du modèle sur {total_timesteps} pas de temps...")
        self.model.learn(total_timesteps=total_timesteps)
        self.model.save(MODEL_PATH)
        print("💾 Modèle sauvegardé avec succès.")
        return {"status": "Model retrained", "timesteps": total_timesteps}
