import os
import pandas as pd
from datetime import datetime
from evidently import Report, Regression


class DriftMonitor:
    def __init__(self, workspace_dir="data/reports", reference_path="data/reference_data.csv"):
        os.makedirs(workspace_dir, exist_ok=True)
        self.workspace_dir = workspace_dir

        # Chargement des données de référence
        try:
            self.reference_data = pd.read_csv(reference_path)
            print(f"✅ Données de référence chargées : {len(self.reference_data)} lignes")
        except FileNotFoundError:
            print("⚠️ Aucune donnée de référence trouvée, elle sera créée à la première exécution.")
            self.reference_data = None

        # Buffer d'observations
        self.observations_buffer = []
        self.buffer_size = 1000

    def add_observation(self, observation, action, reward):
        """Ajoute une observation au buffer"""
        timestamp = datetime.now()
        data = {
            "timestamp": timestamp,
            "price": observation[0],
            "delta": observation[1],
            "action": action,
            "reward": reward,
        }
        self.observations_buffer.append(data)

        # Génère un rapport si on atteint le seuil
        if len(self.observations_buffer) >= self.buffer_size:
            self._create_drift_report()
            self.observations_buffer = []

    def _create_drift_report(self):
        """Crée un rapport Evidently 0.7+ pour comparer les distributions"""
        if not self.observations_buffer:
            return

        current_data = pd.DataFrame(self.observations_buffer)

        if self.reference_data is None:
            self.reference_data = current_data.copy()
            self.reference_data.to_csv(os.path.join(self.workspace_dir, "reference_data.csv"), index=False)
            print("✅ Données de référence initialisées.")
            return

        try:
            # ⚙️ Evidently 0.7+ — approche unifiée par type de tâche
            report = Report(
                Regression(target='reward', prediction='price')  # ici, "reward" est la variable à suivre
            )

            report.run(
                reference_data=self.reference_data,
                current_data=current_data
            )

            report_name = f"drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            report_path = os.path.join(self.workspace_dir, report_name)
            report.save_html(report_path)

            print(f"✅ Rapport Evidently généré : {report_path}")

        except Exception as e:
            print(f"❌ Erreur Evidently : {e}")
            return {"status": "error", "message": str(e)}

        return {"status": "success"}

    def get_latest_metrics(self):
        """Retourne les statistiques basiques du buffer"""
        if not self.observations_buffer:
            return None

        df = pd.DataFrame(self.observations_buffer)
        return {
            "n_observations": len(df),
            "mean_reward": df["reward"].mean(),
            "action_distribution": df["action"].value_counts().to_dict(),
            "last_update": df["timestamp"].max(),
        }
