from cnb import CNB
import pandas as pd
from sklearn.model_selection import train_test_split
from icecream import ic

data = '../data/paper-substitution.csv'
df = pd.read_csv(data)
col_names = ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P', 'front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']


df.columns = col_names


output =  ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']

input = ['front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']

mask = (df[['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']].values ==
        df[['front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']].values).all(axis=1)

df_cleaned = df[~mask].reset_index(drop=True)

for i in output+input:
    df_cleaned[i] = df_cleaned[i].str.strip().replace('', None).fillna('None')


df_train, df_test = train_test_split(df_cleaned, test_size=0.1, random_state=42)

data_dict = {
    'front_sheet-O': 'KAC125',
    'c_wave-O': 'CM112',
    'middle_sheet-O': 'None',
    'b_wave-O': 'None',
    'back_sheet-O': 'KB120'
}
nb_input = pd.DataFrame(data_dict, index=[0]) 

cnb_instance = CNB(df_data=df_train,nb_input=nb_input)
cnb_instance.show()


