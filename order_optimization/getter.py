from pandas import DataFrame
import pandas as pd
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from order_optimization.setter import *

from .models import CSVFile, OrderList
from order_optimization.container import ModelContainer, OrderContainer
from modules.ordplan import ORD
from modules.new_ga import GA
from modules.hd import HD

from typing import Any, Dict, List, Optional, Tuple

from icecream import ic

from ordplan_project.settings import CACHE_TIMEOUT


def get_orders_cache(file_id: str) -> DataFrame:
    """
    Get raw orders from cache or model, if there nothing
    populate model with file excel.
    """
    orders = cache.get(f"order_cache_{file_id}", None)

    if orders is not None:
        return orders

    order_records = OrderList.objects.filter(file=set_csv_file(file_id))

    if order_records.exists():
        orders = pd.DataFrame(order_records.values())
        # orders["due_date"] = pd.to_datetime(orders["due_date"]).dt.strftime("%m/%d/%y")
        cache.set(f"order_cache_{file_id}", orders, CACHE_TIMEOUT)
    else:
        set_model(file_id)

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
    start_date: Optional[pd.Timestamp] = None,
    stop_date: Optional[pd.Timestamp] = None,
    selector: Optional[Dict[str, Any]] = None,
    common_init_order: Optional[Dict[str,Any]] = None
) -> DataFrame:
    """
    Pass args to order processor.

    return: processed orders.
    """

    return ic(OrderContainer(
        #provider=ORD(
        #    orders=get_orders_cache(file_id),
        #    deadline_scope=deadline_scope,
        #    _filter_diff=filter_diff,
        #    filter_value=filter_value,
        #    size=size_value,
        #    tuning_values=tuning_values,
        #    common=common,
        #    filler=filler,
        #    selector=selector if selector else get_selected_order(request),
        #    first_date_only=first_date_only,
        #    preview=preview,
        #    start_date=start_date,
        #    stop_date=stop_date,
        #    common_init_order=common_init_order,
        #)
        provider=HD(
            orders=get_orders_cache(file_id),
            common=common,
            start_date=start_date,
            stop_date=stop_date,
            common_init_order=common_init_order,
            )
    ).get())


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
    out_range: int = 5,
    num_generations: int = 50,
    show_output: bool = False,
    blade:Optional[int] = None,
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
            blade=blade

        ),
    )
    optimizer_instance.run()
    return optimizer_instance





def get_outputs(optimizer_instance: ModelContainer) -> Tuple[float, List[Dict]]:
    """
    Extract values from optimizer instance.
    """
    fitness_values = optimizer_instance.fitness_values
    # output_data = optimizer_instance.output.drop_duplicates().to_dict("records")
    output_data = optimizer_instance.output.to_dict("records")

    return fitness_values, output_data


def get_common(
    request,
    blade: int,
    file_id: str,
    item: Dict[str, Any],
    results: Dict[str, Any],
    single: bool = False,
):
    size_value = (item["cut_width"] * item["out"]) + results["trim"]
    orders = get_orders(
        request=request,
        file_id=file_id,
        size_value=size_value,
        deadline_scope=-1,
        filter_diff=False,
        common=True,
        selector={"order_id": item["id"]} if single else None,
        common_init_order=item
    )
    optimizer_instance = get_optimizer(
        request=request, orders=orders, size_value=size_value, show_output=False, blade=blade
    )
    return optimizer_instance
