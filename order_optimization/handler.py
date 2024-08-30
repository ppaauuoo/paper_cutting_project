from datetime import datetime
from django.contrib import messages
from django.core.cache import cache
from django.conf import settings

from django.http import HttpResponse
import pandas as pd
from typing import Callable, Dict, List, Optional, Any
from icecream import ic

from .getter import get_orders, get_outputs, get_optimizer
from order_optimization.container import ModelContainer

ROLL_PAPER = settings.ROLL_PAPER
FILTER = settings.FILTER
OUT_RANGE = settings.OUT_RANGE
TUNING_VALUE = settings.TUNING_VALUE
CACHE_TIMEOUT = settings.CACHE_TIMEOUT

MAX_RETRY = settings.MAX_RETRY
MAX_TRIM = settings.MAX_TRIM
MIN_TRIM = settings.MIN_TRIM


def handle_optimization(func):
    def wrapper(request, *args, **kwargs):
        kwargs = func(request)
        if not kwargs:
            return messages.error(
                request, "Error 404: No orders were found. Please try again."
            )

        size_value = kwargs.get("size_value", 66)
        orders = kwargs.get("orders", None)

        if orders is None:
            raise ValueError("Orders is empty!")
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
    init_order_number = round(init_num_orders / init_out)

    foll_order_len: List[int] = []
    foll_out: List[int] = []

    for index, order in enumerate(output_data):
        if index == 0 and len(output_data)>1:
            continue
        foll_order_len.append(order["cut_len"])
        foll_out.append(order["out"])

    foll_order_number = round(
        (init_len * init_num_orders) / (foll_order_len[0] * init_out)
    )
    # foll_order_number = foll_order_number[index]/foll_out[index]
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
    if orders is None:
        raise ValueError("Orders is empty!")

    # Update kwargs with the found orders
    kwargs.update(
        {
            "orders": orders,
            "size_value": size_value,
            "num_generations": num_generations,
            "out_range": out_range,
        }
    )

    return kwargs


@handle_optimization
def handle_auto_config(request, **kwargs):
    again = cache.get("try_again", 0)
    out_range = 3 + again
    orders, size = auto_size_filter_logic(request)
    if size is None:
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


def auto_size_filter_logic(request):
    filter_index = 0
    roll_index = 8
    orders = cache.get("auto_order", None)
    size = cache.get("order_size", ROLL_PAPER[roll_index])
    file_id = request.POST.get("file_id")
    tuning_value = TUNING_VALUE[1]
    while orders is None or len(orders) <= 0:
        orders = get_orders(
            request=request,
            file_id=file_id,
            size_value=size,
            filter_value=FILTER[-filter_index],
            tuning_values=tuning_value,
            first_date_only=False,
        )
        filter_index += 1
        if filter_index >= len(FILTER):
            filter_index = 0
            roll_index += 1
            if roll_index >= len(ROLL_PAPER):
                return (None,None)
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
            request,
            file_id,
            size_value,
            deadline_scope=-1,
            filter_diff=False,
            common=True,
        )
        optimizer_instance = get_optimizer(
            request, orders, size_value, show_output=True
        )

        if abs(optimizer_instance.fitness_values) < abs(best_fitness):
            best_fitness, best_output = get_outputs(optimizer_instance)
            best_index = i

    if best_index is not None:
        results = update_results(results, best_index, best_output, best_fitness)
        messages.success(request, "Common order found.")
    else:
        messages.error(request, "No suitable common order found.")

    return cache.set("optimization_results", results, CACHE_TIMEOUT)


def update_results(
    results: Dict,
    best_index: int,
    best_output: List[Dict],
    best_fitness: float,
) -> Dict:
    results["output"].pop(best_index)  # remove the old order
    results["output"].extend(best_output)  # add the new one

    for item in results["output"]:  # calculate new fitness
        results["fitness"] += item["cut_width"] * item["out"]

    results["trim"] = abs(best_fitness)  # set new trim
    return results


