#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import matplotlib.pyplot as plt # data visualization
import seaborn as sns # statistical data visualization
from sklearn.model_selection import train_test_split


# In[2]:


data = './data/paper-substitution.csv'

df = pd.read_csv(data)
col_names = ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P', 'front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']


df.columns = col_names

paper_part = 'front_sheet'


# #Yagdrasil

# In[3]:


import ydf  # Yggdrasil Decision Forests
import pandas as pd  # We use Pandas to load small datasets
from icecream import ic


output =  ['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']

input = ['front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']

# Create a mask to identify rows where -P and -O columns are the same
mask = (df[['front_sheet-P', 'c_wave-P', 'middle_sheet-P', 'b_wave-P', 'back_sheet-P']].values ==
        df[['front_sheet-O', 'c_wave-O', 'middle_sheet-O', 'b_wave-O', 'back_sheet-O']].values).all(axis=1)

# Drop the rows where the mask is True
df_cleaned = df[~mask].reset_index(drop=True)
# df_cleaned = df

for i in output+input:
    df_cleaned[i] = df_cleaned[i].str.strip().replace('', None).fillna('None')


df_train, df_test = train_test_split(df_cleaned, test_size=0.1, random_state=42)

df_cleaned


# In[4]:


model = {}

for paper in output:
    model[paper] = ydf.RandomForestLearner(label=f'{paper}', features=input, task=ydf.Task.CLASSIFICATION).train(df_train)
    # model[paper].save(f"modules/yggdrasil_models/{paper}")
    evaluation = model[paper].evaluate(df_test)
    # Query individual evaluation metrics
    print(f"{paper}test accuracy: {evaluation.accuracy}")


# In[5]:


model = {}

for paper in output:
    model[paper] = ydf.GradientBoostedTreesLearner(label=f'{paper}', features=input).train(df_train)
    # model[paper].save(f"modules/yggdrasil_models/{paper}")
    evaluation = model[paper].evaluate(df_test)
    # Query individual evaluation metrics
    print(f"{paper}test accuracy: {evaluation.accuracy}")


# In[12]:
       
from cnb import CNB


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


# In[7]:


# import numpy as np
# from sklearn.naive_bayes import CategoricalNB
# clf = CategoricalNB()
# clf.fit(X, y.ravel())
# nb_input = X[3:4]
# pred = clf.predict(nb_input)
# print('input',input_enc.inverse_transform(nb_input))
# print('output\n',output_enc.inverse_transform(pred.reshape(-1, 1)))


# In[ ]:


#rfc sklearn


# In[ ]:


X = df[[col for col in col_names if f'{paper_part}-P' not in col]].copy()
y = df[f'{paper_part}-P'].copy()
# split data into training and testing sets


X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.33, random_state = 42)

import category_encoders as ce
# encode categorical variables with ordinal encoding

encoder = ce.OrdinalEncoder(cols=[f'{paper_part}-O'])



X_train = encoder.fit_transform(X_train)

X_test = encoder.transform(X_test)


# In[ ]:


# instantiate the classifier with n_estimators = 100
from sklearn.ensemble import RandomForestClassifier

rfc_100 = RandomForestClassifier(n_estimators=100, random_state=0)



# fit the model to the training set

rfc_100.fit(X_train, y_train)



# Predict on the test set results

y_pred_100 = rfc_100.predict(X_test)



# Check accuracy score 
from sklearn.metrics import accuracy_score

print('Model accuracy score with 100 decision-trees : {0:0.4f}'. format(accuracy_score(y_test, y_pred_100)))


# In[ ]:


test_data = {
    f'{paper_part}-O': ['CM127     '],
}

test = pd.DataFrame(test_data)
print(test)

X = encoder.transform(test)

first_row = X.iloc[0]
print(first_row)
print(rfc_100.predict([first_row]))


import joblib
joblib.dump(rfc_100, f'{paper_part}P_randomforest.joblib')


# In[ ]:


# create the classifier with n_estimators = 100

clf = RandomForestClassifier(n_estimators=100, random_state=0)



# fit the model to the training set

clf.fit(X_train, y_train)


# In[ ]:


# view the feature scores

feature_scores = pd.Series(clf.feature_importances_, index=X_train.columns).sort_values(ascending=False)

feature_scores


# In[ ]:


# Creating a seaborn bar plot

sns.barplot(x=feature_scores, y=feature_scores.index)



# Add labels to the graph

plt.xlabel('Feature Importance Score')

plt.ylabel('Features')



# Add title to the graph

plt.title("Visualizing Important Features")



# Visualize the graph

plt.show()

