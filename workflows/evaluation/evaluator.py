import matplotlib.pyplot as plt
import tempfile
import mlflow

class Evaluator:
    @staticmethod
    def evaluate(model, config):
        actions, total_assets, env_test = test_action_model(model, config)
        print(f"💰 Initial : {env_test.initial_capital}, Final : {env_test.total_asset}")
        return actions, total_assets, env_test

    @staticmethod
    def plot_gain(actions, total_assets, env_test, show_plot=True):
        gain_pct = (env_test.total_asset/env_test.initial_capital-1)*100
        plt.figure(figsize=(10,5))
        plt.plot(total_assets, label="Portefeuille", linewidth=2)
        plt.title(f"Gain total : {gain_pct:.2f}%")
        plt.grid(True)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        plt.savefig(tmp.name)
        mlflow.log_artifact(tmp.name, artifact_path="plots")
        mlflow.log_metric("final_gain", gain_pct)
        if show_plot: plt.show()
        plt.close()
