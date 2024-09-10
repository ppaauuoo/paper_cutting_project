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
def test_common_order():
    test_data = pd.DataFrame(
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

    ord = ORD(test_data, size=66, common=True, no_build=True)
    ord.format_data()
    ord.filter_common_order()
    assert len(ord.ordplan) == 2


@pytest.mark.django_db
def test_filler_common_order():
    test_data = pd.DataFrame(
        {
            "id": ['1', '2', '3', '4', '5', '6', '7'],
            "width":     [66.04, 66.04, 66.04, 66.04, 80, 80, 0.0],
            "length":    [200.0, 200.0, 200.0, 200.0, 100.0, 100.0, 0],
            "due_date": [
                "08/01/23",
                "08/01/23",
                "08/05/23",
                "08/10/23",
                "08/15/23",
                "08/20/23",
                "02/21/22",
            ],
            "front_sheet":      [1, 1, 1, 1, 1, 1, 0],
            "c_wave":           [1, 2, 1, 1, 1, 1, 0],
            "middle_sheet":     [1, 1, 1, 1, 1, 1, 0],
            "b_wave":           [1, 1, 1, 1, 1, 1, 0],
            "back_sheet":       [1, 1, 1, 1, 1, 1, 0],
            "level":            [1, 1, 1, 1, 1, 1, 0],
            "edge_type":        [1, 1, 1, 1, 1, 1, 0],
            "left_edge_cut":    [1, 1, 1, 1, 1, 1, 0],
            "middle_edge_cut":  [1, 1, 2, 1, 1, 1, 0],
            "right_edge_cut":   [1, 1, 1, 1, 1, 1, 0],
            "component_type":   [1, 1, 1, 1, 1, 1, 0],
            "quantity":         [1, 1, 1, 1, 1, 1, 1],
        }
    )
    ord = ORD(test_data, size=80, common=True, filler='6', no_build=True)
    ord.format_data()
    ord.filter_common_order()
    assert len(ord.ordplan) == 1

@pytest.mark.django_db
def test_filler_not_found():
    test_data = pd.DataFrame(
        {
            "id": ['1', '2', '3', '4', '5', '6', '7'],
            "width":     [66.04, 66.04, 66.04, 66.04, 80, 80, 0.0],
            "length":    [200.0, 200.0, 200.0, 200.0, 100.0, 100.0, 0],
            "due_date": [
                "08/01/23",
                "08/01/23",
                "08/05/23",
                "08/10/23",
                "08/15/23",
                "08/20/23",
                "02/21/22",
            ],
            "front_sheet":      [1, 1, 1, 1, 1, 1, 0],
            "c_wave":           [1, 2, 1, 1, 1, 1, 0],
            "middle_sheet":     [1, 1, 1, 1, 1, 1, 0],
            "b_wave":           [1, 1, 1, 1, 1, 1, 0],
            "back_sheet":       [1, 1, 1, 1, 1, 1, 0],
            "level":            [1, 1, 1, 1, 1, 1, 0],
            "edge_type":        [1, 1, 1, 1, 1, 1, 0],
            "left_edge_cut":    [1, 1, 1, 1, 1, 1, 0],
            "middle_edge_cut":  [1, 1, 2, 1, 1, 1, 0],
            "right_edge_cut":   [1, 1, 1, 1, 1, 1, 0],
            "component_type":   [1, 1, 1, 1, 1, 1, 0],
            "quantity":         [1, 1, 1, 1, 1, 1, 1],
        }
    )
    ord = ORD(test_data, size=80, common=True, filler='8', no_build=True)
    ord.format_data()
    with pytest.raises(ValueError): 
        ord.filter_common_order()



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
            "front_sheet":  [2, 1, 2, 1, 1, 2, 0],
            "c_wave":       [2, 1, 1, 1, 2, 2, 0],
            "middle_sheet": [1, 1, 1, 1, 1, 1, 0],
            "b_wave":       [1, 1, 1, 1, 3, 1, 0],
            "back_sheet":   [3, 3, 1, 1, 1, 4, 0],
            "quantity":     [1, 1, 1, 1, 1, 1, 1],
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
            "front_sheet":  [2, 1, 2, 1, 1, 2, 0],
            "c_wave":       [2, 1, 1, 1, 2, 2, 0],
            "middle_sheet": [1, 1, 1, 1, 1, 1, 0],
            "b_wave":       [1, 1, 1, 1, 3, 1, 0],
            "back_sheet":   [3, 3, 1, 1, 1, 3, 0],
            "quantity":     [1, 1, 1, 1, 1, 1, 1],
        }
    )

    ord = ORD(test_data, size=66, no_build=True)
    ord.format_data()
    ord.legacy_filter_order()
    assert len(ord.ordplan) == 2
