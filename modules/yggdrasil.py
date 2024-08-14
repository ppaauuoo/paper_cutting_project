import os
import ydf  # Yggdrasil Decision Forests
from typing import Dict
import numpy as np

import os
import numpy as np
from typing import Dict

class YDF:
    def __init__(self):
        models_dir = os.path.abspath(os.path.join('.', 'modules', 'yggdrasil_models'))
        self.model_names = ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']
        self.model = {}
        for paper in self.model_names:
            self.model[paper] = ydf.load_model(f"{models_dir}/{paper}")

    def predict(self, input: Dict) -> Dict:
        class_labels = [
            "KS231", "KS161", "KB230", "KS121", "KB160", "KB120", "KAC125", "CM85", 
            "CM97", "KI128", "KA125", "CM127", "KAC185", "KA185", "KAC155", "KAV150", 
            "KL250", "KA155", "KL125", "WLK154", "KI158", "KAC225", "KL205", "KI188", 
            "KA225", "KAP185", "KAV185", "WLK174", "CM112", "KM150", "CM100", "KAV230", 
            "KM120"
        ]
        
        output = []
        for paper in self.model_names:
            output.append(self.model[paper].predict(input))
        
        predicted_classes = [np.argmax(pred) for pred in output]
        predicted_labels = {name: class_labels[index] for name, index in zip(self.model_names, predicted_classes)}

        return predicted_labels 

    def get(self):
        return self.model



test_input = {
    'front_sheet-P': ['KS161'],
    'c_wave-P': ['CM127'],
    'middle_sheet-P': ['CM127'],
    'b_wave-P': ['CM127'],
    'back_sheet-P': ['KB160'],
    'front_sheet-O': ['KS161'],
    'c_wave-O': ['CM127'],
    'middle_sheet-O': ['CM127'],
    'b_wave-O': ['CM127'],
    'back_sheet-O': ['KB160']
}

model = YDF()
predictions = model.predict(test_input)
print(predictions)