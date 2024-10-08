import random
import pytest
import os
import pandas as pd
from django.test import Client
from modules.ordplan import ORD
from tempfile import NamedTemporaryFile
from icecream import ic


@pytest.fixture
def test_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6, 7],
            "width": [66.04, 66.04, 66.04, 66.04, 80, 80, 0.0],
            "length": [200.0, 200.0, 200.0, 200.0, 200.0, 100.0, 0],
            "due_date": [
                "08/01/23",
                "08/01/23",
                "08/05/23",
                "08/10/23",
                "08/15/23",
                "08/20/23",
                "02/21/22",
            ],
            "front_sheet": [1, 1, 1, 1, 1, 1, 0],
            "c_wave": [1, 2, 1, 1, 1, 1, 0],
            "middle_sheet": [1, 1, 1, 1, 1, 1, 0],
            "b_wave": [1, 1, 1, 1, 1, 1, 0],
            "back_sheet": [1, 1, 1, 1, 1, 1, 0],
            "level": [1, 1, 1, 1, 1, 1, 0],
            "edge_type": [1, 1, 1, 1, 1, 1, 0],
            "left_edge_cut": [1, 1, 1, 1, 1, 1, 0],
            "middle_edge_cut": [1, 1, 2, 1, 1, 1, 0],
            "right_edge_cut": [1, 1, 1, 1, 1, 1, 0],
            "component_type": [1, 1, 1, 1, 1, 1, 0],
            "quantity": [1, 1, 1, 1, 1, 1, 1],
        }
    )


@pytest.mark.django_db
def test_format_data(test_data: pd.DataFrame):
    ord = ORD(test_data, no_build=True)
    ord.format_data()
    assert round(ord.ordplan["width"][0], 2) == 66.04
    assert round(ord.ordplan["length"][0], 2) == 200.0
    assert len(ord.ordplan) == 6


@pytest.mark.django_db
def test_filter_diff_order_small(test_data):
    ord = ORD(test_data, size=66, tuning_values=1, filter_value=1, no_build=True)
    plan = ord.filter_diff_order(ord.ordplan)
    assert len(plan) == 4


@pytest.mark.django_db
def test_filter_diff_order_large(test_data):
    ord = ORD(test_data, size=66, tuning_values=1, filter_value=16, no_build=True)
    plan = ord.filter_diff_order(ord.ordplan)
    assert len(plan) == 6


@pytest.mark.django_db
def test_first_date(test_data):
    ord = ORD(
        test_data, size=66, first_date_only=True, no_build=True, _filter_diff=False
    )
    ord.format_data()
    ord.set_first_date()
    assert len(ord.ordplan) == 2
    assert len(set(ord.ordplan["due_date"])) == 1


@pytest.mark.django_db
def test_selected_order(test_data):
    ord = ORD(test_data, size=66, selector={"order_id": 6}, no_build=True)
    ord.format_data()
    ord.set_selected_order()
    assert ord.ordplan["id"][0] == 6


@pytest.mark.django_db
def test_filter_common_order_with_common_true():
    data = {
        "front_sheet": ["A", "A", "A", "C", "C", "D"],
        "c_wave":       ["X", "X", "X", "Z", "Z", "W"],
        "middle_sheet": ["M", "M", "M", "O", "O", "P"],
        "b_wave":       ["W", "W", "W", "Y", "Y", "X"],
        "back_sheet":   ["B", "B", "B", "D", "D", "E"],
        "edge_type":    ["E1", "E1", "E1", "E3", "E3", "E4"],
        "width":        [100, 150, 100, 150, 150, 250],
        "length":       [200, 250, 200, 250, 250, 350],
        "left_edge_cut": [1, 1, 1, 1, 1, 2],
        "middle_edge_cut": [1, 1, 1, 1, 1, 2],
        "right_edge_cut": [1, 1, 1, 1, 1, 2],
        "component_type": ["T1", "T1", "T1", "T3", "T3", "T4"],
    }
    init_data = {
        "front_sheet": ["A"],
        "c_wave": ["X"],
        "middle_sheet": ["M"],
        "b_wave": ["W"],
        "back_sheet": ["B"],
        "edge_type": ["E1"],
        "width": [100],
        "length": [200],
        "left_edge_cut": [1],
        "middle_edge_cut": [1],
        "right_edge_cut": [1],
        "component_type": ["T1"],
    }
    
    ordplan_df = pd.DataFrame(data)
    ord = ORD(ordplan_df, no_build=True)
    ord.common = True
    ord.common_init_order = init_data
    ord.filter_common_order()
    assert len(ord.ordplan) == 2

