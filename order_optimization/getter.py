from pandas import DataFrame
import pandas as pd
from django.core.cache import cache

from ordplan_project.settings import CACHE_TIMEOUT, ROLL_PAPER
from order_optimization.setter import set_csv_file, set_model, set_progress
from order_optimization.models import OrderList
from order_optimization.container import ModelContainer, OrderContainer
from modules.new_ga import GA
from modules.hd import HD

from typing import Any, Dict, List, Optional, Tuple


def get_production_quantity(output_data):
    """
    Calculate first order cut and second order cut.
    """
    init_len = output_data[0]["cut_len"]
    init_out = output_data[0]["out"]
    init_num_orders = output_data[0]["num_orders"]

    if len(output_data) <= 1:
        return (init_num_orders, init_num_orders)

    foll_order_len = output_data[1]["cut_len"]
    foll_out = output_data[1]["out"]

    foll_order_number = round(

      (init_len * init_num_orders * foll_out) / (foll_order_len * init_out)

    )
    return (init_num_orders, foll_order_number)


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
        cache.set(f"order_cache_{file_id}", orders, CACHE_TIMEOUT)
    else:
        set_model(file_id)

    return get_orders_cache(file_id)


def get_orders(
    file_id: str,
    common: bool = False,
    preview: bool = False,
    start_date: Optional[pd.Timestamp] = None,
    stop_date: Optional[pd.Timestamp] = None,
    common_init_order: Optional[Dict[str, Any]] = None,
) -> DataFrame:
    """
    Pass args to order processor.

    return: processed orders.
    """

    orders = get_orders_cache(file_id)

    return OrderContainer(
        provider=HD(
            orders=orders,
            common=common,
            start_date=start_date,
            stop_date=stop_date,
            common_init_order=common_init_order,
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
    size_value: Optional[float] = None,
    num_generations: int = 50,
    show_output: bool = False,
    blade: Optional[int] = None,
    common: bool = False,
    selector: Dict[str, Any] = None,
) -> ModelContainer:
    """
    Clear progress, request and run the optimizer.
    """
    cache.delete("optimization_progress")
    optimizer_instance = ModelContainer(
        model=GA(
            orders,
            size=size_value,
            num_generations=num_generations,
            showOutput=show_output,
            set_progress=set_progress,
            blade=blade,
            common=common,
            selector=selector
        ),
    )
    optimizer_instance.run()
    return optimizer_instance


def get_outputs(optimizer_instance:
                ModelContainer) -> List[Dict]:
    """
    Extract values from optimizer instance.
    """
    output_df = optimizer_instance.output.reset_index()
    output_data = output_df.to_dict("records")
    if len(output_data) <= 0:
        raise ValueError("Solution Not Found")
    if len(output_data) > 2:
        raise ValueError("Solution Not Satisfied")

    return output_data


def get_common(
    request,
    blade: int,
    file_id: str,
    item: Dict[str, Any],
    results: Dict[str, Any],
):
    size_value = (item["cut_width"] * item["out"]) + results["trim"]
    orders = get_orders(
        file_id=file_id, common=True, common_init_order=item
    )
    optimizer_instance = get_optimizer(
        request=request,
        orders=orders,
        size_value=size_value,
        show_output=False,
        blade=blade,
        common=True,
        selector=item
    )
    return optimizer_instance
