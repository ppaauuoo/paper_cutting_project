from gymnasium.envs.registration import register

register(
    id="cutting_stock/CuttingStock",
    entry_point="cutting_stock.envs:CuttingStockEnv",
)
