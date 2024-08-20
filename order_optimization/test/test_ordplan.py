import pytest
import os
import pandas as pd
from django.test import Client
from ..modules.ordplan import ORD
from tempfile import NamedTemporaryFile
from icecream import ic

@pytest.fixture
def test_data():
    return pd.DataFrame({
        "order_number": [1, 2, 3, 4, 5, 6],
        "width": [66.04, 66.04, 66.04, 66.04, 80, 80],
        "length": [200.0, 200.0, 200.0, 200.0, 200.0, 100.0],
        "due_date": ["08/01/23", "08/01/23", "08/05/23", "08/10/23", "08/15/23", "08/20/23"],
        "front_sheet": [1, 1, 1, 1, 1, 1],
        "c_wave": [1, 2, 1, 1, 1, 1],
        "middle_sheet": [1, 1, 1, 1, 1, 1],
        "b_wave": [1, 1, 1, 1, 1, 1],
        "back_sheet": [1, 1, 1, 1, 1, 1],
        "level": [1, 1, 1, 1, 1, 1],
        "edge_type": [1, 1, 1, 1, 1, 1],
        "left_edge_cut": [1, 1, 1, 1, 1, 1],
        "middle_edge_cut": [1, 1, 2, 1, 1, 1],
        "right_edge_cut": [1, 1, 1, 1, 1, 1],
        "component_type": [1, 1, 1, 1, 1, 1]
    })

@pytest.fixture
def test_xlsx_file(test_data):
    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        test_data.to_excel(tmp_file.name, index=False)
        yield tmp_file.name
    os.remove(tmp_file.name)

@pytest.mark.django_db
def test_format_data(test_data):
    ord = ORD(test_data, no_build=True)
    ord.format_data()
    assert round(ord.ordplan["width"][0], 2) == 2.60
    assert round(ord.ordplan["length"][0], 2) == 7.87

@pytest.mark.django_db
def test_filter_diff_order_small(test_data):
    ord = ORD(test_data, size=66, tuning_values=1, filter_value=1,no_build=True)
    plan = ord.filter_diff_order(ord.ordplan)
    assert len(plan) == 4

@pytest.mark.django_db
def test_filter_diff_order_large(test_data):
    ord = ORD(test_data, size=66, tuning_values=1, filter_value=16,no_build=True)
    plan = ord.filter_diff_order(ord.ordplan)
    assert len(plan) == 6

@pytest.mark.django_db
def test_first_date(test_data):
    ord = ORD(test_data, size=66,  first_date_only=True,no_build=True, _filter_diff=False)
    ord.format_data()
    ord.set_first_date()
    assert len(ord.ordplan) == 2
    assert len(set(ord.ordplan["due_date"])) == 1

@pytest.mark.django_db
def test_selected_order(test_data):
    ord = ORD(test_data, size=66, selector={'order_id': 6},no_build=True)
    ord.format_data()
    ord.set_selected_order()
    assert ord.ordplan['order_number'][0] == 6

@pytest.mark.django_db
def test_common_order(test_data):
    ord = ORD(test_data, size=66, common=True,no_build=True)
    ord.format_data()
    ord.filter_common_order()
    assert len(ord.ordplan) == 2

@pytest.mark.django_db
def test_filler_common_order(test_data):
    ord = ORD(test_data, size=66, common=True, filler=6,no_build=True)
    ord.format_data()
    ord.filter_common_order()
    assert len(ord.ordplan) == 1


@pytest.mark.django_db
def test_expand_deadline_scope(test_data):
    ord = ORD(test_data, _filter_diff=False, no_build=True,deadline_range=3)
    ord.format_data()
    ord.expand_deadline_scope()
    assert len(ord.ordplan) == 3
    assert len(set(ord.ordplan["due_date"])) == 2
    


@pytest.mark.django_db
def test_expand_deadline_scope_nolimit(test_data):
    ord = ORD(test_data, _filter_diff=False, no_build=True,)
    ord.format_data()
    ord.expand_deadline_scope()
    assert len(ord.ordplan) == 6
    assert len(set(ord.ordplan["due_date"])) == 5

@pytest.mark.django_db
def test_no_rules(test_data):
    ord = ORD(test_data, _filter_diff=False, no_build=True, deadline_scope=-1)
    ord.format_data()
    ord.expand_deadline_scope()
    assert len(ord.ordplan) == 6
    assert len(set(ord.ordplan["due_date"])) == 5