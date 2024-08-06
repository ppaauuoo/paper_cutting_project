import pandas as pd

class ORD:
    def __init__(self, path, deadline_scope, size, tuning_values, filter_value, filter=None, common=None, auto=None):
        self.deadline_scope = deadline_scope
        self.ordplan = pd.read_csv(path, header=None)
        self.filter = True if filter is None else filter
        self.common = False if common is None else common
        self.auto = False if auto is None else auto

        self.size = size
        self.tuning_values = tuning_values
        self.filter_value = filter_value

    def get(self):
        ordplan = self.ordplan

        col_to_drop = (
            list(range(9, 12))
            + list(range(13, 14))
            + list(range(15, 18))
            + list(range(19, 26))
        )
        ordplan = ordplan.drop(columns=col_to_drop, axis=1)

        col = [
            "กำหนดส่ง",
            "แผ่นหน้า",
            "ลอน C",
            "แผ่นกลาง",
            "ลอน B",
            "แผ่นหลัง",
            "จำนวนชั้น",
            "ตัดกว้าง",
            "ตัดยาว",
            "เลขที่ใบสั่งขาย",
            "จำนวนสั่งขาย",
            "ประเภททับเส้น",
        ]
        ordplan.columns = col

        new_col = ["เลขที่ใบสั่งขาย"] + [
            col for col in ordplan.columns if col != "เลขที่ใบสั่งขาย"
        ]
        ordplan = ordplan.reindex(columns=new_col)
        ordplan["เลขที่ใบสั่งขาย"] = (
            ordplan["เลขที่ใบสั่งขาย"].astype(str).str.replace("121811", "x")
        )

        ordplan = ordplan[
            (ordplan["ตัดกว้าง"] != 0) & (ordplan["ตัดยาว"] != 0)
        ]  # filter out zero values -> index misaligned

        ordplan["ตัดกว้าง"] = round(ordplan["ตัดกว้าง"] / 25.4, 4)
        ordplan["ตัดยาว"] = round(ordplan["ตัดยาว"] / 25.4, 4)

        ordplan["จำนวนสั่งขาย"] = ordplan["จำนวนสั่งขาย"].str.replace(
            ",", ""
        )  # fix error values ex. 10,00 -> 1000
        ordplan.fillna(0, inplace=True)  # fix error values ex. , -> NA
        ordplan["จำนวนสั่งขาย"] = ordplan["จำนวนสั่งขาย"].astype(int)  # turns str -> int

        #filter deadline_scope
        if self.deadline_scope >= 0:
            deadline = ordplan["กำหนดส่ง"].iloc[self.deadline_scope]
            ordplan = ordplan[ordplan["กำหนดส่ง"] == deadline]
        ordplan = ordplan.reset_index(drop=True)

        self.ordplan = ordplan

        return self.prep()


    def prep(self):
        orders = self.ordplan

        #เอาไซส์กระดาษมาหารกับปริมาณการตัด เช่น กระดาษ 63 ถ้าตัดสองครั้งจได้ ~31 แล้วบันทึกเก็บไว้
        if self.auto:
            selected_values = self.ordplan["ตัดกว้าง"].loc[0] / (3 if self.ordplan["ตัดกว้าง"].loc[0] > 80 else 2)
        else:
            selected_values = self.size / self.tuning_values



        for i, row in orders.iterrows():
            diff = abs(selected_values - row["ตัดกว้าง"])
            orders.loc[i, "diff"] = diff

        #โดยออเดอร์ที่สามารถนำมาคู่กันได้ สำหรับกระดาษไซส์นี้ จะมีขนาดไม่เกิน 31(+-filter value) โดย filter value คือค่าที่กำหนดเอง
        new_orders = orders
        if self.filter:
            new_orders = (
                orders[orders["diff"] < self.filter_value].sort_values(by="ตัดกว้าง").reset_index(drop=True)
            )

        if self.common:
            # Filter based on the first order
            init_order = new_orders.iloc[0]
            new_orders = new_orders[new_orders.apply(lambda order: all(init_order[i] == order[i] for i in [3, 4, 5, 6, 7, 8, 12]), axis=1)]

        return new_orders



