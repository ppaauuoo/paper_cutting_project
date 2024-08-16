import pytest
import os
import pandas as pd
from django.test import Client
from ..modules.ga import GA
from tempfile import NamedTemporaryFile

@pytest.fixture
def test_data():
    return pd.DataFrame({
        "เลขที่ใบสั่งขาย": [1, 2, 3, 4, 5, 6],
        "กว้างผลิต": [66.04, 66.04, 66.04, 66.04, 80, 80],
        "ยาวผลิต": [200.0, 200.0, 200.0, 200.0, 200.0, 100.0],
        "กำหนดส่ง": ["08/01/23", "08/01/23", "08/05/23", "08/10/23", "08/15/23", "08/20/23"],
        "แผ่นหน้า": [1, 1, 1, 1, 1, 1],
        "ลอน C": [1, 2, 1, 1, 1, 1],
        "แผ่นกลาง": [1, 1, 1, 1, 1, 1],
        "ลอน B": [1, 1, 1, 1, 1, 1],
        "แผ่นหลัง": [1, 1, 1, 1, 1, 1],
        "จน.ชั้น": [1, 1, 1, 1, 1, 1],
        "ประเภททับเส้น": [1, 1, 1, 1, 1, 1],
        "ทับเส้นซ้าย": [1, 1, 1, 1, 1, 1],
        "ทับเส้นกลาง": [1, 1, 2, 1, 1, 1],
        "ทับเส้นขวา": [1, 1, 1, 1, 1, 1],
        "ชนิดส่วนประกอบ": [1, 1, 1, 1, 1, 1]
    })

@pytest.fixture
def test_xlsx_file(test_data):
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        test_data.to_excel(tmp_file.name, index=False)
        yield tmp_file.name
    os.remove(tmp_file.name)


@pytest.fixture
def test_solution():
    return [0,0,1,1,1,0,]

