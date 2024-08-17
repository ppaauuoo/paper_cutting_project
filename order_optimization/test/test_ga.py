from pandas import DataFrame
import pytest
import os
import pandas as pd
from django.test import Client
from ..modules.ga import GA
from tempfile import NamedTemporaryFile
from icecream import ic

@pytest.fixture
def test_data() -> DataFrame:
    return pd.DataFrame({
        "เลขที่ใบสั่งขาย": [1, 2, 3, 4, 5],
        "จำนวนสั่งขาย": [100, 200, 1500, 500, 250],
        "ชนิดส่วนประกอบ": ["A", "B", "C", "D", "E"],
        "กว้างผลิต": [66.04, 66.04, 66.04, 66.04, 80],
        "ยาวผลิต": [200.0, 200.0, 200.0, 200.0, 200.0],
        "ประเภททับเส้น": ["X", "N", "W", "X", "Y"],
        "กำหนดส่ง": ["08/01/23", "08/01/23", "08/05/23", "08/10/23", "08/15/23"],
        "แผ่นหน้า": ["P1", "P2", "P3", "P4", "P5"],
        "ลอน C": ["C1", "C2", "C3", "C4", "C5"],
        "แผ่นกลาง": ["M1", "M2", "M3", "M4", "M5"],
        "ลอน B": ["B1", "B2", "B3", "B4", "B5"],
        "แผ่นหลัง": ["B1", "B2", "B3", "B4", "B5"],
        "จน.ชั้น": [1, 2, 3, 1, 2],
        "ทับเส้นซ้าย": [0, 1, 0, 1, 0],
        "ทับเส้นกลาง": [1, 0, 1, 0, 1],
        "ทับเส้นขวา": [0, 1, 0, 1, 0],
    })


@pytest.mark.django_db
def test_ga(test_data):
    ga_instance = GA(test_data)
    ga_instance.get().run()
    ic(ga_instance.output())



