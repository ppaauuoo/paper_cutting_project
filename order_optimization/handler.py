from order_optimization.modules import ga
from .modules.ordplan import ORD
from .modules.ga import GA

from typing import Callable, Dict
from django.contrib import messages
from django.core.cache import cache

import pandas as pd

from typing import Callable, Dict, List, Optional

from .getter import get_orders, get_outputs, get_optimizer

from django.conf import settings

from icecream import ic

ROLL_PAPER = settings.ROLL_PAPER
FILTER = settings.FILTER
OUT_RANGE = settings.OUT_RANGE
TUNING_VALUE = settings.TUNING_VALUE
CACHE_TIMEOUT = settings.CACHE_TIMEOUT

MAX_RETRY = 3
MAX_TRIM = 3
MIN_TRIM = 1


def handle_optimization(func):
    def wrapper(request, *args, **kwargs):
        kwargs = func(request)
        if not kwargs:
            ic()
            return messages.error(request, "Error 404: No orders were found. Please try again.")

        size_value = kwargs.get("size_value", None)
        orders = kwargs.get("orders", None)
        num_generations = kwargs.get("num_generations", 50)
        out_range = kwargs.get("out_range", 6)

        optimizer_instance = get_optimizer(
            request, orders, size_value, out_range, num_generations
        )
        fitness_values, output_data = get_outputs(optimizer_instance)

        init_order_number, foll_order_number = handle_orders_logic(output_data)

        results = results_format(
            optimizer_instance,
            output_data,
            size_value,
            fitness_values,
            init_order_number,
            foll_order_number,
        )

        if is_trim_fit(fitness_values):
            messages.success(request, "Optimizing finished.")
            return cache.set("optimization_results", results, CACHE_TIMEOUT)

        if "auto" in request.POST:
            return handle_auto_retry(request)

        satisfied = 1 if request.POST.get("satisfied") == "true" else 0
        if satisfied:
            return handle_satisfied_retry(wrapper, request, results, *args, **kwargs)

        cache.delete("try_again")
        messages.error(
            request, "Optimizing finished with unsatisfied result, please try again."
        )
        return cache.set("optimization_results", results, CACHE_TIMEOUT)

    return wrapper


def is_trim_fit(fitness_values: float):
    return abs(fitness_values) <= MAX_TRIM and abs(fitness_values) >= MIN_TRIM


def handle_orders_logic(output_data):
    init_len = output_data[0]["cut_len"]
    init_out = output_data[0]["out"]
    init_num_orders = output_data[0]["num_orders"]

    foll_order_len = init_len
    if len(output_data) > 1:
        foll_order_len = output_data[1]["cut_len"]

    init_order_number = round(init_num_orders / init_out)
    foll_order_number = round(init_len * init_order_number / foll_order_len)
    return (init_order_number, foll_order_number)


def handle_auto_retry(request):
    again = cache.get("try_again", 0)
    if again <= MAX_RETRY:
        again += 1
        cache.set("try_again", again, CACHE_TIMEOUT)
        return handle_auto_config(request)
    messages.error(request, "Error : Auto config malfunctioned, please contact admin.")
    return cache.delete("optimization_results")  # clear


def handle_satisfied_retry(wrapper, request, results, *args, **kwargs):
    again = cache.get("try_again", 0)
    if again <= MAX_RETRY:
        again += 1
        cache.set("try_again", again, CACHE_TIMEOUT)
        return wrapper(request, *args, **kwargs)
    messages.error(
        request, "Optimizing finished with unsatisfied result, please try again."
    )
    cache.delete("try_again")
    return cache.set("optimization_results", results, CACHE_TIMEOUT)


@handle_optimization
def handle_manual_config(request, **kwargs):
    # Extract values from the request
    file_id = request.POST.get("file_id")
    size_value = int(request.POST.get("size_value", 0))
    deadline_toggle = -1 if request.POST.get("deadline_toggle") == "true" else 0
    filter_value = int(request.POST.get("filter_value", 0))
    tuning_value = int(request.POST.get("tuning_value", 0))
    num_generations = int(request.POST.get("num_generations", 0))
    out_range = int(request.POST.get("out_range", 0))
    first_date_only = request.POST.get("first_date_only")

    # Fetch orders using the extracted parameters
    orders = get_orders(
        request=request,
        file_id=file_id,
        size_value=size_value,
        deadline_scope=deadline_toggle,
        filter_value=filter_value,
        tuning_values=tuning_value,
        first_date_only=first_date_only,
    )

    # Check if any orders were found
    if orders.empty:
        return None  # Return kwargs even if no orders are found

    # Update kwargs with the found orders
    kwargs.update({
        "orders": orders,
        "size_value": size_value,
        "num_generations": num_generations,
        "out_range": out_range,
    })

    return kwargs


