from stable_baselines3.common.callbacks import BaseCallback

class HallucinationCallback(BaseCallback):
    """
    Détecte les comportements incohérents (PnL négatif très élevé, actions extrêmes répétées)
    """
    def __init__(self, env, verbose=1):
        super().__init__(verbose)
        self.env = env
        self.history = []

    def _on_step(self) -> bool:
        infos = self.locals.get("infos")
        if infos:
            info = infos[0] if isinstance(infos, (list, tuple)) else infos
            if isinstance(info, dict):
                bal = info.get("balance", None)
                pos = info.get("position", None)
                if bal is not None:
                    self.history.append((bal, pos))
                    max_bal = max([h[0] for h in self.history])
                    if max_bal is not None and bal < 0.5 * max_bal:
                        if self.verbose > 0:
                            self.logger.record("hallucination_alert", bal)
                            print(f"⚠️ Alerte hallucination : balance {bal:.2f}, position {pos}")
        return True
