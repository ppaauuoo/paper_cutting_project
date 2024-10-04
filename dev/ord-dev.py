#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pandas as pd

UNIT_CONVERTER = 24.5
data = pd.read_excel('../media/data/order2024.xlsx', engine="openpyxl")

    # Rename columns
data = data.rename(columns={
        "กำหนดส่ง": "due_date",
        "แผ่นหน้า": "front_sheet",
        "ลอน C": "c_wave",
        "แผ่นกลาง": "middle_sheet",
        "ลอน B": "b_wave",
        "แผ่นหลัง": "back_sheet",
        "จน.ชั้น": "level",
        "กว้างผลิต": "width",
        "ยาวผลิต": "length",
        "ทับเส้นซ้าย": "left_edge_cut",
        "ทับเส้นกลาง": "middle_edge_cut",
        "ทับเส้นขวา": "right_edge_cut",
        "เลขที่ใบสั่งขาย": "order_number",
        "ชนิดส่วนประกอบ": "component_type",
        "จำนวนสั่งขาย": "quantity",
        "จำนวนสั่งผลิต": "production_quantity",
        "ประเภททับเส้น": "edge_type",
        "สถานะใบสั่ง": "order_status",
        "% ที่เกิน": "excess_percentage"
    })



# In[2]:


import uuid

for index, row in data.iterrows():
    data.at[index, 'width'] = round(row["width"] / UNIT_CONVERTER, 4)
    data.at[index, 'length'] = round(row["length"] / UNIT_CONVERTER, 4)
    data.at[index, 'id'] = uuid.uuid4()


# In[ ]:





# In[3]:


start_date = pd.to_datetime('2024-08-1')
stop_date = pd.to_datetime('2024-08-7')




# In[4]:





# In[6]:


from icecream import ic
import numpy as np
from dataclasses import dataclass
from typing import Any, Dict
from numpy import roll
import pandas as pd



# In[7]:


# from modules.ordplan import ORD

# legacy_data = ORD(filtered_data, deadline_range = 30, size=temp_size).get()



# In[8]:

from modules.lp import LP

# In[9]:


from modules.new_ga import GA

# In[10]:

from modules.hd import HD

# In[11]:


from ordplan_project.settings import MAX_TRIM, MIN_TRIM
from typing import Dict, Any

def is_trim_fit(trim: float):
    """
    Check if trim exceed min/max tirm.
    """
    return trim <= MAX_TRIM and trim >= MIN_TRIM


def handle_switcher(used) -> Dict[str,Any]:
    if is_trim_fit(used):
        return
    switcher = LP({'fitness': used}).run().get()
    # ic(switcher,used)
    return switcher

def update_acc_list(acc_list,ga_instance,hd_instance,elapsed_times):
        temp_acc_str = ""
        temp_acc_str+='Parameters -> '
        
        parameters = (
            "parent:" +ga_instance.parent_selection_type + " | " +
            "co proba:" +str(ga_instance.crossover_probability) + " | " +
            "crossover:" +ga_instance.crossover_type + " | " +
            str(ga_instance.mutation_probability) + " | " +
            str(ga_instance.mutation_percent_genes) + " | " +
            "heu type:" +hd_instance.h_type +"\n"
        )
        
        temp_acc_str+=parameters
        
        accuracy = (passed_trim / count) * 100.00 if count != 0 else 0.0
        temp_acc_str += "Accuracy -> {:.2f}%".format(accuracy)
    
        total_seconds = sum(elapsed_times)
        
        minutes, seconds = divmod(total_seconds, 60)
        
        time_spent_str = f"{int(minutes)}:{int(seconds):02d}"
        
        temp_acc_str += f"\nTime Spent -> {time_spent_str}"

        temp_acc_str += "\n"
        
        acc_list.append(temp_acc_str)


# In[14]:


from tqdm import tqdm
import itertools
import time

import enlighten


crossover_types = ["two_points", "uniform"]
mutation_proba = [None,[0.25, 0.05]]
crossover_proba = [None, 0.65]
acc_list = []

x = 1
count = 2

hd_instances = []
h_types = ["ff", "ffa"]
for h_type in h_types:
    hd_instance = HD(orders=data,h_type=h_type, x=x, start_date=start_date, stop_date=stop_date)
    hd_instances.append(hd_instance)

temp_size = hd_instance.temp_size

manager = enlighten.get_manager()
types = manager.counter(total=len(list((itertools.product(crossover_types, mutation_proba, crossover_proba, hd_instances)))), desc='Types', unit='it')
counts = manager.counter(total=count*len(list((itertools.product(crossover_types, mutation_proba, crossover_proba, hd_instances)))), desc='Count', unit='it')

for crossover_prob, crossover, mutation, hd_instance in itertools.product(crossover_proba, crossover_types, mutation_proba,hd_instances):
    heuristic_data = hd_instance.get()
    elapsed_times = []
    passed_trim = 0
    types.update()
    for i in range(count):
        counts.update()
        start_time = time.time()
        ga_instance = GA(
            heuristic_data,
            size=temp_size,
            num_generations=50,
            out_range=5,
            seed=i,
            parent_selection_type="tournament",
            crossover_type=crossover,
            mutation_probability=mutation,
            crossover_probability=crossover_prob
        )
        ga_instance.run()
        size = ga_instance.PAPER_SIZE
        trim = abs(ga_instance.fitness_values)
        used = ga_instance.PAPER_SIZE+ga_instance.fitness_values
        switcher = handle_switcher(used)
    
        if switcher is not None:
            size = switcher["new_roll"]
            trim = switcher["new_trim"]
    
        # print(size)
        # print(used)
        # print(trim)
        if trim < 3:
            passed_trim+=1
        end_time = time.time()
        elapsed_time = end_time - start_time
        elapsed_times.append(elapsed_time)


    update_acc_list(acc_list,ga_instance,hd_instance,elapsed_times)


    


# In[15]:


for i in acc_list:
    print(i)


# In[ ]:



