import torch
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3.common.callbacks import BaseCallback

class NaNStopCallback(BaseCallback):
    def _on_step(self):
        for param in self.model.policy.parameters():
            if torch.isnan(param).any():
                print("❌ NaN détecté — arrêt de l'entraînement.")
                return False
        return True

class EarlyStoppingCallback(BaseCallback):
    def __init__(self, check_freq=5000, min_improvement=0.02, lookback=5):
        super().__init__()
        self.check_freq = check_freq
        self.min_improvement = min_improvement
        self.lookback = lookback
        self.rewards = []

    def _on_step(self):
        if self.n_calls % self.check_freq == 0 and len(self.model.ep_info_buffer) > 0:
            current_reward = np.mean([ep_info["r"] for ep_info in self.model.ep_info_buffer])
            self.rewards.append(current_reward)
            if len(self.rewards) > self.lookback:
                old_mean = np.mean(self.rewards[-self.lookback-1:-1])
                new_mean = np.mean(self.rewards[-self.lookback:])
                if (new_mean - old_mean) < self.min_improvement:
                    print(f"⚠️ Early stopping: reward stagnante ({new_mean:.2f})")
                    return False
        return True

class EquityVisualizerCallback(BaseCallback):
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.equity, self.positions, self.prices = [], [], []

    def _on_step(self):
        infos = self.locals.get("infos")
        if infos:
            info = infos[0] if isinstance(infos, (list, tuple)) else infos
            if isinstance(info, dict):
                if bal := info.get("balance"): self.equity.append(bal)
                if pos := info.get("position"): self.positions.append(pos)
                if close := info.get("close"): self.prices.append(close)
        return True

    def plot_results(self):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[2, 1])
        ax1.plot(self.equity, color="blue"); ax1.set_title("💰 Balance"); ax1.grid(True)
        ax2.plot(self.prices, color="gray", alpha=0.6)
        for i in range(1, len(self.positions)):
            color = "green" if self.positions[i] == 1 else "red" if self.positions[i] == -1 else None
            if color: ax2.axvspan(i-1, i, color=color, alpha=0.3)
        ax2.set_title("📈 Prix & positions"); ax2.grid(True)
        plt.tight_layout(); plt.show()
