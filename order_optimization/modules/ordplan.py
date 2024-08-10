import pandas as pd
from typing import Dict
class ORD:
    def __init__(self, path: str, deadline_scope: int = 0, size: float = 66, tuning_values: int = 3, filter_value: int = 16, filter: bool = True, common: bool = False, filler: int =0,selector: str = None) -> None:
        self.ordplan = pd.read_excel(path, engine='openpyxl')
        self.deadline_scope = deadline_scope
        self.filter = filter
        self.common = common
        self.size = size
        self.tuning_values = tuning_values
        self.filter_value = filter_value
        self.filler=filler
        self.selector=selector
    def get(self)-> Dict:
        ordplan = self.ordplan

        ordplan["กว้างผลิต"] = round(ordplan["กว้างผลิต"] / 25.4, 2)
        ordplan["ยาวผลิต"] = round(ordplan["ยาวผลิต"] / 25.4, 2)

        ordplan["กำหนดส่ง"] = pd.to_datetime(ordplan["กำหนดส่ง"]).dt.strftime('%m/%d/%y')
        ordplan.fillna(0, inplace=True)  # fix error values ex. , -> NA
        
        #filter deadline_scope
        if self.deadline_scope >= 0:
            deadline = ordplan["กำหนดส่ง"].iloc[self.deadline_scope]
            ordplan = ordplan[ordplan["กำหนดส่ง"] == deadline].reset_index(drop=True)

        #โดยออเดอร์ที่สามารถนำมาคู่กันได้ สำหรับกระดาษไซส์นี้ จะมีขนาดไม่เกิน 31(+-filter value) โดย filter value คือค่าที่กำหนดเอง
        if self.filter:
            #เอาไซส์กระดาษมาหารกับปริมาณการตัด เช่น กระดาษ 63 ถ้าตัดสองครั้งจได้ ~31 แล้วบันทึกเก็บไว้
            selected_values = self.size / self.tuning_values
            for i, row in ordplan.iterrows():
                diff = abs(selected_values - row["กว้างผลิต"])
                ordplan.loc[i, "diff"] = diff
            

            ordplan = (
                ordplan[ordplan["diff"] < self.filter_value].sort_values(by="กว้างผลิต").reset_index(drop=True)
            )

        if self.selector:
            self.selectorFilter()
            ordplan = ordplan[ordplan['เลขที่ใบสั่งขาย'] != self.selector]
            ordplan = pd.concat([self.selected_order, ordplan], ignore_index=True)

        if self.common:
            col = [
                "แผ่นหน้า",
                "ลอน C",
                "แผ่นกลาง",
                "ลอน B",
                "แผ่นหลัง",
                "จน.ชั้น",
                "ประเภททับเส้น",
            ]
                    # Filter based on the first order
            init_order = ordplan.iloc[0]
            if self.filler:
                init_order = ordplan[ordplan['เลขที่ใบสั่งขาย'] == self.filler]
                ordplan = ordplan[ordplan['เลขที่ใบสั่งขาย'] != self.filler]

            if isinstance(init_order, pd.Series):
                ordplan = ordplan[ordplan.apply(lambda order: all(init_order[i] == order[i] for i in col), axis=1)].reset_index(drop=True)

        self.ordplan = ordplan

        return ordplan

    def handle_orders_logic(output_data):
        init_len = output_data[0]['cut_len']
        init_out = output_data[0]['out']
        init_num_orders = output_data[0]['num_orders']

        foll_order_len = init_len
        if len(output_data) > 1:
            foll_order_len = output_data[1]['cut_len']

        init_order_number = round(init_num_orders/init_out)
        foll_order_number = round(init_len * init_order_number / foll_order_len)
        return (init_order_number,foll_order_number)

    def selectorFilter(self):
        self.selected_order = self.ordplan[self.ordplan['เลขที่ใบสั่งขาย'] == self.selector]
