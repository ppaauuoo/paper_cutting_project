import random

from datetime import datetime
from typing import Dict, List, Optional, Any
from icecream import ic

from django.contrib import messages
from django.core.cache import cache

from order_optimization.setter import set_common
from order_optimization.models import OptimizationPlan, OrderList
from order_optimization.getter import get_common, get_orders, get_outputs, get_optimizer, get_production_quantity
from ordplan_project.settings import (
    MIN_TRIM,
    ROLL_PAPER,
    FILTER,
    CACHE_TIMEOUT,
    MAX_RETRY,
    MAX_TRIM,
    MIN_TRIM,
)
from order_optimization.formatter import (
    database_formatter,
    output_formatter,
    plan_orders_formatter,
    results_formatter,
)

from modules.lp import LP

def handle_optimization(func):
    """
    Run optimizer then processing the output,
    Looping thru optimizer multiple time if stated.
    """

    def wrapper(request, *args, **kwargs):
        kwargs = func(request)
        if not kwargs:
            return messages.error(
                request, "Error 404: No orders were found. Please try again."
            )

        results = handle_results(request, kwargs=kwargs)
        results = handle_switcher(results)
        try:
            results = handle_common_component(request, results=results)
        except(ValueError) as e:
            ic(e)
            pass

        if is_trim_fit(results["trim"]) and is_foll_ok(results["output"], results["foll_order_number"]):
            messages.success(request, "Optimizing finished.")
            cache.delete("past_size")
            cache.delete("try_again")
            cache.set("optimization_results", results, CACHE_TIMEOUT)
            return

        best_result = cache.get("best_result", {"trim": 1000})
        if results["trim"] < best_result["trim"]:
            cache.set("best_result", results, CACHE_TIMEOUT)

        if "auto" or "ai" in request.POST:
            return handle_auto_retry(request)

        cache.delete("try_again")
        messages.error(
            request, "Optimizing finished with unsatisfied result, please try again."
        )
        return cache.set("optimization_results", best_result, CACHE_TIMEOUT)

    return wrapper


def handle_results(request, kwargs) -> Dict[str, Any]:
    orders = kwargs.get("orders", None)

    if orders is None:
        raise ValueError("Orders is empty!")

    optimizer_instance = get_optimizer(
        request=request,
        orders=orders,
        size_value=kwargs.get("size_value", 66),
        out_range=kwargs.get("out_range", 6),
        num_generations=kwargs.get("num_generations", 50),
        show_output=False,
    )
    fitness_values, output_data = get_outputs(optimizer_instance)
    init_order_number, foll_order_number = get_production_quantity(output_data)

    results = results_formatter(
        optimizer_instance=optimizer_instance,
        output_data=output_data,
        size_value=kwargs.get("size_value", 66),
        fitness_values=fitness_values,
        init_order_number=init_order_number,
        foll_order_number=foll_order_number,
    )
    return results

def handle_switcher(results: Dict[str, Any]) -> Dict[str, Any]:
    if is_trim_fit(results["trim"]):
        return results
    switcher = LP(results).run().get()
    if switcher is not None:
        results["trim"] = switcher["new_trim"]
        results["roll"] = switcher["new_roll"]
    return results


def is_foll_ok(output: List[Dict[str, Any]], foll_order_number: int):
    """
    Check if second order's cut exceed the second order's stock or not.
    """
    for index, order in enumerate(output):
        if index == 0:
            continue
        if order["num_orders"] < foll_order_number:
            return False
    return True


def is_trim_fit(trim: float):
    """
    Check if trim exceed min/max tirm.
    """
    return trim <= MAX_TRIM and trim >= MIN_TRIM


def handle_auto_retry(request):
    """
    Recursive features for auto configuration.
    """
    again = cache.get("try_again", 0)
    if again < MAX_RETRY:
        again += 1
        cache.set("try_again", again, CACHE_TIMEOUT)
        return handle_auto_config(request)

    messages.error(request, "Error : Auto config malfunctioned, please contact admin.")
    best_result = cache.get("best_result")
    cache.delete("past_size")
    cache.set("optimization_results", best_result, CACHE_TIMEOUT)
    cache.delete("try_again")
    raise ValueError('No More!')
    return


@handle_optimization
def handle_auto_config(request, **kwargs):
    """
    Automatically defines values needed for requesting orders and send it to optimizer.
    """

    again = cache.get("try_again", 0)
    out_range = 5
    file_id = request.POST.get("file_id")
    start_date = request.POST.get("start_date")
    stop_date = request.POST.get("stop_date")
    orders = get_orders(request=request, file_id=file_id, start_date=start_date, stop_date=stop_date)
    size = 66
    if again > MAX_RETRY:
        raise ValueError("Logic error!")
    if orders is None:
        raise ValueError("Orders is empty!")

    kwargs.update(
        {
            "orders": orders,
            "size_value": size,
            "num_generations": 50,
            "out_range": out_range,
        }
    )
    return kwargs

def handle_common_component(request, results: Dict[str, Any]) -> Dict[str, Any]:
    common = handle_common(request, results=results, as_component=True)
    
    if common is not None:
        results = common
    return results

def handle_common(
    request, results: Optional[Dict[str, Any]] = None, as_component: bool = False
) -> Optional[Dict[str,Any]]:
    """
    Request orders base from the past results with common logic and run an optimizer.
    """
    if results is None:
        results = cache.get("optimization_results")
    best_trim = results["trim"]
    best_index: Optional[int] = None

    if not as_component:
        file_id = request.POST.get("selected_file_id")
    else:
        file_id = request.POST.get("file_id")

    for index, item in enumerate(results["output"]):

        optimizer_instance = get_common(
            request=request, blade=2, file_id=file_id, item=item, results=results
        )

        if abs(optimizer_instance.fitness_values) <= best_trim:
            best_fitness, best_output = get_outputs(optimizer_instance)
            best_trim = abs(best_fitness)
            best_index = index
            break

    if best_index is not None:
        results = set_common(results, best_index, best_output, best_trim)
        messages.success(request, "Common order found.")
    else:
        messages.error(request, "No suitable common order found.")

    if as_component:
        return handle_switcher(results)

    return cache.set("optimization_results", results, CACHE_TIMEOUT)


def handle_saving(request):
    """
    Pull data from cache to save into the model and updating both cache and model.
    """
    file_id = request.POST.get("file_id")
    cache.delete(f"order_cache_{file_id}")
    data = cache.get("optimization_results", None)
    cache.delete(f"optimization_results")
    if data is None:
        raise ValueError("Output is empty!")
    try:    
        database_formatter(data)
    except ValueError as e:
        raise ValueError(e)




def handle_reset(request):
    """
    Remove cache and database.
    """
    cache.clear()
    OptimizationPlan.objects.all().delete()
    OrderList.objects.all().delete()


def handle_export(request):
    """
    For exporting data from model to file excel.
    """
    df = plan_orders_formatter()
    # Save the DataFrame to a file
    df.to_excel(
        f'media/exports/orders_export_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx',
        index=False,
    )
