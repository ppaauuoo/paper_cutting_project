
from typing import List, Any ,Optional, Dict
from dataclasses import dataclass, field
import pandas as pd
from order_optimization.container import ProviderInterface
from ordplan_project.settings import PLAN_RANGE, LEGACY_FILTER,COMMON_FILTER,UNIT_CONVERTER,DEADLINE_RANGE,ROLL_PAPER
import random
from icecream import ic

@dataclass
class HD(ProviderInterface):
    orders: pd.DataFrame
    x:int = 10 
    h_type:str = 'ffa'
    start_date: Optional[pd.Timestamp] = None
    stop_date: Optional[pd.Timestamp] = None
    common: bool = False
    common_init_order: Optional[Dict[str,Any]] = None
    preview: bool = False

    def filter_common_order(self,data):
        """Use common filter base on the first order or filler order."""
        if not self.common:
            return

        legacy_filters = LEGACY_FILTER
        init_order = pd.DataFrame(self.common_init_order)
        if init_order is None:
            raise ValueError('Common init order is None!')
        mask = (data[legacy_filters].eq(init_order[legacy_filters].iloc[0])).all(axis=1)
        legecy_filtered_plan = data.loc[mask].reset_index(drop=True).copy()
        if len(legecy_filtered_plan) <= 0:
            raise ValueError('Legacy is empty')
    
        common_filters = COMMON_FILTER
        orders = pd.DataFrame(None)
        best_index=0
        most_compat_plan = 0
        indices = list(range(len(legecy_filtered_plan)))
        random.shuffle(indices)
        for index in indices:
            init_order = legecy_filtered_plan.iloc[index]
            mask = (data[common_filters].eq(init_order[common_filters])).all(axis=1)
            orders = data.loc[mask].reset_index(drop=True).copy()
            if len(orders)>most_compat_plan:
                best_index=index
                most_compat_plan=len(orders)

        init_order = legecy_filtered_plan.iloc[best_index]
        mask = (data[common_filters].eq(init_order[common_filters])).all(axis=1)
        orders = data.loc[mask].reset_index(drop=True)
        return orders
        

    def __post_init__(self):
        data = self.orders.copy()
        data = self.format_data(data)
        if self.stop_date:
            data = data[(data['due_date'] >= self.start_date) & (data['due_date'] <= self.stop_date)].reset_index(drop=True)
        filters = {False: self.legacy_filter_order, True: self.filter_common_order}
        filtered_data = ic(filters.get(self.common))(data) 
        self.temp_size = min(ROLL_PAPER)
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
    
    @staticmethod
    def format_data(data):
        """Format due date for calculation purpose and filter out any unuseable data."""
        ordplan = data.copy() 
        ordplan["due_date"] = pd.to_datetime(ordplan["due_date"], format="%m/%d/%y")
        ordplan.fillna(0, inplace=True)  # fix error values ex. , -> NA
        ordplan = ordplan[ordplan["length"] > 0]  # drop len = 0
        ordplan = ordplan[ordplan["quantity"] > 0]  # drop quantity = 0

        return ordplan 

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
            plan_range = DEADLINE_RANGE
            data = data.head(int(plan_range))
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




