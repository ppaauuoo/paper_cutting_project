# Retrieves orders from cache if available with an integer file_id, using the @pytest.mark.django_db decorator

import pandas as pd
import pytest
from django.core.cache import cache

from order_optimization.getter import get_orders_cache, set_orders_model
from order_optimization.models import CSVFile


@pytest.mark.django_db
def test_orders_cache(mocker):
    file_id = 1
    expected_orders = pd.DataFrame(
        {"order_number": [1, 2], "due_date": ["01/01/23", "02/01/23"]}
    )
    mock_csv = mocker.Mock()
    mock_csv.file.path = "test_path"

    mocker.patch("order_optimization.getter.get_csv_file", return_value=mock_csv)
    mocker.patch("django.core.cache.cache.get", return_value=expected_orders)

    orders = get_orders_cache(file_id)

    assert not orders.empty
    assert orders.equals(expected_orders)


@pytest.mark.django_db
def test_orders_nocache(mocker):
    file_id = 1
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


@pytest.fixture
def create_mock_order_data():
    # Create a sample DataFrame that mimics your Excel file structure
    mock_excel_data = pd.DataFrame(
        {
            "เลขที่ใบสั่งขาย": [1, 2],
            "ชนิดส่วนประกอบ": ["TYPE1", "TYPE2"],
            "กำหนดส่ง": ["01/01/23", "02/01/23"],
            "แผ่นหน้า": ["FRONT1", "FRONT2"],
            "ลอน C": ["C1", "C2"],
            "แผ่นกลาง": ["MIDDLE1", "MIDDLE2"],
            "ลอน B": ["B1", "B2"],
            "แผ่นหลัง": ["BACK1", "BACK2"],
            "จน.ชั้น": [1, 2],
            "กว้างผลิต": [100, 200],
            "ยาวผลิต": [300, 400],
            "ทับเส้นซ้าย": [10, 20],
            "ทับเส้นกลาง": [15, 25],
            "ทับเส้นขวา": [20, 30],
            "จำนวนสั่งขาย": [1000, 2000],
            "จำนวนสั่งผลิต": [1100, 2200],
            "ประเภททับเส้น": ["TYPE_A", "TYPE_B"],
            "สถานะใบสั่ง": ["PENDING", "COMPLETED"],
            "% ที่เกิน": [10, 15],
        }
    )

    return mock_excel_data


@pytest.mark.django_db
def test_set_orders_model(mocker):
    # Mock the get_csv_file function
    mock_csv_file = mocker.patch("order_optimization.getter.get_csv_file")
    mock_csv_file.return_value = CSVFile(id='123', file="test_path")

    # Mock the pd.read_excel function
    mock_read_excel = mocker.patch("pandas.read_excel")
    mock_read_excel.return_value = pd.DataFrame(
        {
            "กำหนดส่ง": ["01/01/23"],
            "เลขที่ใบสั่งขาย": [123],
            "ชนิดส่วนประกอบ": ["A"],
            "แผ่นหน้า": ["front"],
            "ลอน C": ["C"],
            "แผ่นกลาง": ["middle"],
            "ลอน B": ["B"],
            "แผ่นหลัง": ["back"],
            "จน.ชั้น": [1],
            "กว้างผลิต": [100],
            "ยาวผลิต": [200],
            "ทับเส้นซ้าย": [10],
            "ทับเส้นกลาง": [20],
            "ทับเส้นขวา": [30],
            "จำนวนสั่งขาย": [1000],
            "จำนวนสั่งผลิต": [900],
            "ประเภททับเส้น": ["type"],
            "สถานะใบสั่ง": ["status"],
            "% ที่เกิน": [5],
        }
    )

    # Call the function under test
    set_orders_model(123)

    # Assert that the CSV file was retrieved
    mock_csv_file.assert_called_once_with(123)
