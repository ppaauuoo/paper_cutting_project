import pytest
import os
import pandas as pd
from django.test import Client
from ..modules.ordplan import ORD
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

@pytest.mark.django_db
def test_format_data(test_xlsx_file):
    ord = ORD(test_xlsx_file)
    ord.format_data()
    assert round(ord.ordplan["กว้างผลิต"][0], 2) == 2.60
    assert round(ord.ordplan["ยาวผลิต"][0], 2) == 7.87
    assert ord.ordplan["กำหนดส่ง"][0] == "08/01/23"

@pytest.mark.django_db
def test_filter_diff_order(test_xlsx_file):
    ord = ORD(test_xlsx_file, size=66, tuning_values=1, filter_value=1)
    ord.filter_diff_order()
    assert len(ord.ordplan) == 4

@pytest.mark.django_db
def test_filter_diff_order(test_xlsx_file):
    ord = ORD(test_xlsx_file, size=66, tuning_values=1, filter_value=16)
    ord.filter_diff_order()
    assert len(ord.ordplan) == 6

@pytest.mark.django_db
def test_expand_deadline_scope(test_xlsx_file):
    ord = ORD(test_xlsx_file, size=66, tuning_values=1, filter_value=16, deadline_scope=0)
    ord.format_data()
    ord.expand_deadline_scope()
    assert len(ord.ordplan) == 6
    assert len(set(ord.ordplan["กำหนดส่ง"])) == 5




@pytest.mark.django_db
def test_first_date(test_xlsx_file):
    ord = ORD(test_xlsx_file, size=66,  first_date_only=True)
    ord.format_data()
    ord.set_first_date()
    assert len(ord.ordplan) == 2
    assert len(set(ord.ordplan["กำหนดส่ง"])) == 1

@pytest.mark.django_db
def test_selected_order(test_xlsx_file):
    ord = ORD(test_xlsx_file, size=66, selector={'order_id': 6})
    ord.format_data()
    ord.set_selected_order()
    assert ord.ordplan['เลขที่ใบสั่งขาย'][0] == 6

@pytest.mark.django_db
def test_common_order(test_xlsx_file):
    ord = ORD(test_xlsx_file, size=66, common=True)
    ord.format_data()
    ord.filter_common_order()
    assert len(ord.ordplan) == 2

@pytest.mark.django_db
def test_common_order(test_xlsx_file):
    ord = ORD(test_xlsx_file, size=66, common=True, filler=6)
    ord.format_data()
    ord.filter_common_order()
    assert len(ord.ordplan) == 1