@pytest.mark.django_db
def test_filter_common_order_with_common_true_2():
    data = {
        "front_sheet":      ["A", "A", "C", "C", "C", "D"],
        "c_wave":           ["X", "X", "Z", "Z", "Z", "W"],
        "middle_sheet":     ["M", "M", "O", "O", "O", "P"],
        "b_wave":           ["W", "W", "Y", "Y", "Y", "X"],
        "back_sheet":       ["B", "B", "D", "D", "D", "E"],
        "edge_type":        ["E1", "E1", "E3", "E3", "E3", "E4"],
        "width":            [100, 150, 100, 150, 150, 250],
        "length":           [200, 250, 200, 250, 250, 350],
        "left_edge_cut":    [1, 1, 1, 1, 1, 2],
        "middle_edge_cut":  [1, 1, 1, 1, 1, 2],
        "right_edge_cut":   [1, 1, 1, 1, 1, 2],
        "component_type":   ["T1", "T1", "T3", "T3", "T3", "T4"],
    }
    init_data = {
        "front_sheet": ["C"],
        "c_wave": ["Z"],
        "middle_sheet": ["O"],
        "b_wave": ["Y"],
        "back_sheet": ["D"],
        "edge_type": ["E3"],
        "width": [100],
        "length": [200],
        "left_edge_cut": [1],
        "middle_edge_cut": [1],
        "right_edge_cut": [1],
        "component_type": ["T3"],
    }
    
    ordplan_df = pd.DataFrame(data)
    ord = ORD(ordplan_df, no_build=True)
    ord.common = True
    ord.common_init_order = init_data
    ord.filter_common_order()
    assert len(ord.ordplan) == 2

@pytest.mark.django_db
def test_legacy():
    test_data = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6, 7],
            "width": [66.04, 67.04, 68.04, 69.04, 80, 80, 0.0],
            "length": [190.0, 200.0, 210.0, 220.0, 200.0, 100.0, 0],
            "due_date": [
                "08/01/23",
                "08/01/23",
                "08/05/23",
                "08/10/23",
                "08/15/23",
                "08/20/23",
                "02/21/22",
            ],
            "front_sheet": [1, 1, 1, 1, 1, 1, 0],
            "c_wave": [1, 1, 1, 1, 1, 1, 0],
            "middle_sheet": [1, 1, 1, 1, 1, 1, 0],
            "b_wave": [1, 1, 1, 1, 1, 1, 0],
            "back_sheet": [1, 1, 1, 1, 1, 1, 0],
            "level": [1, 1, 1, 1, 1, 1, 0],
            "edge_type": [1, 1, 1, 1, 1, 1, 0],
            "left_edge_cut": [1, 1, 1, 1, 1, 1, 0],
            "middle_edge_cut": [1, 1, 1, 1, 1, 1, 0],
            "right_edge_cut": [1, 1, 1, 1, 1, 1, 0],
            "component_type": [1, 1, 1, 1, 1, 1, 0],
            "quantity": [1, 1, 1, 1, 1, 1, 1],
        }
    )
    ord = ORD(test_data, size=66, no_build=True)
    ord.format_data()
    ord.legacy_filter_order()
    assert len(ord.ordplan) == 6


@pytest.mark.django_db
def test_legacy_restriction_first_only():
    test_data = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6, 7],
            "width": [66.04, 67.04, 68.04, 69.04, 80, 80, 0.0],
            "length": [190.0, 200.0, 210.0, 220.0, 200.0, 100.0, 0],
            "due_date": [
                "08/01/23",
                "08/01/23",
                "08/05/23",
                "08/10/23",
                "08/15/23",
                "08/20/23",
                "02/21/22",
            ],
            "front_sheet": [2, 1, 2, 1, 1, 2, 0],
            "c_wave": [2, 1, 1, 1, 2, 2, 0],
            "middle_sheet": [1, 1, 1, 1, 1, 1, 0],
            "b_wave": [1, 1, 1, 1, 3, 1, 0],
            "back_sheet": [3, 3, 1, 1, 1, 4, 0],
            "quantity": [1, 1, 1, 1, 1, 1, 1],
        }
    )

    ord = ORD(test_data, size=66, no_build=True)
    ord.format_data()
    ord.legacy_filter_order()
    assert len(ord.ordplan) == 1


@pytest.mark.django_db
def test_legacy_restriction_fist_last():
    test_data = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6, 7],
            "width": [66.04, 67.04, 68.04, 69.04, 80, 80, 0.0],
            "length": [190.0, 200.0, 210.0, 220.0, 200.0, 100.0, 0],
            "due_date": [
                "08/01/23",
                "08/01/23",
                "08/05/23",
                "08/10/23",
                "08/15/23",
                "08/20/23",
                "02/21/22",
            ],
            "front_sheet": [2, 1, 2, 1, 1, 2, 0],
            "c_wave": [2, 1, 1, 1, 2, 2, 0],
            "middle_sheet": [1, 1, 1, 1, 1, 1, 0],
            "b_wave": [1, 1, 1, 1, 3, 1, 0],
            "back_sheet": [3, 3, 1, 1, 1, 3, 0],
            "quantity": [1, 1, 1, 1, 1, 1, 1],
        }
    )

    ord = ORD(test_data, size=66, no_build=True)
    ord.format_data()
    ord.legacy_filter_order()
    assert len(ord.ordplan) == 2