@handle_optimization
def handle_auto_config(request, **kwargs):
    again = cache.get("try_again", 0)
    out_range = 3 + again
    orders, size = auto_size_filter_logic(request)
    # Pass all necessary variables to the wrapped function
    kwargs.update({
        "orders": orders,
        "size_value": size,
        "num_generations": 50,  # or another value as needed
        "out_range": out_range
    })
    return kwargs


def auto_size_filter_logic(request):
    filter_index = 0
    roll_index = 8
    orders = cache.get("auto_order", [])
    size = cache.get("order_size", ROLL_PAPER[roll_index])
    file_id = request.POST.get("file_id")
    tuning_value = TUNING_VALUE[1]
    while len(orders) <= 0:
        orders = get_orders(
            request,
            file_id,
            size,
            FILTER[-filter_index],
            tuning_value,
            first_date_only=True,
        )
        filter_index += 1
        if filter_index > len(FILTER):
            filter_index = 0
            roll_index += 1
            size = ROLL_PAPER[roll_index]

    cache.set("auto_order", orders, CACHE_TIMEOUT)
    cache.set("order_size", size, CACHE_TIMEOUT)

    return (orders, size)


def handle_common(request) -> Callable:

    results = cache.get("optimization_results")
    best_fitness = -results["trim"]
    best_index: Optional[int] = None
    file_id = request.POST.get("selected_file_id")

    for i, item in enumerate(results["output"]):

        size_value = (item["cut_width"] * item["out"]) + results["trim"]
        orders = get_orders(
            request, file_id, size_value, deadline_scope=-1, filter_diff=False, common=True
        )
        optimizer_instance = get_optimizer(
            request, orders, size_value, show_output=True
        )

        if abs(optimizer_instance.fitness_values) < abs(best_fitness):
            best_fitness, best_output = get_outputs(optimizer_instance)
            best_index = i

    if best_index is not None:
        update_results(results, best_index, best_output, best_fitness, size_value)
        messages.success(request, "Common order found.")
    else:
        messages.error(request, "No suitable common order found.")

    return cache.set("optimization_results", results, CACHE_TIMEOUT)


def update_results(
    results: Dict,
    best_index: int,
    best_output: List[Dict],
    best_fitness: float,
    size_value: float,
) -> None:
    results["output"].pop(best_index)  # remove the old order
    results["output"].extend(best_output)  # add the new one

    for item in results["output"]:  # calculate new fitness
        results["fitness"] += item["cut_width"] * item["out"]

    results["trim"] = abs(best_fitness)  # set new trim


def handle_filler(request):
    results = cache.get("optimization_results")
    init_order = results["output"][0]["order_number"]
    file_id = request.POST.get("selected_file_id")
    size_value = results["output"][0]["cut_width"]
    init_out = results["output"][0]["out"]
    orders = get_orders(
        request,
        file_id,
        size_value,
        tuning_values=1,
        filter_diff=False,
        common=True,
        filler=init_order,
    )

    i = 0
    while (
        i < len(orders)
        and results["foll_order_number"]
        > results["output"][1]["num_orders"] + orders["จำนวนสั่งขาย"][i]
    ):
        i += 1

    filler_data = output_format(orders.iloc[i], init_out).to_dict(orient="records")
    results["output"].extend(filler_data)
    return cache.set("optimization_results", results, CACHE_TIMEOUT)


def output_format(orders: Dict, init_out: int = 0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_number": [orders["เลขที่ใบสั่งขาย"]],
            "num_orders": [orders["จำนวนสั่งขาย"]],
            "cut_width": [orders["กว้างผลิต"]],
            "cut_len": [orders["ยาวผลิต"]],
            "type": [orders["ประเภททับเส้น"]],
            "deadline": [orders["กำหนดส่ง"]],
            "out": [init_out],
        }
    )


def results_format(
    optimizer_instance: GA,
    output_data: dict,
    size_value: int,
    fitness_values: float,
    init_order_number: int,
    foll_order_number: int,
) -> Dict:
    return {
        "output": output_data,
        "roll": optimizer_instance.PAPER_SIZE,
        "fitness": size_value + fitness_values,
        "trim": abs(fitness_values),
        "init_order_number": init_order_number,
        "foll_order_number": foll_order_number,
    }


from .models import OptimizedOrder

def handle_saving(request):
    data = cache.get("optimization_results", [])
    cache.delete("optimization_results")
    optimized_order = OptimizedOrder(output=data["output"])
    optimized_order.save()


