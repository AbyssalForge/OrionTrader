import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from dateutil.relativedelta import relativedelta
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from finrl.meta.env_stock_trading.env_stocktrading_np import StockTradingEnv
import optuna


# ===============================================================
# 🔧 Construction des splits temporels
# ===============================================================
def walk_forward_splits(df: pd.DataFrame,
                        train_months: int = 36,
                        test_months: int = 6,
                        stride_months: int = 6):
    df = df.sort_values("time")
    start = df["time"].min()
    end = df["time"].max()
    cur_start = start

    while cur_start + relativedelta(months=train_months + test_months) <= end:
        train_start = cur_start
        train_end = cur_start + relativedelta(months=train_months)
        test_end = train_end + relativedelta(months=test_months)

        train_df = df[(df["time"] >= train_start) & (df["time"] < train_end)]
        test_df = df[(df["time"] >= train_end) & (df["time"] < test_end)]

        yield train_df, test_df, train_start, test_end
        cur_start += relativedelta(months=stride_months)


# ===============================================================
# 🧩 Préparation de la config pour FinRL
# ===============================================================
def prepare_config(df: pd.DataFrame, scaler=None, if_train=True):
    if scaler is None:
        scaler = StandardScaler()
        df["close_scaled"] = scaler.fit_transform(df[["close"]])
    else:
        df["close_scaled"] = scaler.transform(df[["close"]])

    price_array = df[["close_scaled"]].values
    tech_array = np.column_stack([
        df["close_scaled"].pct_change().fillna(0),
        df["close_scaled"].rolling(5).mean().bfill()
    ])
    turbulence_array = np.zeros(len(df))

    config = {
        "price_array": price_array,
        "tech_array": tech_array,
        "turbulence_array": turbulence_array,
        "if_train": if_train,
    }

    return config, scaler


# ===============================================================
# ⚙️ Optimisation Optuna des hyperparamètres PPO
# ===============================================================
def optimize_model(train_env, n_trials=10):

    def objective(trial):
        learning_rate = trial.suggest_float("learning_rate", 1e-5, 1e-3, log=True)
        gamma = trial.suggest_float("gamma", 0.90, 0.999)
        gae_lambda = trial.suggest_float("gae_lambda", 0.8, 1.0)
        clip_range = trial.suggest_float("clip_range", 0.1, 0.4)
        ent_coef = trial.suggest_float("ent_coef", 1e-4, 1e-1, log=True)
        n_steps = trial.suggest_int("n_steps", 128, 512, step=64)

        model = PPO(
            "MlpPolicy",
            train_env,
            learning_rate=learning_rate,
            gamma=gamma,
            gae_lambda=gae_lambda,
            clip_range=clip_range,
            ent_coef=ent_coef,
            n_steps=n_steps,
            verbose=0,
        )

        model.learn(total_timesteps=10_000)
        rewards = []
        obs = train_env.reset()
        for _ in range(500):
            action, _ = model.predict(obs)
            obs, reward, done, _ = train_env.step(action)
            rewards.append(reward)
            if done.any():
                break
        return np.mean(rewards)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)
    return study.best_params, study.best_value


# ===============================================================
# 🤖 Boucle principale Walk-Forward
# ===============================================================
def run_walk_forward(df: pd.DataFrame,
                     train_months: int = 36,
                     test_months: int = 6,
                     stride_months: int = 6,
                     n_trials: int = 5,
                     save_dir: str = "models"):
    os.makedirs(save_dir, exist_ok=True)
    results = []

    for train_df, test_df, start, end in walk_forward_splits(df, train_months, test_months, stride_months):
        print(f"\n🧭 Fenêtre {start.date()} → {end.date()}")

        # Préparation des configs
        train_config, scaler = prepare_config(train_df, if_train=True)
        test_config, _ = prepare_config(test_df, scaler=scaler, if_train=False)

        # Création des environnements
        train_env = DummyVecEnv([lambda: StockTradingEnv(config=train_config)])
        test_env = DummyVecEnv([lambda: StockTradingEnv(config=test_config)])

        # Optimisation des hyperparamètres
        best_params, best_reward = optimize_model(train_env, n_trials=n_trials)
        print(f"✅ Meilleurs paramètres: {best_params}")
        print(f"🏆 Reward moyen: {best_reward:.2f}")

        # Entraînement final avec les meilleurs hyperparamètres
        model = PPO("MlpPolicy", train_env, verbose=0, **best_params)
        model.learn(total_timesteps=50_000)

        # Évaluation sur la période test
        obs = test_env.reset()
        total_reward = 0
        for _ in range(len(test_df)):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, _ = test_env.step(action)
            total_reward += reward[0]
            if done.any():
                break

        model_path = os.path.join(save_dir, f"ppo_walkforward_{start.date()}_{end.date()}.zip")
        model.save(model_path)
        print(f"💾 Modèle sauvegardé: {model_path}")

        results.append({
            "train_start": start,
            "train_end": start + relativedelta(months=train_months),
            "test_end": end,
            "best_reward_train": best_reward,
            "total_reward_test": total_reward,
            "best_params": best_params
        })

    return pd.DataFrame(results)
