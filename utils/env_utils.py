import gymnasium as gym
from gymnasium import spaces
import numpy as np

class DummyTradingEnv(gym.Env):
    """Petit environnement de test compatible Gymnasium pour PPO."""
    metadata = {"render_modes": []}

    def __init__(self):
        super().__init__()
        self.observation_space = spaces.Box(low=-1, high=1, shape=(5,), dtype=np.float32)
        self.action_space = spaces.Discrete(3)  # 0=SELL, 1=HOLD, 2=BUY
        self.state = np.zeros(5, dtype=np.float32)
        self.steps = 0

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.state = np.random.uniform(-1, 1, 5).astype(np.float32)
        self.steps = 0
        info = {}
        return self.state, info

    def step(self, action):
        reward = np.random.randn()  # récompense aléatoire
        terminated = np.random.rand() > 0.95  # fin d’épisode aléatoire
        truncated = False  # ici, pas de coupure de séquence
        self.state = np.random.uniform(-1, 1, 5).astype(np.float32)
        info = {}
        return self.state, reward, terminated, truncated, info
