import os
import ydf  # Yggdrasil Decision Forests

class YDF:
    def __init__(self):
        models_dir = os.path.abspath(os.path.join('.','order_optimization','modules','yggdrasil_models'))
        self.model_names = ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']
        self.model = {}
        for paper in self.model_names:
            self.model[paper] = ydf.load_model(f"{models_dir}\{paper}")
