from finrl.meta.env_stock_trading.env_stocktrading_np import StockTradingEnv
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3 import PPO
from prefect import get_run_logger

def optimize_model(trial, config):
    
    learning_rate = trial.suggest_float("learning_rate", 1e-5, 3e-4, log=True)
    n_steps = trial.suggest_categorical("n_steps", [1024, 2048, 4096])
    gamma = trial.suggest_float("gamma", 0.9, 0.9999)
    clip_range = trial.suggest_float("clip_range", 0.1, 0.3)
    ent_coef = trial.suggest_float("ent_coef", 1e-5, 0.01, log=True)

    train_env = DummyVecEnv([lambda: StockTradingEnv(config=config)])
    model = PPO(
        "MlpPolicy",
        train_env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        gamma=gamma,
        clip_range=clip_range,
        ent_coef=ent_coef,
        verbose=0
    )

    model.learn(total_timesteps=50_000)
    mean_reward, _ = evaluate_policy(model, train_env, n_eval_episodes=5)

    return mean_reward
