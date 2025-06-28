import uuid
import pandas as pd
from typing import List

from order_optimization.models import CSVFile, OrderList
from ordplan_project.settings import CACHE_TIMEOUT, UNIT_CONVERTER

from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils import timezone


def set_csv_file(file_id: str) -> CSVFile:
    return get_object_or_404(CSVFile, id=file_id)


def set_progress(progress: float) -> None:
    """
    Update progress cache
    """
    cache.set("optimization_progress", progress, CACHE_TIMEOUT)


def set_model(file_id: str) -> None:
    """
    Extract data from file excel then creating a model with it.
    """
    csv_file = set_csv_file(file_id)
    # Read from Excel file and create new records
    data = pd.read_excel(csv_file.file.path, engine="openpyxl")
    order_instances: List[OrderList] = []

    for _, row in data.iterrows():
        try:
            due_date = timezone.make_aware(
                pd.to_datetime(row["กำหนดส่ง"], format="%m/%d/%y")
            )
        except (ValueError, TypeError):
            print(f"Warning: Could not parse due_date for order {row.get('เลขที่ใบสั่งขาย', 'N/A')}. Using current time.")
            due_date = timezone.now()

        order_id = f"{row['เลขที่ใบสั่งขาย'] }-{row['ชนิดส่วนประกอบ']}-{uuid.uuid4()}"

        order_instance = OrderList(
            id=order_id,
            due_date=due_date,
            front_sheet=row.get("แผ่นหน้า", "not defined"),
            c_wave=row.get("ลอน C", "not defined"),
            middle_sheet=row.get("แผ่นกลาง", "not defined"),
            b_wave=row.get("ลอน B", "not defined"),
            back_sheet=row.get("แผ่นหลัง", "not defined"),
            level=row.get("จน.ชั้น", 0),
            width=round(row.get("กว้างผลิต", 0) / UNIT_CONVERTER, 4),
            length=round(row.get("ยาวผลิต", 0) / UNIT_CONVERTER, 4),
            left_edge_cut=row.get("ทับเส้นซ้าย", 0),
            middle_edge_cut=row.get("ทับเส้นกลาง", 0),
            right_edge_cut=row.get("ทับเส้นขวา", 0),
            order_number=row.get("เลขที่ใบสั่งขาย", 0),
            component_type=row.get("ชนิดส่วนประกอบ", "not defined"),
            quantity=row.get("จำนวนสั่งขาย", 0),
            production_quantity=row.get("จำนวนสั่งผลิต", 0),
            edge_type=row.get("ประเภททับเส้น", "not defined"),
            order_status=row.get("สถานะใบสั่ง", "not defined"),
            excess_percentage=row.get("% ที่เกิน", 0),
            file=csv_file,
        )
        order_instances.append(order_instance)

    if order_instances:
        OrderList.objects.bulk_create(order_instances)
        orders = pd.DataFrame(list(OrderList.objects.filter(file=csv_file).values()))
        cache.set(f"order_cache_{file_id}", orders, CACHE_TIMEOUT)
    else:
        cache.set(f"order_cache_{file_id}", pd.DataFrame(), CACHE_TIMEOUT)
