
from typing import List, Any ,Optional
from dataclasses import dataclass, field
import pandas as pd
from order_optimization.container import ProviderInterface
from ordplan_project.settings import PLAN_RANGE, LEGACY_FILTER,COMMON_FILTER,UNIT_CONVERTER,DEADLINE_RANGE
import random

@dataclass
class HD(ProviderInterface):
    ROLL_PAPER = [66, 68, 70, 73, 74, 75, 79, 82, 85, 88, 91, 93, 95, 97]
    orders: pd.DataFrame
    x:int = 10 
    h_type:str = 'ff'
    start_date: Optional[pd.Timestamp] = None
    stop_date: Optional[pd.Timestamp] = None

    def __post_init__(self):
        data = self.orders
        if self.stop_date is not None:
            data = data[(data['due_date'] >= self.start_date) & (data['due_date'] <= self.stop_date)].reset_index(drop=True)
            
        filtered_data = self.legacy_filter_order(data)
        
        self.temp_size = min(self.ROLL_PAPER)
        self.ff_list = []
        self.ffa_list = []
        self.ffd_list = []

        match(self.h_type):
            case 'ff':
                self.ff_list = [[] for _ in range(self.x)]
            case 'ffa':
                self.ffa_list = [[] for _ in range(self.x)]

        ff_list = self.ff_list
        ffa_list = self.ffa_list
        ffd_list = self.ffd_list
        for item, id in zip(filtered_data['width'], filtered_data['id']):
            ff_list = self.first_fit(ff_list, item, id)
        
        # print(width_sum_formatter(ff_list))
        ff_df = self.df_formatter(ff_list)
        
        desc_filtered_data = filtered_data.sort_values('width', ascending=False)
        for item, id in zip(desc_filtered_data['width'], desc_filtered_data['id']):
            ffd_list = self.first_fit(ffd_list, item, id)
        
        # print(width_sum_formatter(ffd_list))
        ffd_df = self.df_formatter(ffd_list)
        
        asc_filtered_data = filtered_data.sort_values('width', ascending=True)
        for item, id in zip(asc_filtered_data['width'], asc_filtered_data['id']):
            ffa_list = self.first_fit(ffa_list, item, id)
            
        # print(width_sum_formatter(ffa_list))
        ffa_df = self.df_formatter(ffa_list)
        
        heuristic_data_id = pd.concat([ffd_df, ff_df, ffa_df])
        heuristic_data_id = heuristic_data_id.drop_duplicates('id').reset_index(drop=True)
        
        self.heuristic_data = filtered_data[filtered_data['id'].isin(heuristic_data_id['id'])].reset_index(drop=True)
    
    
    def is_fit(self, data_list, item):
        return sum([row[0] for row in data_list]) + item - self.temp_size < 0

    @staticmethod
    def get_width(data_list):
        return [row[0] for row in data_list]
    
    
    def width_sum_formatter(self, data_list):
        output = ""
        for index, _ in enumerate(data_list):
            output+= str(round(sum(self.get_width(data_list[index])),4))+" | "
        return output

    @staticmethod
    def df_formatter(data_list):
        combined_data = []
        for data in data_list:
            combined_data += data
        return pd.DataFrame(combined_data, columns=['width', 'id'])


    def first_fit(self,data_list, item, id):
        for data in data_list:
            if self.is_fit(data, item):
                data.append((item, id))
                return data_list
        return data_list

    def get(self) -> pd.DataFrame:    
        return self.heuristic_data

    @staticmethod
    def legacy_filter_order(data):
            legacy_filters = LEGACY_FILTER
            ordplan = pd.DataFrame(None)
            best_index=0
            most_compat_plan = 0
            indices = list(range(len(data)))
            random.shuffle(indices)

            for index in indices:
                init_order = data.iloc[index]
                # Create a mask for matching orders using all legacy filters
                mask = (data[legacy_filters].eq(init_order[legacy_filters])).all(axis=1)
                # Apply the mask and reset the index
                ordplan = data.loc[mask].reset_index(drop=True)
                if len(ordplan)>most_compat_plan:
                    best_index=index
                    most_compat_plan=len(ordplan)

            init_order = data.iloc[best_index]
            mask = (data[legacy_filters].eq(init_order[legacy_filters])).all(axis=1)
            ordplan = data.loc[mask].reset_index(drop=True)
            data = ordplan
            return data


# In[5]:




