from typing import Dict, List
import uuid

from django.shortcuts import get_object_or_404
import pandas as pd

from order_optimization.models import CSVFile, OrderList
from ordplan_project.settings import CACHE_TIMEOUT, UNIT_CONVERTER

from django.core.cache import cache
from django.utils import timezone


def set_common(
    results: Dict,
    best_index: int,
    best_output: List[Dict],
    best_fitness: float,
) -> Dict:
    """
    Remove the order that got chosen to be swapped by common orders, then
    injecting the common orders and new fitness into results.
    """
    results["output"].pop(best_index)  # remove the old order
    
    for item in results['output']:
        item['blade'] = 1
    
    results["output"].extend(best_output)  # add the new one

    new_fitness = 0
    for index, item in enumerate(results["output"]):  # calculate new fitness
        new_fitness += item["cut_width"] * item["out"]
        
        

    results["fitness"] = new_fitness
    results["trim"] = abs(best_fitness)  # set new trim
    return results


def set_csv_file(file_id: str) -> CSVFile:
    return get_object_or_404(CSVFile, id=file_id)


def set_progress(progress) -> None:
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
    order_instances = []

    for _, row in data.iterrows():
        due_date = timezone.make_aware(
            pd.to_datetime(row["กำหนดส่ง"], format="%m/%d/%y")
        )
        order_id = f"{row['เลขที่ใบสั่งขาย']}-{row['ชนิดส่วนประกอบ']}-{uuid.uuid4()}"

        # if OrderList.objects.filter(id=order_id).exists():
        #     continue

        order_instance = OrderList(
            id=order_id,
            due_date=due_date,
            front_sheet=row["แผ่นหน้า"],
            c_wave=row["ลอน C"],
            middle_sheet=row["แผ่นกลาง"],
            b_wave=row["ลอน B"],
            back_sheet=row["แผ่นหลัง"],
            level=row["จน.ชั้น"],
            width=round(row["กว้างผลิต"] / UNIT_CONVERTER, 4),
            length=round(row["ยาวผลิต"] / UNIT_CONVERTER, 4),
            left_edge_cut=row["ทับเส้นซ้าย"],
            middle_edge_cut=row["ทับเส้นกลาง"],
            right_edge_cut=row["ทับเส้นขวา"],
            order_number=row["เลขที่ใบสั่งขาย"],
            component_type=row["ชนิดส่วนประกอบ"],
            quantity=row["จำนวนสั่งขาย"],
            production_quantity=row["จำนวนสั่งผลิต"],
            edge_type=row["ประเภททับเส้น"],
            order_status=row["สถานะใบสั่ง"],
            excess_percentage=row["% ที่เกิน"],
            file=csv_file,
        )
        order_instances.append(order_instance)

    if order_instances:
        OrderList.objects.bulk_create(order_instances)
        orders = pd.DataFrame(list(OrderList.objects.all().values()))

    # for column in orders.columns:
    #     if pd.api.types.is_datetime64_any_dtype(orders[column]):
    #         orders[column] = orders[column].dt.strftime("%m/%d/%y")

    # Cache the orders
    cache.set(f"order_cache_{file_id}", orders, CACHE_TIMEOUT)
