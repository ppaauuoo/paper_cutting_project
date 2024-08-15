from .modules.ordplan import ORD

from django.shortcuts import get_object_or_404

from .models import CSVFile
  
from typing import Dict, List, Tuple
from .modules.ga import GA
from django.core.cache import cache

from dataclasses import dataclass

from django.conf import settings
CACHE_TIMEOUT = settings.CACHE_TIMEOUT 


#TODO
def get_orders(
    request,
    file_id: str,
    size_value: float,
    deadline_scope: int = 0,
    filter_value: int = 16,
    tuning_values: int = 3,
    filter: bool = True,
    common: bool = False,
    filler: int = 0,
    first_date_only: bool = False
) -> ORD:
    csv_file = get_csv_file(file_id)
    file_path = csv_file.file.path
    return ORD(
        path=file_path,
        deadline_scope=deadline_scope,
        filter=filter,
        filter_value=filter_value,
        size=size_value,
        tuning_values=tuning_values,
        common=common,
        filler = filler,
        selector = get_selected_order(request),
        first_date_only=first_date_only
    ).get()

def get_selected_order(request)->Dict|None:
    selector_id = request.POST.get("selector_id")
    if not selector_id: return None
        
    selector_id = int(selector_id)
    selector_out = int(request.POST.get("selector_out"))
    return {
        "order_id": selector_id,
        "out": selector_out
    }

def get_genetic_algorithm(
    request,
    orders: ORD,
    size_value: float,
    out_range: int = 3,
    num_generations: int = 50,
    show_output: bool = False,
) -> GA:
    cache.delete("optimization_progress")

    ga_instance = GA(
        orders,
        size=size_value,
        out_range=out_range,
        num_generations=num_generations,
        showOutput=show_output,
        selector=get_selected_order(request)
    )

    ga_instance.get(set_progress=set_progress).run()
    return ga_instance






def set_progress(progress) -> None:
    cache.set("optimization_progress", progress, CACHE_TIMEOUT)

def get_csv_file(file_id: str) -> CSVFile:
    return get_object_or_404(CSVFile, id=file_id)

# def get_ord(config: OrdersConfig, request) -> ORD:
#     return ORD(
#         path=config.file_path,
#         deadline_scope=config.deadline_scope,
#         filter=config.filter,
#         filter_value=config.filter_value,
#         size=config.size_value,
#         tuning_values=config.tuning_values,
#         common=config.common,
#         filler=config.filler,
#         selector=get_selected_order(request),
#         first_date_only=config.first_date_only
#     ).get()

def get_outputs(ga_instance: GA) -> Tuple[float, List[Dict]]:
    fitness_values = ga_instance.fitness_values
    output_data = ga_instance.output.to_dict("records")
    return fitness_values, output_data
