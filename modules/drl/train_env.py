import gymnasium
import cutting_stock
import polars as pl
from pathlib import Path

from sb3_contrib import MaskablePPO
from stable_baselines3.common.env_util import make_vec_env

# Load sample data
data_path = Path(__file__).parent.parent.parent / 'data' / 'sampledata.xlsx'
orders = pl.read_excel(data_path)
   
orders=orders['width']

# env = gymnasium.make('cutting_stock/CuttingStock',W=66,required_widths=orders)


# Parallel environments
vec_env = make_vec_env(
    'cutting_stock/CuttingStock',
    n_envs=4,
    env_kwargs={'W': 66, 'required_widths': orders}
)

model = MaskablePPO("MlpPolicy", vec_env, verbose=1)
model.learn(total_timesteps=25000)
model.save("ppo_cutting")

obs = vec_env.reset()
while True:
    action, _states = model.predict(obs)
    obs, rewards, dones, info = vec_env.step(action)
    vec_env.render("human")