def handle_filler(request):
    results = cache.get("optimization_results")
    init_order = results["output"][0]["id"]
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
        orders is not None
        and i < len(orders)
        and results["foll_order_number"]
        > results["output"][1]["num_orders"] + orders["quantity"][i]
    ):
        i += 1

    filler_data = output_format(orders.iloc[i], init_out).to_dict(orient="records")
    results["output"].extend(filler_data)
    return cache.set("optimization_results", results, CACHE_TIMEOUT)


def output_format(orders: pd.Series, init_out: int = 0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_number": [orders["order_number"]],
            "num_orders": [orders["quantity"]],
            "cut_width": [orders["width"]],
            "cut_len": [orders["length"]],
            "type": [orders["edge_type"]],
            "deadline": [orders["due_date"]],
            "out": [init_out],
        }
    )


def results_format(
    optimizer_instance: ModelContainer,
    output_data: List[Dict[str, Any]],
    size_value: int,
    fitness_values: float,
    init_order_number: int,
    foll_order_number: int,
) -> Dict[str, Any]:
    return {
        "output": output_data,
        "roll": optimizer_instance.PAPER_SIZE,
        "fitness": size_value + fitness_values,
        "trim": abs(fitness_values),
        "init_order_number": init_order_number,
        "foll_order_number": foll_order_number,
    }

from .models import OptimizationPlan, OrderList, PlanOrder


def handle_saving(request):
    file_id = request.POST.get("file_id")
    cache.delete(f"order_cache_{file_id}")
    data = cache.get("optimization_results", None)
    cache.delete(f"optimization_results")
    if data is None:
        raise ValueError("Output is empty!")

    handle_order_exhaustion(data)

    optimized_order = database_format(data)
    optimized_order.save()

def database_format(
    data: Dict[str, List[Dict[str, int]]]
) -> OptimizationPlan:

    format_data = OptimizationPlan.objects.create() 

    for item in data["output"]:
        current_id = item['id']
        match item["blade"]:
            case 1:
                blade1_order = PlanOrder.objects.create(
                    order=OrderList.objects.get(id=current_id),
                    plan_quantity=data['init_order_number'],
                    out=item["out"],
                    blade_type='Blade 1'
                )
                format_data.blade_1.add(blade1_order)
                
            case 2:
                blade2_order = PlanOrder.objects.create(
                    order=OrderList.objects.get(id=current_id),
                    plan_quantity=data['foll_order_number'],
                    out=item["out"],
                    blade_type='Blade 2'
                )
                format_data.blade_2.add(blade2_order)

    return format_data



def handle_order_exhaustion(data: Dict[str, Any]) -> None:
    output_data = data["output"]

    for index, order in enumerate(output_data):
        id = order["id"]
        try:
            filtered_order = OrderList.objects.filter(id=id)[0]
        except IndexError:
            raise ValueError("Order Number Not Found!")
        new_value = filtered_order.quantity - data["foll_order_number"]
        if index == 0:
            new_value = 0
        if new_value < 0:
            raise ValueError("Second Order Number Exceed!")
        filtered_order.quantity = new_value
        filtered_order.save()
        filtered_order.quantity


def handle_reset():
    cache.clear()
    OptimizationPlan.objects.all().delete()
    OrderList.objects.all().delete()
    
def handle_export():

    optimized_output = list(PlanOrder.objects.all().values(
        "order_id", "plan_quantity", "out", "blade_type"
    ))

    # Extract order IDs
    optimized_output_ids = [order['order_id'] for order in optimized_output]
    
    # Get corresponding OrderList objects
    optimized_order_list = list(OrderList.objects.filter(id__in=optimized_output_ids).values())

    # Create a dictionary with order_id as the key
    optimized_order_dict = {order['id']: order for order in optimized_order_list}
    
    
    # Combine results
    for order in optimized_output:
        order_id = order['order_id']
        if order_id in optimized_order_dict:
            order.update(optimized_order_dict[order_id])
    
    

    # Create a DataFrame
    df = pd.DataFrame(optimized_output)

    df = handle_timezones(df)

    # Save the DataFrame to a file
    df.to_excel(f'media/exports/orders_export_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx', index=False)

def handle_timezones(df: pd.DataFrame):
    for col in df.select_dtypes(include=['datetime64[ns, UTC]', 'datetime64[ns]']):
        df[col] = df[col].dt.tz_localize(None)
    return df