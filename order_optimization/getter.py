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
    
    orders = cache.get(f'order_cache_{file_id}', None)

    if orders is None:
        # Check if orders are already saved in the database
        try:
            order_records = OrderList.objects.filter(file=csv_file)
            if order_records.exists():
                orders = pd.DataFrame(list(order_records.values()))
            else:
                raise OrderList.DoesNotExist
        except OrderList.DoesNotExist:
            orders = pd.read_excel(file_path, engine="openpyxl")
            
            # Save orders to the database
            order_instances = []
            for _, row in orders.iterrows():
                order_instance = OrderList(
                    file=csv_file,
                    กำหนดส่ง=row['กำหนดส่ง'],
                    แผ่นหน้า=row['แผ่นหน้า'],
                    ลอน_C=row['ลอน C'],
                    แผ่นกลาง=row['แผ่นกลาง'],
                    ลอน_B=row['ลอน B'],
                    แผ่นหลัง=row['แผ่นหลัง'],
                    จน_ชั้น=row['จน.ชั้น'],
                    กว้างผลิต=row['กว้างผลิต'],
                    ยาวผลิต=row['ยาวผลิต'],
                    ทับเส้นซ้าย=row['ทับเส้นซ้าย'],
                    ทับเส้นกลาง=row['ทับเส้นกลาง'],
                    ทับเส้นขวา=row['ทับเส้นขวา'],
                    เลขที่ใบสั่งขาย=row['เลขที่ใบสั่งขาย'],
                    ชนิดส่วนประกอบ=row['ชนิดส่วนประกอบ'],
                    จำนวนสั่งขาย=row['จำนวนสั่งขาย'],
                    จำนวนสั่งผลิต=row['จำนวนสั่งผลิต'],
                    ประเภททับเส้น=row['ประเภททับเส้น'], 
                    สถานะใบสั่ง=row['สถานะใบสั่ง'],
                    เปอร์เซ็นต์ที่เกิน=row['% ที่เกิน']
                )
                order_instances.append(order_instance)
            
            OrderList.objects.bulk_create(order_instances)
        
        # Cache the orders
        cache.set(f'order_cache_{file_id}', orders, CACHE_TIMEOUT)

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
    first_date_only: bool= False,
) -> DataFrame:

    orders: DataFrame = get_orders_cache(file_id)


    return OrderContainer(
        provider=ORD(
            orders= orders,
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
