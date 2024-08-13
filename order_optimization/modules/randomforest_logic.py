import joblib
import pandas as pd

import os
from sklearn.ensemble import RandomForestClassifier

models_dir = os.path.abspath(os.path.join('.','order_optimization','modules','randomforest_models'))

model_names = ['front_sheetP', 'c_waveP', 'middle_sheetP', 'b_waveP', 'back_sheetP']
models = {}


for name in model_names:
# Load the saved model
    models[name] = joblib.load(os.path.join(models_dir, f'{name}_randomforest.joblib'))


paper_part = 'front_sheet'

test_data = {
    f'{paper_part}-O': ['CM127     '],
}

test = pd.DataFrame(test_data)
print(test)

X = test

first_row = X.iloc[0]
print(first_row)
print(models['front_sheetP'].predict([first_row]))