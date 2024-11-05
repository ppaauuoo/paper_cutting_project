from datetime import datetime
from typing import Dict, List, Optional, Any
from icecream import ic

from django.core.cache import cache

from order_optimization.setter import set_common
from order_optimization.models import OptimizationPlan, OrderList
from order_optimization.getter import (
    get_common,
    get_orders,
    get_outputs,
    get_optimizer,
    get_production_quantity,
)
from ordplan_project.settings import (
    CACHE_TIMEOUT,
    MAX_RETRY,
    MAX_TRIM,
    MIN_TRIM,
    PENALTY_VALUE,
)
from order_optimization.formatter import (
    database_formatter,
    plan_orders_formatter,
    results_formatter,
)

from modules.lp import LP

FILE_ID = "1"


def handle_optimization(func):
    """
    Run optimizer then processing the output,
    Looping thru optimizer multiple time if stated.
    """

    def wrapper(request, *args, **kwargs):
        kwargs = func(request)
        if not kwargs:
            return
        try:
            results = handle_results(request, kwargs=kwargs)
        except ValueError as e:
            raise e

        results = handle_switcher(results)
        try:
            results = handle_common_component(request, results=results)
        except ValueError as e:
            raise e
            pass

        log = ""
        if is_trim_fit(results["trim"]):
            if is_foll_ok(results["output"], results["foll_order_number"]):
                cache.delete("try_again")
                cache.set("optimization_results", results, CACHE_TIMEOUT)
                return
            log = "stock not ok"
        else:
            log = f'trim not ok roll:{results["roll"]} fitness:{
                round(results["fitness"])}'

        cache.set("log", log, CACHE_TIMEOUT)
        cache.delete("try_again")
        cache.set("optimization_results", results, CACHE_TIMEOUT)
        raise ValueError("No Satisfiable Solution Found")

    return wrapper


def handle_results(request, kwargs) -> Dict[str, Any]:
    orders = kwargs.get("orders", None)

    if orders is None:
        raise ValueError("Orders is empty!")

    optimizer_instance = get_optimizer(
        request=request,
        orders=orders,
        num_generations=kwargs.get("num_generations", 50),
        show_output=False,
    )
    fitness_values, output_data = get_outputs(optimizer_instance)
    if fitness_values >= PENALTY_VALUE:
        raise ValueError("Fitness Error!")
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
    foll_stock = 0
    if len(output) <= 1:
        return True
    for index, order in enumerate(output):
        if index == 0:
            continue
        foll_stock += order["num_orders"]
    if foll_stock < foll_order_number:
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

    best_result = cache.get("best_result")
    cache.set("optimization_results", best_result, CACHE_TIMEOUT)
    # cache.delete("optimization_results")
    cache.delete("try_again")
    raise ValueError("No Satisfiable Solution Found")


@handle_optimization
def handle_auto_config(request, **kwargs):
    """
    # Automatically defines values needed for requesting orders
    and send it to optimizer.
    """

    again = cache.get("try_again", 0)
    file_id = FILE_ID

    start_date = request.POST.get("start_date")
    stop_date = request.POST.get("stop_date")

    orders = get_orders(
        file_id=file_id, start_date=start_date, stop_date=stop_date)
    if again > MAX_RETRY:
        raise ValueError("Logic error!")
    if orders is None:
        raise ValueError("Orders is empty!")

    kwargs.update(
        {
            "orders": orders,
        }
    )
    return kwargs


def handle_common_component(request, results: Dict[str, Any]) -> Dict[str, Any]:
    common = handle_common(request, results=results, as_component=True)

    if common is not None:
        results = common
    return results


def handle_common(
    request, results: Optional[Dict[str, Any]], as_component: Optional[bool]
) -> Optional[Dict[str, Any]]:
    """
    Request orders base from the past results
    with common logic and run an optimizer.
    """
    if results is None:
        results = cache.get("optimization_results")
    if len(results["output"]) <= 1:
        return results
    best_trim = results["trim"]
    best_index: Optional[int] = None

    if as_component:
        # file_id = request.POST.get("file_id")
        file_id = FILE_ID
    else:
        file_id = request.POST.get("selected_file_id")

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

    if as_component:
        return handle_switcher(results)

    return cache.set("optimization_results", results, CACHE_TIMEOUT)


def handle_saving(request):
    """
    Pull data from cache to save into the model
    and updating both cache and model.
    """
    file_id = FILE_ID
    cache.delete(f"order_cache_{file_id}")
    data = cache.get("optimization_results", None)
    cache.delete("optimization_results")
    if data is None:
        raise ValueError("Output is empty!")
    try:
        handle_database(data)
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
        f'media/exports/orders_export_{
            datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.xlsx',
        index=False,
    )


def handle_database(data: Dict[str, Any]) -> None:

    if len(data["output"]) <= 1 and data["output"][0]["blade"] != 1:
        raise ValueError(data["output"])
        return

    blade2_params_list = []
    left_over_quantity = 0

    for item in data["output"]:
        current_id = item["id"]

        current_order = OrderList.objects.get(id=current_id)
        match item["blade"]:
            case 1:
                current_order.quantity = 0
                blade1_params = {
                    "order": current_order,
                    "plan_quantity": data["init_order_number"],
                    "out": item["out"],
                    "paper_roll": data["roll"],
                    "blade_type": "Blade 1",
                    "order_leftover": 0,
                }

            case 2:
                # get combined out from second blade
                foll_out = sum(i["out"] for i in data["output"][1:])
                # calculate out ratio base from the combined out
                new_out_ratio = item["out"] / foll_out
                # Calculate new cut for each common
                # with foll cut from first blade divide by out ratio
                foll_cut = data["foll_order_number"] * new_out_ratio
                # add potential leftover from previous order
                plan_quantity = round(foll_cut + left_over_quantity)
                # reset left over to zero
                left_over_quantity = 0

                new_quantity = round(current_order.quantity - plan_quantity)

                # check if exceed the stock, then push it to leftover
                if new_quantity < 0:
                    left_over_quantity += abs(new_quantity)
                    new_quantity = 0
                    plan_quantity = current_order.quantity

                current_order.quantity = new_quantity
                blade2_params = {
                    "order": current_order,
                    "plan_quantity": plan_quantity,
                    "out": item["out"],
                    "paper_roll": data["roll"],
                    "blade_type": "Blade 2",
                    "order_leftover": new_quantity,
                }

                blade2_params_list.append(blade2_params)

    if left_over_quantity:
        raise ValueError("order are out of stock!")
        return

    database_formatter(blade1_params, blade2_params_list)
