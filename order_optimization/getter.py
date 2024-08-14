from modules.ordplan import ORD
from modules.ga import GA

from django.shortcuts import get_object_or_404

from .models import CSVFile
  
from typing import Dict, List, Tuple
from django.core.cache import cache

from django.conf import settings

CACHE_TIMEOUT = settings.CACHE_TIMEOUT 

def set_progress(progress) -> None:
    cache.set("optimization_progress", progress, CACHE_TIMEOUT)

def get_selected_order(request)->Dict|None:
    selector_id = request.POST.get("selector_id")
    if selector_id:
        selector_id = int(selector_id)
        selector_out = int(request.POST.get("selector_out"))
        return {
            "order_id": selector_id,
            "out": selector_out
        }
    return None


def get_genetic_algorithm(
    request,
    orders: ORD,
    size_value: float,
    out_range: int = 3,
    num_generations: int = 50,
    show_output: bool = False,
) -> GA:
    """
    Run genetic algorithm optimization.

    Args:
        orders (ORD): The orders to optimize.
        size_value (float): The size value for optimization.
        out_range (int, optional): The out range parameter. Defaults to 3.
        num_generations (int, optional): The number of generations to run. Defaults to 50.

    Returns:
        GA: The genetic algorithm instance after running optimization.
    """
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
    """
    Get orders for optimization.

    Args:
        file_id (str): The ID of the CSV file.
        size_value (float): The size value for optimization.
        deadline_scope (int, optional): The deadline scope. Defaults to 0.
        filter_value (int, optional): The filter value. Defaults to 16.
        tuning_values (int, optional): The tuning values. Defaults to 3.
        filter (bool, optional): Whether to apply filtering. Defaults to True.
        common (bool, optional): Whether to use common optimization. Defaults to False.

    Returns:
        ORD: The ORD object with the retrieved orders.
    """
    csv_file = get_object_or_404(CSVFile, id=file_id)
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

def get_outputs(ga_instance: GA) -> Tuple[float, List[Dict]]:
    """
    Extract fitness values and output data from a GA instance.

    Args:
        ga_instance (GA): The Genetic Algorithm instance to extract data from.

    Returns:
        Tuple[float, List[Dict]]: A tuple containing:
            - fitness_values (float): The fitness values from the GA instance.
            - output_data (List[Dict]): The output data as a list of dictionaries.
    """
    fitness_values = ga_instance.fitness_values
    output_data = ga_instance.output.to_dict("records")
    return fitness_values, output_data
