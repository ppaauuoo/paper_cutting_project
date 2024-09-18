import os
import ydf
from typing import Dict, Optional
import numpy as np
from icecream import ic

class YDF:
    def __init__(self, models_dir: Optional[str] = None):
        if models_dir is None:
            models_dir = os.path.abspath(os.path.join(".", "modules/" "yggdrasil_models"))
        self.model_names = [
            "front_sheet",
            "c_wave",
            "middle_sheet",
            "b_wave",
            "back_sheet",
        ]
        self.model = {}
        for paper in self.model_names:
            self.model[paper] = ydf.load_model(ic(f"{models_dir}/{paper}-P"))

        # Organizing labels into a dictionary
        self.labels = {
            "front_sheet": ['KS231','KS161','KB230','KS121','KB160','KB120','KAC125','KI128','KA125','KL250','CM97','KAV150','KAC155','KAC185','KA155','CM127','WLK154','KL125','KA185','KA225','KI158','KAC225','KI188','WLK174','KM120'],
            "c_wave": ['CM127','CM147','CM112','None','CM197','CM100','CME100'],
            "middle_sheet": ['None','CM127','CM147','CME100','CM112','CM197','CM97','CM100'],
            "b_wave": ['None','CM127','CM112','CM147','CM197','CM100','CME100','CM97'],
            "back_sheet": ['KB160','KB120','KB230','CM127','CM112','CM97','CM147','KL250','KAV150','CM100','CM197','CME100','KA155','KA225','KA185','KAC155']
        }

    def predict(self, input: Dict) -> Dict:
        output = []
        for paper in self.model_names:
            output.append(self.model[paper].predict(input))

        predicted_classes = [np.argmax(pred) for pred in output]
        predicted_labels = {
            name: self.labels[name.split('-')[0]][index]
            for name, index in zip(self.model_names, predicted_classes)
        }

        return predicted_labels

    def get(self):
        return self.model


def main():
    test_input = {
        "front_sheet-O": ["KS231"],
        "c_wave-O": ["CM127"],
        "middle_sheet-O": ["CM127"],
        "b_wave-O": ["CM127"],
        "back_sheet-O": ["KB160"],
    }
    models_dir = os.path.abspath(os.path.join(".", "yggdrasil_models"))

    model = YDF(models_dir)
    prediction = model.predict(test_input)

    test_input = {key.replace('-O', ''): value for key, value in test_input.items()}
    print('test_input:')
    print(test_input)
    print('prediction:')
    print(prediction)


if __name__ == "__main__":
    main()
