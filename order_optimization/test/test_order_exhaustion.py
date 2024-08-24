from pandas import DataFrame
import pytest
import os
import pandas as pd
from django.test import Client
from modules.ga import GA
from tempfile import NamedTemporaryFile
from icecream import ic
import numpy as np

from order_optimization.handler import handle_order_exhaustion
from order_optimization.models import OrderList


@pytest.fixture
def test_data() -> DataFrame:
    return {
        "output": [{"order_number": 1}, {"order_number": 2}],
        "foll_order_number": 10,
    }

# def handle_order_exhaustion(data: Dict[str,List[Dict[str,int]]])->None:
#     output_data = data['output']

#     for index, order  in enumerate(output_data):
#         id = order['order_number']
#         filtered_order = OrderList.objects.filter(order_number=id).first()
#         new_value = data['foll_order_number'] - filtered_order.quantity
#         if index == 0:
#             new_value = 0
#         filtered_order.quantity = new_value
#         filtered_order.save()
#         filtered_order.quantity


@pytest.mark.django_db
def test_handle_order_exhaustion_valid_data(test_data, mocker):

    mock_order1 = mocker.Mock()
    mock_order1.quantity = 5
    mock_order2 = mocker.Mock()
    mock_order2.quantity = 17

    mocker.patch.object(
        OrderList.objects, "filter", side_effect=[[mock_order1], [mock_order2]]
    )

    handle_order_exhaustion(test_data)

    assert mock_order1.quantity == 0
    assert mock_order2.quantity == 7
    mock_order1.save.assert_called_once()
    mock_order2.save.assert_called_once()


@pytest.mark.django_db
def test_handle_order_exhaustion_many_data(mocker):

    data = {
        "output": [{"order_number": 1}, {"order_number": 2}, {"order_number": 3}],
        "foll_order_number": 10,
    }


    mock_order1 = mocker.Mock()
    mock_order1.quantity = 5
    mock_order2 = mocker.Mock()
    mock_order2.quantity = 17
    mock_order3 = mocker.Mock()
    mock_order3.quantity = 12

    mocker.patch.object(
        OrderList.objects, "filter", side_effect=[[mock_order1], [mock_order2], [mock_order3]]
    )

    handle_order_exhaustion(data)
    assert mock_order1.quantity == 0
    assert mock_order2.quantity == 7
    assert mock_order3.quantity == 2
    mock_order1.save.assert_called_once()
    mock_order2.save.assert_called_once()
    mock_order3.save.assert_called_once()

@pytest.mark.django_db
def test_handle_order_exhaustion_order_exceed(test_data, mocker):

    mock_order1 = mocker.Mock()
    mock_order1.quantity = 9
    mock_order2 = mocker.Mock()
    mock_order2.quantity = 3

    mocker.patch.object(
        OrderList.objects, "filter", side_effect=[[mock_order1], [mock_order2]]
    )

    with pytest.raises(ValueError):
        handle_order_exhaustion(test_data)