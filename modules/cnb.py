

from typing import Optional
from sklearn.preprocessing import OrdinalEncoder
import numpy as np
from sklearn.naive_bayes import CategoricalNB
from dataclasses import dataclass
import pandas as pd




input = ['front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']
output = ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']

@dataclass
class CNB:
    df_data: pd.DataFrame
    nb_input: Optional[pd.DataFrame] = None

    def build(self):
        self.nb_output = {}
        data = self.df_data[input]
        input_enc = OrdinalEncoder()
        input_enc.fit(data)
        self.input_enc = input_enc
        X = input_enc.set_params(encoded_missing_value=-1).transform(data)
        nb_input = input_enc.set_params(encoded_missing_value=-1).transform(self.nb_input)
        self.nb_input = nb_input
        for paper_type in output:
            label = self.df_data[[paper_type]]
            output_enc = OrdinalEncoder()
            output_enc.fit(label)
            y = output_enc.set_params(encoded_missing_value=-1).transform(label)
            
            clf = CategoricalNB()
            clf.fit(X, y.ravel())
            
            # Get predicted probabilities
            pred_proba = clf.predict_proba(nb_input)
            
            # Get the predicted classes
            pred = clf.predict(nb_input)
            
            # Prepare predictions for output
            predictions = []
            for i in range(len(pred_proba[0])):
                class_label = output_enc.inverse_transform([[i]])[0]  # Reshape for inverse_transform
                prob = pred_proba[0][i]
                predictions.append((prob, class_label))
            
            # Sort predictions by probability in descending order
            predictions.sort(key=lambda x: x[0], reverse=True)
        
            pred_output = {}
            for i, (prob, cls) in enumerate(predictions, start=1):
                if prob <= 0.0001: break
                if i > 10: break
                cls_out = ''.join(cls)
                pred_output[i]={ 'type':f'{cls_out}','proba': f'{prob:.2%}'}
            pred_output['acc'] = f"{clf.score(X,y):.2%}"
            self.nb_output[f'{paper_type}']=pred_output

    def get(self):
        return self.nb_output

    def show(self):
        # Decode input
        input_decoded = self.input_enc.inverse_transform(self.nb_input) 
        print(f'Input: {input_decoded}\n')
        
        print('Predictions:\n')
        
        # Print the dictionary contents with improved formatting
        for key, values in self.nb_output.items():
            print(f"{key}:")
            
            for item, details in values.items():
                if isinstance(details, dict):
                    proba = details.get('proba', 'N/A')
                    paper_type = details.get('type', 'N/A')
                    #print(f"  {item}. Probability: {proba}, Type: {paper_type}")
                    print(f"  {item}. Type: {paper_type} Probability: {proba}" )
                else:
                    print(f"  {item}: {details}")
            
            print() 

    def predict(self, data_dict):
        nb_input = pd.DataFrame(data_dict, index=[0]) 
        self.nb_input = nb_input
        self.build()
        return self.get()        
 
