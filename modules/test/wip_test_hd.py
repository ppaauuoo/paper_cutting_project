import pytest
import pandas as pd
from modules.hd import HD


@pytest.fixture
def test_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6, 7],
            "width": [66.04, 66.04, 66.04, 66.04, 80, 80, 0.0],
            "length": [200.0, 200.0, 200.0, 200.0, 200.0, 100.0, 0],
            "due_date": [
                "08-01/2023",
                "08/01/2023",
                "08/05/2023",
                "08/10/2023",
                "08/15/2023",
                "08/20/2023",
                "02/21/2022",
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
            "quantity": [600, 600, 600, 600, 600, 600, 600],
        }
    )


@pytest.mark.django_db
def test_empty_data():
    test_data = pd.DataFrame(None)
    with pytest.raises(ValueError):
        HD(orders=test_data)


@pytest.mark.django_db
def test_format(test_data):
    hd_instance = HD(orders=test_data, is_build=False)
    test_data = hd_instance.format_data(test_data)
    assert len(test_data) == 6


@pytest.mark.django_db
def test_stop_data(test_data):
    start_date = pd.to_datetime("8/4/2023", format="%m/%d/%Y")
    stop_date = pd.to_datetime("8/14/2023", format="%m/%d/%Y")
    hd_instance = HD(
        orders=test_data, is_build=False, stop_date=stop_date, start_date=start_date
    )
    test_data = hd_instance.format_data(test_data)
    data = hd_instance.date_range_limit(test_data)
    assert len(data) == 2


@pytest.mark.django_db
def test_empty_start_date(test_data):
    stop_date = pd.to_datetime("8/14/2023", format="%m/%d/%Y")
    hd_instance = HD(orders=test_data, is_build=False, stop_date=stop_date)
    test_data = hd_instance.format_data(test_data)
    data = hd_instance.date_range_limit(test_data)
    assert len(data) == 6
