from finrl.meta.env_stock_trading.env_stocktrading_np import StockTradingEnv
from prefect import get_run_logger

def test_action_model(final_model, config):
    logger = get_run_logger()
    config_test = config.copy()
    config_test["if_train"] = False
    env_test = StockTradingEnv(config=config_test)
    
    actions_list = []
    total_assets = []
    rewards = []

    obs = env_test.reset()
    if isinstance(obs, tuple):
        obs = obs[0]

    for _ in range(env_test.max_step):
        action, _ = final_model.predict(obs, deterministic=True)
        result = env_test.step(action)

        if len(result) == 5:
            obs, reward, terminated, truncated, info = result
            done = terminated or truncated
        else:
            obs, reward, done, info = result

        if isinstance(obs, tuple):
            obs = obs[0]

        total_assets.append(env_test.total_asset)
        rewards.append(reward)
        actions_list.append(action)

        if done:
            break

    logger.info("✅ Test terminé")
    return actions_list, total_assets, env_test
