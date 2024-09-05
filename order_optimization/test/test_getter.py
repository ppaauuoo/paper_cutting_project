# Retrieves orders from cache if available with an integer file_id, using the @pytest.mark.django_db decorator

import uuid
import pandas as pd
import pytest
from django.core.cache import cache

from order_optimization.getter import get_orders_cache
from order_optimization.models import CSVFile


# Retrieves orders from cache when available
@pytest.mark.django_db
def test_retrieves_orders_from_cache(mocker):
    file_id = "test_file_id"
    expected_orders = pd.DataFrame(
        {"order_number": [1, 2], "due_date": ["01/01/23", "02/01/23"]}
    )

    mocker.patch("django.core.cache.cache.get", return_value=expected_orders)
    mocker.patch("order_optimization.getter.PLAN_RANGE", 1)

    orders = get_orders_cache(file_id)

    assert not orders.empty
    assert orders.equals(expected_orders)
