import pandas as pd
import pytest

from modules.ordplan import ORD

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
def test_expand_deadline_scope(test_data):
    ord = ORD(test_data, _filter_diff=False, no_build=True, deadline_range=3)
    ord.format_data()
    ord.expand_deadline_scope()
    assert len(ord.ordplan) == 3
    assert len(set(ord.ordplan["due_date"])) == 2


@pytest.mark.django_db
def test_expand_deadline_scope_nolimit(test_data):
    ord = ORD(
        test_data,
        _filter_diff=False,
        no_build=True,
    )
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


@pytest.mark.django_db
def test_positive_deadline_scope():
    data = {"due_date": ["01/01/23", "01/02/23", "01/03/23"], "width": [10, 20, 30]}
    ordplan = pd.DataFrame(data)
    ord = ORD(ordplan, no_build=True)
    ord.deadline_scope = 1
    ord.start_date = pd.to_datetime("01/01/23", format="%m/%d/%y")
    ord.stop_date = pd.to_datetime("01/03/23", format="%m/%d/%y")
    ord.expand_deadline_scope()
    assert len(ord.ordplan) == 3
    assert ord.ordplan["due_date"].iloc[0] <= pd.to_datetime(
        "01/03/23", format="%m/%d/%y"
    )

@pytest.mark.django_db
def test_start_further():
    data = {"due_date": ["01/01/22", "01/02/23", "01/03/23"], "width": [10, 20, 30]}
    ordplan = pd.DataFrame(data)
    ord = ORD(ordplan, no_build=True)
    ord.deadline_scope = 1
    ord.start_date = pd.to_datetime("01/02/23", format="%m/%d/%y")
    ord.stop_date = pd.to_datetime("01/03/23", format="%m/%d/%y")
    ord.expand_deadline_scope()
    assert len(ord.ordplan) == 2
    assert ord.ordplan["due_date"].iloc[0] <= pd.to_datetime(
        "01/03/23", format="%m/%d/%y"
    )

@pytest.mark.django_db
def test_start_stop_earlier():
    data = {"due_date": ["01/01/22", "01/02/22", "01/02/23","01/03/23"], "width": [10, 20, 30, 40]}
    ordplan = pd.DataFrame(data)
    ord = ORD(ordplan, no_build=True)
    ord.deadline_scope = 1
    ord.start_date = pd.to_datetime("01/02/22", format="%m/%d/%y")
    ord.stop_date = pd.to_datetime("01/02/23", format="%m/%d/%y")
    ord.expand_deadline_scope()
    assert len(ord.ordplan) == 2
    assert ord.ordplan["due_date"].iloc[0] <= pd.to_datetime(
        "01/03/23", format="%m/%d/%y"
    )