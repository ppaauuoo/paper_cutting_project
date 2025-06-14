import pandas as pd
from rules import PackingTree

# Initialize packing configuration validator
packing_tree = PackingTree()
packing_tree.build_default_tree()

def validate_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Validate orders against packing configuration rules"""
    valid_orders = []
    for i in range(0, len(orders), 5):  # Process in packing-sized chunks
        chunk = orders.iloc[i:i+5].to_dict('records')
        if packing_tree.validate_configuration(chunk):
            valid_orders.extend(chunk)
    return pd.DataFrame(valid_orders)

# Read the Excel file
data = pd.read_excel('../data/order2024.xlsx', engine="openpyxl")

# Add ID column at the end
data['id'] = range(1, len(data)+1)

# Perform basic cleaning steps
# 1. Rename columns if necessary (assuming similar structure to order2024.xlsx)
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

# 2. Handle missing values
data.fillna(0, inplace=True)

# 3. Filter out rows with zero values in critical columns
data = data[(data['width'] != 0) & (data['length'] != 0)]
data['width'] = data['width'] * 24.5
data['length'] = data['length'] * 24.5

# Validate orders against packing configuration rules
data = validate_orders(data)

# 4. Convert data types if necessary
data['quantity'] = data['quantity'].astype(str).str.replace(',', '').astype(int)
data['production_quantity'] = data['production_quantity'].astype(str).str.replace(',', '').astype(int)

# Save the cleaned data to a new CSV file
data.to_csv('../data/cleaned_plan2024.csv', index=False, encoding='utf-8')

print("Plan2024.xlsx has been cleaned and saved as cleaned_plan2024.csv")
