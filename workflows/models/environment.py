import numpy as np
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from finrl.meta.env_stock_trading.env_stocktrading_np import StockTradingEnv

class TradingEnvBuilder:
    @staticmethod
    def make_env(df, seed=None, if_train=True):
        def _init():
            df_local = df.copy()
            df_local["return"] = df_local["close"].pct_change().fillna(0)
            df_local["high_low_range"] = (df_local["high"] - df_local["low"]) / df_local["close"]
            df_local["open_close_diff"] = (df_local["close"] - df_local["open"]) / df_local["open"]
            df_local["rolling_mean_5"] = df_local["close"].rolling(5).mean().bfill()
            df_local["rolling_std_5"] = df_local["close"].rolling(5).std().bfill()

            price_array = df_local[["close"]].values
            tech_array = np.column_stack([
                df_local["return"], df_local["high_low_range"], 
                df_local["open_close_diff"], df_local["rolling_mean_5"], df_local["rolling_std_5"]
            ])
            turbulence_array = np.zeros(len(df_local))

            env = StockTradingEnv(config={
                "price_array": price_array,
                "tech_array": tech_array,
                "turbulence_array": turbulence_array,
                "if_train": if_train
            })
            try: env.reset(seed=seed)
            except TypeError: pass
            return Monitor(env)
        return _init
