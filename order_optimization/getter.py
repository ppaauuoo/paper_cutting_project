import uuid
from pandas import DataFrame
import pandas as pd

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from ordplan_project.settings import UNIT_CONVERTER

from .models import CSVFile, OrderList
from order_optimization.container import ModelContainer, OrderContainer
from modules.ordplan import ORD
from modules.ga import GA

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from icecream import ic

from ordplan_project.settings import PLAN_RANGE, CACHE_TIMEOUT


def populate_model(file_id: str) -> None:
    """
    Extract data from file excel then creating a model with it.
    """
    csv_file = get_csv_file(file_id)
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
            width=round(row["กว้างผลิต"] / UNIT_CONVERTER, 2),
            length=round(row["ยาวผลิต"] / UNIT_CONVERTER, 2),
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


def get_orders_cache(file_id: str) -> DataFrame:
    """
    Get raw orders from cache or model, if there nothing
    populate model with file excel.
    """
    orders = cache.get(f"order_cache_{file_id}", None)

    if orders is not None and len(orders) >= PLAN_RANGE:
        return orders

    order_records = OrderList.objects.filter(file=get_csv_file(file_id))

    if order_records.exists():
        orders = pd.DataFrame(order_records.values())
        # orders["due_date"] = pd.to_datetime(orders["due_date"]).dt.strftime("%m/%d/%y")
        cache.set(f"order_cache_{file_id}", orders, CACHE_TIMEOUT)
    else:
        populate_model(file_id)

    return get_orders_cache(file_id)


def get_orders(
    request,
    file_id: str,
    size_value: float = 66.0,
    deadline_scope: int = 0,
    filter_value: int = 16,
    tuning_values: int = 3,
    filter_diff: bool = True,
    common: bool = False,
    filler: Optional[str] = None,
    first_date_only: bool = False,
    preview: bool = False,
    start_date: Optional[pd.DatetimeIndex] = None,
    stop_date: Optional[pd.DatetimeIndex] = None,
) -> DataFrame:
    """
    Pass args to order processor.

    return: processed orders.
    """
    return OrderContainer(
        provider=ORD(
            orders=get_orders_cache(file_id),
            deadline_scope=deadline_scope,
            _filter_diff=filter_diff,
            filter_value=filter_value,
            size=size_value,
            tuning_values=tuning_values,
            common=common,
            filler=filler,
            selector=get_selected_order(request),
            first_date_only=first_date_only,
            preview=preview,
            start_date=start_date,
            stop_date=stop_date,
        )
    ).get()


def get_selected_order(request) -> Dict[str, Any] | None:
    """
    Request order id and out from order selector.
    """
    selector_id = request.POST.get("selector_id")
    if not selector_id:
        return None
    selector_out = int(request.POST.get("selector_out"))
    return {"order_id": selector_id, "out": selector_out}


def get_optimizer(
    request,
    orders: DataFrame,
    size_value: float,
    out_range: int = 3,
    num_generations: int = 50,
    show_output: bool = False,
) -> ModelContainer:
    """
    Clear progress, request and run the optimizer.
    """
    cache.delete("optimization_progress")
    optimizer_instance = ModelContainer(
        model=GA(
            orders,
            size=size_value,
            out_range=out_range,
            num_generations=num_generations,
            showOutput=show_output,
            selector=get_selected_order(request),
            set_progress=set_progress,
        ),
    )
    optimizer_instance.run()
    return optimizer_instance


def set_progress(progress) -> None:
    """
    Update progress cache
    """
    cache.set("optimization_progress", progress, CACHE_TIMEOUT)


def get_csv_file(file_id: str) -> CSVFile:
    return get_object_or_404(CSVFile, id=file_id)


def get_outputs(optimizer_instance: ModelContainer) -> Tuple[float, List[Dict]]:
    """
    Extract values from optimizer instance.
    """
    fitness_values = optimizer_instance.fitness_values
    # output_data = optimizer_instance.output.drop_duplicates().to_dict("records")
    output_data = optimizer_instance.output.to_dict("records")

    return fitness_values, output_data
