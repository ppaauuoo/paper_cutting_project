import os
import ydf  # Yggdrasil Decision Forests
import pandas as pd  # We use Pandas to load small datasets

models_dir = os.path.abspath(os.path.join('.','order_optimization','modules','yggdrasil_models'))

model_names = ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']

model = {}


for paper in model_names:
    print(f"{models_dir}\{paper}")
    model[paper] = ydf.load_model(f"{models_dir}\{paper}")
    print(f"This is a {model[paper].name()} model.")
