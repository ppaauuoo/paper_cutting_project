import pandas as pd
from typing import Dict

MM_TO_INCH = 25.4
DEADLINE_RANGE = 50
COMMON_FILTER = [
                "แผ่นหน้า", "ลอน C", "แผ่นกลาง", "ลอน B", "แผ่นหลัง", "จน.ชั้น", "ประเภททับเส้น",
                "กว้างผลิต", "ยาวผลิต", "ทับเส้นซ้าย", "ทับเส้นกลาง", "ทับเส้นขวา", "ชนิดส่วนประกอบ",
            ]
class ORD:
    def __init__(self, path: str, deadline_scope: int = 0, size: float = 66, tuning_values: int = 3, filter_value: int = 16, filter: bool = True, common: bool = False, filler: int =0,selector: Dict = None,first_date_only:bool = False) -> None:
        self.ordplan = pd.read_excel(path, engine='openpyxl')
        self.deadline_scope = deadline_scope
        self.filter = filter
        self.common = common
        self.size = size
        self.tuning_values = tuning_values
        self.filter_value = filter_value
        self.filler=filler
        self.selector=selector
        self.first_date_only=first_date_only
    
    def get(self) -> Dict:
        ordplan = self.ordplan
        self.format_data()

        if self.first_date_only:
            self.set_first_date()
        else:
            self.expand_deadline_scope()

        self.filter_diff_order()

        self.filter_common_order()
        
        self.set_selected_order()


        self.ordplan = ordplan.reset_index(drop=True)
        return self.ordplan


    def set_first_date(self):
        ordplan = self.ordplan
        deadline = ordplan["กำหนดส่ง"].iloc[0]
        self.ordplan = ordplan[ordplan["กำหนดส่ง"] == deadline].reset_index(drop=True) #filter only fist deadline

    def expand_deadline_scope(self):
        if self.deadline_scope < 0:
            return
        ordplan = self.ordplan
        deadline_range = DEADLINE_RANGE
        deadlines = ordplan["กำหนดส่ง"].unique()
        while len(ordplan) <= deadline_range and len(deadlines) <= self.deadline_scope:
            deadline = deadlines[self.deadline_scope]
            ordplan = ordplan[self.ordplan["กำหนดส่ง"] <= deadline].sort_values("กำหนดส่ง").reset_index(drop=True)
            self.deadline_scope = self.deadline_scope+1
            self.filter_diff_order()
        self.ordplan = ordplan
    
    def format_data(self):
        ordplan = self.ordplan
        ordplan["กว้างผลิต"] = round(ordplan["กว้างผลิต"] / MM_TO_INCH, 2)
        ordplan["ยาวผลิต"] = round(ordplan["ยาวผลิต"] / MM_TO_INCH, 2)
        ordplan["กำหนดส่ง"] = pd.to_datetime(ordplan["กำหนดส่ง"], format='%m/%d/%y').dt.strftime('%m/%d/%y')
        ordplan.fillna(0, inplace=True)  # fix error values ex. , -> NA
        self.ordplan = ordplan

    def filter_diff_order(self):
        if not self.filter:
            return
        ordplan = self.ordplan
        selected_values = self.size / self.tuning_values
        ordplan["diff"] = ordplan["กว้างผลิต"].apply(lambda x: abs(selected_values - x)) # add diff col
        self.ordplan = ordplan[ordplan["diff"] < self.filter_value].sort_values(by="กว้างผลิต").reset_index(drop=True) # filter out diff
            

    def set_selected_order(self):
        if not self.selector:
            return
        self.selected_order = self.ordplan[self.ordplan['เลขที่ใบสั่งขาย'] == self.selector['order_id']] #get selected order
        ordplan = self.ordplan[self.ordplan['เลขที่ใบสั่งขาย'] != self.selector['order_id']] #filter out selected order
        self.ordplan = pd.concat([self.selected_order, ordplan], ignore_index=True) #add selected order to the top row for GA
            
    def filter_common_order(self): 
        if not self.common:
            return
        ordplan = self.ordplan
        init_order = self.ordplan.iloc[0] # use first order as init
        
        init_order = self.set_filler_order(init_order)
        
        common_cols = COMMON_FILTER
        mask = ordplan[common_cols].eq(init_order[common_cols]).all(axis=1) #common mask
        self.ordplan = ordplan.loc[mask].reset_index(drop=True) #filter out with mask

    def set_filler_order(self,init_order):
        if not self.filler:
            return init_order
        ordplan = self.ordplan
        init_order = ordplan[ordplan['เลขที่ใบสั่งขาย'] == self.filler] #use filler as init instead
        self.ordplan = ordplan[ordplan['เลขที่ใบสั่งขาย'] != self.filler] #remove dupe filler
        return init_order


