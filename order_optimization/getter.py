import datetime
from django.utils import timezone
from pandas import DataFrame
import pandas as pd

from order_optimization.container import ModelContainer, OrderContainer
from .modules.ordplan import ORD

from django.shortcuts import get_object_or_404

from .models import CSVFile, OrderList

from typing import Dict, List, Tuple
from .modules.ga import GA
from django.core.cache import cache

from dataclasses import dataclass

from django.conf import settings

from icecream import ic

CACHE_TIMEOUT = settings.CACHE_TIMEOUT


def get_orders_cache(file_id: str) -> DataFrame:
    csv_file = get_csv_file(file_id)
    file_path = csv_file.file.path

    orders = cache.get(f"order_cache_{file_id}", None)

    if orders is None:
        # Check if orders are already saved in the database
        try:
            order_records = OrderList.objects.filter(file=csv_file)
            if order_records.exists():
                orders = pd.DataFrame(list(order_records.values()))
                orders["due_date"] = orders["due_date"].dt.strftime("%m/%d/%y")
            else:
                raise OrderList.DoesNotExist
        except OrderList.DoesNotExist:
            data = pd.read_excel(file_path, engine="openpyxl")

            # Save orders to the database
            order_instances = []
            for _, row in data.iterrows():
                due_date = pd.to_datetime(row["กำหนดส่ง"], format="%m/%d/%y")
                due_date = timezone.make_aware(due_date, timezone.get_current_timezone())

                order_instance = OrderList(
                    file=csv_file,
                    due_date=due_date,
                    front_sheet=row["แผ่นหน้า"],
                    c_wave=row["ลอน C"],
                    middle_sheet=row["แผ่นกลาง"],
                    b_wave=row["ลอน B"],
                    back_sheet=row["แผ่นหลัง"],
                    level=row["จน.ชั้น"],
                    width=row["กว้างผลิต"],
                    length=row["ยาวผลิต"],
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
                )
                order_instances.append(order_instance)

            OrderList.objects.bulk_create(order_instances)
            orders = pd.DataFrame(list(order_records.values()))
            orders["due_date"] = orders["due_date"].dt.strftime("%m/%d/%y")

        # Cache the orders
        cache.set(f"order_cache_{file_id}", orders, CACHE_TIMEOUT)

    return orders


def get_orders(
    request,
    file_id: str,
    size_value: float = 66,
    deadline_scope: int = 0,
    filter_value: int = 16,
    tuning_values: int = 3,
    filter_diff: bool = True,
    common: bool = False,
    filler: int = 0,
    first_date_only: bool = False,
) -> DataFrame:

    orders: DataFrame = get_orders_cache(file_id)

    return OrderContainer(
        provider=ORD(
            orders=orders,
            deadline_scope=deadline_scope,
            _filter_diff=filter_diff,
            filter_value=filter_value,
            size=size_value,
            tuning_values=tuning_values,
            common=common,
            filler=filler,
            selector=get_selected_order(request),
            first_date_only=first_date_only,
        )
    ).get()


def get_selected_order(request) -> Dict[str, int] | None:
    selector_id = request.POST.get("selector_id")
    if not selector_id:
        return None

    selector_id = int(selector_id)
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
    cache.set("optimization_progress", progress, CACHE_TIMEOUT)


def get_csv_file(file_id: str) -> CSVFile:
    return get_object_or_404(CSVFile, id=file_id)


def get_outputs(optimizer_instance: ModelContainer) -> Tuple[float, List[Dict]]:
    fitness_values = optimizer_instance.fitness_values
    output_data = optimizer_instance.output.to_dict("records")
    return fitness_values, output_data
