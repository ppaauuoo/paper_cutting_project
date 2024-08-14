from .modules.ordplan import ORD

from typing import Callable, Dict
from django.contrib import messages
from django.core.cache import cache

import pandas as pd

from typing import Callable, Dict, List, Optional

from .getter import get_orders, get_outputs, get_genetic_algorithm

from django.conf import settings

ROLL_PAPER = settings.ROLL_PAPER 
FILTER = settings.FILTER 
OUT_RANGE = settings.OUT_RANGE 
TUNING_VALUE = settings.TUNING_VALUE 
CACHE_TIMEOUT = settings.CACHE_TIMEOUT 

def handle_manual_config(request)->Callable:
    file_id = request.POST.get("file_id")
    size_value = int(request.POST.get("size_value"))
    deadline_toggle = -1 if request.POST.get("deadline_toggle") == "true" else 0
    filter_value = int(request.POST.get("filter_value"))
    tuning_value = int(request.POST.get("tuning_value"))
    num_generations = int(request.POST.get("num_generations"))
    out_range = int(request.POST.get("out_range"))
    first_date_only = request.POST.get("first_date_only")
    orders = get_orders(request, file_id,size_value,deadline_toggle,filter_value,tuning_value,first_date_only)
    if len(orders) <= 0:
        messages.error(request, "Eror 404: No orders were found. Please try again.")
        return
    return handle_optimization(request, orders, num_generations, out_range, size_value)

def handle_auto_config(request)->Callable:
    again = cache.get("try_again", 0)
    num_generations = 50+(10*again)
    out_range = 2+again
    orders,size = auto_size_filter_logic(request)
    return handle_optimization(request, orders, num_generations, out_range, size)

def auto_size_filter_logic(request):
    i = 0
    j = 8
    orders = cache.get('auto_order', [])
    size = cache.get('order_size', ROLL_PAPER[j])
    file_id = request.POST.get("file_id")
    tuning_value = TUNING_VALUE[1]
    while len(orders) <= 0:
        orders = get_orders(request, file_id,size,FILTER[-i],tuning_value,first_date_only=True)
        i += 1
        if i > len(FILTER):
            i = 0
            j+=1
            size=ROLL_PAPER[j]

    cache.set('auto_order', orders, CACHE_TIMEOUT)
    cache.set('order_size', size, CACHE_TIMEOUT)

    return (orders, size)

def handle_optimization(request, orders: ORD, num_generations: int, out_range: int, size_value: float)->Callable:
    ga_instance = get_genetic_algorithm(request,orders, size_value, out_range, num_generations)
    fitness_values, output_data = get_outputs(ga_instance)
    init_order_number, foll_order_number = ORD.handle_orders_logic(output_data)
    results = results_format(ga_instance, output_data, size_value, fitness_values, init_order_number, foll_order_number)
    
    if abs(fitness_values) <= 3 and abs(fitness_values) >= 1:
        messages.success(request, "Optimizing finished.")
        return cache.set("optimization_results", results, CACHE_TIMEOUT)
    
    again = cache.get("try_again", 0)

    if "auto" in request.POST:
        if again <= 4:
            again+=1
            cache.set("try_again", again, CACHE_TIMEOUT)
            return handle_auto_config(request) 
        return messages.error(request, "Error : Auto config malfuncioned, please contact admin.")
    
    satisfied  = 1 if request.POST.get("satisfied") == "true" else 0
    if satisfied:
        if again <= 3:
            again+=1
            cache.set("try_again", again, CACHE_TIMEOUT)
            return handle_optimization(request, orders, num_generations, out_range, size_value)
    
    cache.delete("try_again")
    

    messages.error(request, "Optimizing finished with unsatisfied result, please try again.")
    return cache.set("optimization_results", results, CACHE_TIMEOUT)


def handle_common(request) -> Callable:
    """
    Handle common order optimization.

    Args:
        request: The HTTP request object.
        action: The action to perform ('trim' or 'order').

    Returns:
        Dict: The updated results dictionary.
    """
    results = cache.get("optimization_results")
    best_fitness = -results["trim"]
    best_output: Optional[List[Dict]] = None
    best_index: Optional[int] = None
    file_id = request.POST.get("selected_file_id")


    for i, item in enumerate(results["output"]):

        size_value = (item["cut_width"]*item["out"]) + results["trim"]
        orders = get_orders(request, file_id,size_value,deadline_scope=-1, filter=False, common=True)
        ga_instance = get_genetic_algorithm(request,orders,size_value, show_output=True)


        if abs(ga_instance.fitness_values) < abs(best_fitness):
            best_fitness, best_output = get_outputs(ga_instance)
            best_index = i

    if best_index is not None:
        update_results(results, best_index, best_output, best_fitness, size_value)
        messages.success(request, "Common order found.")
    else:
        messages.error(request, "No suitable common order found.")

    return cache.set("optimization_results", results, CACHE_TIMEOUT)


def update_results(results: Dict, best_index: int, best_output: List[Dict], best_fitness: float, size_value: float) -> None:
    """Update results with the best common order."""
    results["output"].pop(best_index)
    results["output"] = [item for item in results["output"] if item.get("out", 0) >= 1]
    results["output"].extend(best_output)

    for item in results["output"]: 
            results["fitness"] += item["cut_width"]*item["out"]
            print(results["fitness"])


    print("results['roll']:", results["roll"])
    print("results['output'][best_index]['cut_width']:", results["output"][best_index]["cut_width"])
    print("results['output'][best_index]['out']:", results["output"][best_index]["out"])
    print("best_fitness:", best_fitness)
    print("size_value:", size_value)
    results["trim"] = abs(best_fitness)

def handle_filler(request):
    results = cache.get("optimization_results")
    init_order = results['output'][0]['order_number']
    file_id = request.POST.get("selected_file_id")
    size_value = results['output'][0]['cut_width']
    init_out = results['output'][0]['out']
    orders = get_orders(request, file_id,size_value,deadline_scope=-1,tuning_values=1, filter=False,common=True,filler=init_order)
    i = 0
    while i < len(orders) and results['foll_order_number'] > results['output'][1]['num_orders'] + orders['จำนวนสั่งขาย'][i]: i += 1

    output = output_format(orders.iloc[i], init_out).to_dict(orient='records')
    results['output'].extend(output)
    return cache.set("optimization_results", results, CACHE_TIMEOUT)

def output_format(orders: ORD, init_out: int = 0) -> pd.DataFrame:
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



def results_format(ga_instance: object, output_data: dict, size_value: int, fitness_values: float, init_order_number: int, foll_order_number: int) -> Dict:
    return {
        "output": output_data,
        "roll": ga_instance.PAPER_SIZE,
        "fitness": size_value + fitness_values,
        "trim": abs(fitness_values),
        "init_order_number": init_order_number,
        "foll_order_number": foll_order_number
    }

def handle_saving(request):
    df = cache.get("optimized_orders_view", [])
    data = cache.get("optimization_results")
    cache.delete("optimization_results")
    df.append(data['output'])
    cache.set("optimized_orders_view", df, CACHE_TIMEOUT)





