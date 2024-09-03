import random
import pytest
import os
import pandas as pd
from django.test import Client
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

def test_functional(test_data):
    ord = ORD(orders=test_data, deadline_scope=1, size=66, tuning_values=3,
              filter_value = 16, _filter_diff=True, common=True,filler=True,selector={"order_id": 6},
              deadline_range  = 5,start_date=pd.to_datetime("08/1/23", format="%m/%d/%y"),
              stop_date=pd.to_datetime("08/20/23", format="%m/%d/%y"))
    assert len(ord.ordplan) == 2