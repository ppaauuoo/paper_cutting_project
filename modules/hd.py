
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

    is_build: bool = True 
    
    def __post_init__(self):
        if self.orders.empty: raise ValueError('Orders Empty!')
        if self.is_build:
            self.build()
        
    def build(self):
        data = self.format_data(self.orders)
        data = self.date_range_limit(data)
        
        filters = {False: self.legacy_filter_order, True: self.filter_common_order}
        filtered_data = filters.get(self.common)(data)
        self.temp_size = min(ROLL_PAPER)
        ff_list = []
        ffa_list = []

        match(self.h_type):
            case 'ff':
                ff_list = [[] for _ in range(self.x)]
                for item, id in zip(filtered_data['width'], filtered_data['id']):
                    ff_list = self.first_fit(ff_list, item, id)
                data_df = self.df_formatter(ff_list)
            case 'ffa':
                ffa_list = [[] for _ in range(self.x)]
                asc_filtered_data = filtered_data.sort_values('width', ascending=True)
                for item, id in zip(asc_filtered_data['width'], asc_filtered_data['id']):
                    ffa_list = self.first_fit(ffa_list, item, id)
                data_df = self.df_formatter(ffa_list)

        heuristic_data_id = data_df
        heuristic_data_id = heuristic_data_id.drop_duplicates('id').reset_index(drop=True)

        self.heuristic_data = filtered_data[filtered_data['id'].isin(heuristic_data_id['id'])].reset_index(drop=True)



    @staticmethod
    def format_data(data):
        """Format due date for calculation purpose and filter out any unuseable data."""
        ordplan = data.copy()
        ordplan["due_date"] = pd.to_datetime(ordplan["due_date"], format="%m/%d/%Y")
        ordplan.fillna(0, inplace=True)  # fix error values ex. , -> NA
        ordplan = ordplan[ordplan["length"] > 0]  # drop len = 0
        ordplan = ordplan[ordplan["quantity"] > 500]  # drop quantity = 500

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


    def date_range_limit(self, data):
        if self.stop_date and self.start_date:
            data = data[(data['due_date'] >= self.start_date) & (data['due_date'] <= self.stop_date)].reset_index(drop=True)
        return data
 

    def legacy_filter_order(self, data, data_range:float = DEADLINE_RANGE,best_plan:pd.DataFrame = pd.DataFrame(None) ):
            used_data = data.head(int(data_range)).copy()

            legacy_filters = LEGACY_FILTER
            indices = list(range(0,len(used_data)))
            random.shuffle(indices)
            indices = indices[:100]

            for index in indices:
                init_order = used_data.iloc[index]
                # Create a mask for matching orders using all legacy filters
                mask = (used_data[legacy_filters].eq(init_order[legacy_filters])).all(axis=1)
                # Apply the mask and reset the index
                plan = used_data.loc[mask].reset_index(drop=True)
                if len(plan)>len(best_plan):
                    best_plan = plan
                
                #early stop
                if len(best_plan) >= PLAN_RANGE:
                    return best_plan

            if len(best_plan) < PLAN_RANGE:
                return self.legacy_filter_order(data=data, data_range=data_range+PLAN_RANGE)

            return best_plan 

    def filter_common_order(self,data):
        """Use common filter base on the first order or filler order."""
        if not self.common:
            return

        legacy_filters = LEGACY_FILTER

        init_order = pd.DataFrame([self.common_init_order])

        if init_order is None:
            raise ValueError('Common init order is None!')
        mask = (data[legacy_filters].eq(init_order[legacy_filters].iloc[0])).all(axis=1)
        legecy_filtered_plan = data.loc[mask].reset_index(drop=True).copy()
        if len(legecy_filtered_plan) <= 0:
            raise ValueError('Legacy is empty')
        best_plan:pd.DataFrame = pd.DataFrame(None)
        common_filters = COMMON_FILTER
        best_plan = pd.DataFrame(None)
        best_index=0
        indices = list(range(len(legecy_filtered_plan)))
        random.shuffle(indices)
        indices = indices[:100]
        for index in indices:
            init_order = legecy_filtered_plan.iloc[index]
            mask = (data[common_filters].eq(init_order[common_filters])).all(axis=1)
            orders = data.loc[mask].reset_index(drop=True).copy()
            
            if len(orders)>len(best_plan):
                best_plan = orders

        return best_plan
