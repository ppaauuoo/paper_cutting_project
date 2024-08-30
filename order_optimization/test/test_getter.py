# Retrieves orders from cache if available with an integer file_id, using the @pytest.mark.django_db decorator

import uuid
import pandas as pd
import pytest
from django.core.cache import cache

from order_optimization.getter import get_orders_cache, set_orders_model
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


@pytest.mark.django_db
def test_orders_nocache(mocker):
    file_id = "1"
    expected_orders = pd.DataFrame(
        {"order_number": [1, 2], "due_date": ["01/01/23", "02/01/23"]}
    )
    mock_csv = mocker.Mock()
    mock_csv.file.path = "test_path"

    # Create a mock for the QuerySet
    mock_queryset = mocker.Mock()
    # Set up the values method to return a list of dictionaries
    mock_queryset.values.return_value = [
        {"order_number": 1, "due_date": "01/01/23"},
        {"order_number": 2, "due_date": "02/01/23"},
    ]

    mocker.patch("django.core.cache.cache.get", return_value=None)
    mocker.patch("order_optimization.getter.get_csv_file", return_value=mock_csv)
    mocker.patch(
        "order_optimization.models.OrderList.objects.filter", return_value=mock_queryset
    )

    orders = get_orders_cache(file_id)

    assert not orders.empty
    assert orders.equals(expected_orders)
