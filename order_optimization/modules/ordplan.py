import pandas as pd

class ORD:
    def __init__(self, path, deadline_scope, size, tuning_values, filter_value, filter=None):
        self.deadline_scope = deadline_scope
        self.ordplan = pd.read_csv(path, header=None)
        self.filter = True if filter is None else filter
        self.size = size
        self.tuning_values = tuning_values
        self.filter_value = filter_value

    def prep(self):
        orders = self.ordplan

        #เอาไซส์กระดาษมาหารกับปริมาณการตัด เช่น กระดาษ 63 ถ้าตัดสองครั้งจได้ ~31 แล้วบันทึกเก็บไว้
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
        # print(new_orders)


        temp = []

        #filter โดนยึดจากอันแรก
        # init_order = new_orders.iloc[0]
        # for i, order in new_orders.iterrows():
        #     if all(init_order[i] == order[i] for i in [2, 3, 4, 5, 6, 7, 11]):
        #         # if init_order[11] == order[11]:
        #         temp.append(order)

        temp = new_orders

        temp = pd.DataFrame(temp)

        return temp

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

    def calculate_trim_and_roll(width):
        roll_paper = [68, 73, 75, 79, 82, 85, 88, 91, 95, 97]
        trim_min = 1
        trim_max = 3
        trim = [paper - width for paper in roll_paper]
        valid_trim_values = [t for t in trim if trim_min <= t <= trim_max]

        if valid_trim_values:
            roll = roll_paper[trim.index(valid_trim_values[0])]
            return valid_trim_values[0], int(roll)
        else:
            return None, None

    def calculate_roll(width):
        roll_paper = [68, 73, 75, 79, 82, 85, 88, 91, 95, 97]
        trim_min = 1
        trim_max = 3
        roll = None
        for i in range(1, 4):
            trim = [paper - width * i for paper in roll_paper]
            valid_trim_values = [t for t in trim if trim_min <= t <= trim_max]

            if valid_trim_values:
                roll = roll_paper[trim.index(valid_trim_values[0])]

        return roll

    def calculate_roll_tuning(width, tuning_values):
        roll_paper = [68, 73, 75, 79, 82, 85, 88, 91, 95, 97]
        trim_min = 1
        trim_max = 3
        roll = None
        trim = [paper - width * tuning_values for paper in roll_paper]
        valid_trim_values = [t for t in trim if trim_min <= t <= trim_max]

        if valid_trim_values:
            roll = roll_paper[trim.index(valid_trim_values[0])]
        return roll

    def calculate_roll_and_width(paper, width):
        trim_min = 1
        trim_max = 3
        if trim_min <= paper - width <= trim_max:
            return False
        return True

    def check_roll_compat(self, var, i, orders, PAPER_SIZE):
        if var:  # ถ้า var = 0 False
            if ORD.calculate_roll_and_width(
                PAPER_SIZE, 2 * orders.loc[i, "ตัดกว้าง"]
            ):  # ถ้า width *2 แล้วผ่าน False
                if ORD.calculate_roll_and_width(
                    PAPER_SIZE, 3 * orders.loc[i, "ตัดกว้าง"]
                ):  # ถ้า width *3 แล้วผ่าน False
                    if ORD.calculate_roll_and_width(
                        PAPER_SIZE, 4 * orders.loc[i, "ตัดกว้าง"]
                    ):  # ถ้า width *4 แล้วผ่าน False
                        if ORD.calculate_roll_and_width(
                            PAPER_SIZE, 5 * orders.loc[i, "ตัดกว้าง"]
                        ):  # ถ้า width *5 แล้วผ่าน False
                            if ORD.calculate_roll_and_width(
                                PAPER_SIZE, 6 * orders.loc[i, "ตัดกว้าง"]
                            ):  # ถ้า width *6 แล้วผ่าน False ex. 4*6 = 24 > 22-24 = -2
                                return abs(PAPER_SIZE * 2)
        return 0
