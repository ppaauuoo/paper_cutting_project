import pandas as pd

class ORD:
        def __init__(self,path,deadline_scope):
                self.deadline_scope = deadline_scope
                self.ordplan = pd.read_csv(path, header=None)
                        
        def get(self,deadline):
                ordplan = self.ordplan
                
                col_to_drop = list(range(9, 12)) + list(range(13, 14)) + \
                        list(range(15, 18)) + list(range(19, 26))
                ordplan = ordplan.drop(columns=col_to_drop, axis=1)

                col = ['กำหนดส่ง', 'แผ่นหน้า', 'ลอน C', 'แผ่นกลาง',
                        'ลอน B', 'แผ่นหลัง', 'จำนวนชั้น', 'ตัดกว้าง', 'ตัดยาว',
                        'เลขที่ใบสั่งขาย', 'จำนวนสั่งขาย', 'ประเภททับเส้น']
                ordplan.columns = col

                new_col = ['เลขที่ใบสั่งขาย'] + \
                        [col for col in ordplan.columns if col != 'เลขที่ใบสั่งขาย']
                ordplan = ordplan.reindex(columns=new_col)
                ordplan['เลขที่ใบสั่งขาย'] = ordplan['เลขที่ใบสั่งขาย'].astype(
                        str).str.replace('121811', 'x')
                        
                ordplan = ordplan[(ordplan['ตัดกว้าง'] != 0) & (ordplan['ตัดยาว'] != 0)] #filter out zero values -> index misaligned

                ordplan['ตัดกว้าง'] = round(ordplan['ตัดกว้าง'] / 25.4, 4)
                ordplan['ตัดยาว'] = round(ordplan['ตัดยาว'] / 25.4, 4)
                        
                ordplan['จำนวนสั่งขาย'] = ordplan['จำนวนสั่งขาย'].str.replace(',', '') #fix error values ex. 10,00 -> 1000
                ordplan.fillna(0, inplace=True) #fix error values ex. , -> NA
                ordplan['จำนวนสั่งขาย'] = ordplan['จำนวนสั่งขาย'].astype(int) #turns str -> int
                
                if(deadline):
                        deadline = ordplan['กำหนดส่ง'].iloc[self.deadline_scope]
                        ordplan = ordplan[ordplan['กำหนดส่ง'] == deadline]
                ordplan = ordplan.reset_index(drop=True)

                return ordplan
                


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
                        for i in range(1, 7):
                                trim = [paper - width*i for paper in roll_paper]
                                valid_trim_values = [t for t in trim if trim_min <= t <= trim_max]
        
                                if valid_trim_values:
                                        roll = roll_paper[trim.index(valid_trim_values[0])]

                        return roll
                        
        def calculate_roll_and_width(paper,width):
                        trim_min = 1
                        trim_max = 3                        
                        if trim_min <= paper-width <= trim_max: return False
                        return True
                                