

from typing import Optional, Dict
from sklearn.preprocessing import OrdinalEncoder
import numpy as np
from sklearn.naive_bayes import CategoricalNB
from dataclasses import dataclass
import pandas as pd
import pickle
import os
from icecream import ic

input = ['front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']
output = ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']

@dataclass
class CNB:
    nb_input: Optional[pd.DataFrame] = None
    models_dir: Optional[str] = None
    def __post_init__(self):
        if self.models_dir is None:
            self.models_dir = os.path.abspath(os.path.join(".","modules/"  "cnb_models"))

        self.nb_output = {}

    def build(self):
        data = '../data/paper-substitution.csv'
        df = pd.read_csv(data)
        col_names = ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P', 'front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']


        df.columns = col_names

        mask = (df[['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']].values ==
                df[['front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']].values).all(axis=1)

        df_cleaned = df[~mask].reset_index(drop=True)

        for i in output+input:
            df_cleaned[i] = df_cleaned[i].str.strip().replace('', None).fillna('None')



        self.df_data = df_cleaned


        models_dir = self.models_dir
        ic(self.df_data[input])
        data = self.df_data[input]
        input_enc = OrdinalEncoder()
        input_enc.fit(data)
        self.input_enc = input_enc
        X = input_enc.set_params(encoded_missing_value=-1).transform(data)
        model_acc={}
        for paper_type in output:
            label = self.df_data[[paper_type]]
            output_enc = OrdinalEncoder()
            output_enc.fit(label)
            y = output_enc.set_params(encoded_missing_value=-1).transform(label)

            clf = CategoricalNB()
            clf.fit(X, y.ravel())

            model_acc[f'{paper_type}']= f"{clf.score(X,y):.2%}"

            with open(f'{models_dir}/{paper_type}.pkl','wb') as f:
                pickle.dump(clf,f)

            with open(f'{models_dir}/{paper_type}_enc.pkl','wb') as f:
                pickle.dump(output_enc,f)

            with open(f'{models_dir}/input_enc.pkl','wb') as f:
                pickle.dump(input_enc,f)

        with open(f'{models_dir}/model_acc.pkl','wb') as f:
            pickle.dump(model_acc,f)

    def get(self):
        models_dir = self.models_dir
        nb_input = self.nb_input
        with open(f'{models_dir}/model_acc.pkl','rb') as f:
            model_acc = pickle.load(f)

        with open(f'{models_dir}/input_enc.pkl','rb') as f:
            input_enc = pickle.load(f)

        nb_input = input_enc.set_params(encoded_missing_value=-1).transform(nb_input)
        for paper_type in output:
            with open(f'{models_dir}/{paper_type}.pkl','rb') as f:
                clf = pickle.load(f)

            with open(f'{models_dir}/{paper_type}_enc.pkl','rb') as f:
                output_enc = pickle.load(f)

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

            pred_output:Dict[int|str,str|Dict[str,str]] = {}
            for i, (prob, cls) in enumerate(predictions, start=1):
                if prob <= 0.0001: break
                if i > 10: break
                cls_out = ''.join(cls)
                pred_output[i]={ 'type':f'{cls_out}','proba': f'{prob:.2%}'}
            pred_output['acc'] = model_acc[f'{paper_type}']
            self.nb_output[f'{paper_type}']=pred_output
        return self.nb_output

    def show(self):

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
        return self.get()

def main():
    data_dict = {
    'front_sheet-O': 'KAC125',
    'c_wave-O': 'CM112',
    'middle_sheet-O': 'None',
    'b_wave-O': 'None',
    'back_sheet-O': 'KB120'
}

    models_dir = os.path.abspath(os.path.join(".", "cnb_models"))
    CNB(models_dir=models_dir).build()


if __name__ == "__main__":
    main()
