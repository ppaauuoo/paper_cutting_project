from django.core.cache import cache
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
import pandas as pd
from .models import CSVFile
from .forms import CSVFileForm, LoginForm
from .modules.ordplan import ORD
from .modules.ga import GA
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.http import JsonResponse
from typing import Callable, Dict, List, Optional, Tuple

ROLL_PAPER = [66, 68, 70, 73, 74, 75, 79, 82, 85, 88, 91, 93, 95, 97]
FILTER = [16,8,6,4,2]
OUT_RANGE = [7,5,3]
TUNING_VALUE = [3,2]
CACHE_TIMEOUT = 300  # Cache timeout in seconds (e.g., 5 min)

@login_required
def optimize_order(request):
    if request.method == "POST":
        match request.POST:
            case {"optimize": _}:
                manual_configuration(request)
            case {"upload": _}:
                handle_file_upload(request)
            case {"delete": _}:
                handle_file_deletion(request)
            case {"auto": _}:
                auto_configuration(request)
            case {"common_trim": _}:
                handle_common(request)
            case {"common_order": _}:
                handle_filler(request)

    cache.delete("optimization_progress")  # Clear previous progress
    csv_files = CSVFile.objects.all()
    form = CSVFileForm()

    results = cache.get("optimization_results")

    context = {
        "results": results,
        "roll_paper": ROLL_PAPER,
        "filter": FILTER,
        "out_range": OUT_RANGE,
        "tuning_value": TUNING_VALUE,
        "csv_files": csv_files,
        "form": form,
    }
    return render(request, "optimize.html", context)

def handle_selector(request)->Dict:
    selector_id = int(request.POST.get("selector_id"))
    selector_out = int(request.POST.get("selector_out"))
    return {
        "order_id": selector_id,
        "out": selector_out
    }

def manual_configuration(request)->Callable:
    file_id = request.POST.get("file_id")
    size_value = int(request.POST.get("size_value"))
    deadline_toggle = -1 if request.POST.get("deadline_toggle") == "true" else 0
    filter_value = int(request.POST.get("filter_value"))
    tuning_value = int(request.POST.get("tuning_value"))
    num_generations = int(request.POST.get("num_generations"))
    out_range = int(request.POST.get("out_range"))
    orders = get_orders(request, file_id,size_value,deadline_toggle,filter_value,tuning_value)
    if len(orders) <= 0:
        messages.error(request, "Eror 404: No orders were found. Please try again.")
        return
    return handle_optimization(request, orders, num_generations, out_range, size_value)

def auto_configuration(request)->Callable:
    again = cache.get("try_again", 0)
    num_generations = 50+(10*again)
    out_range = 2+again
    orders,size = search_compat_size_and_filter(request)
    return handle_optimization(request, orders, num_generations, out_range, size)

def search_compat_size_and_filter(request):
    i = 0
    j = 7
    orders = cache.get('auto_order', [])
    size = cache.get('order_size', ROLL_PAPER[j])
    file_id = request.POST.get("file_id")
    tuning_value = TUNING_VALUE[1]
    while len(orders) <= 0:
        orders = get_orders(request, file_id,size,FILTER[-i],tuning_value)
        i += 1
        if i > len(FILTER):
            i = 0
            j+=1
            size=ROLL_PAPER[j]

    cache.set('auto_order', orders, CACHE_TIMEOUT)
    cache.set('order_size', size, CACHE_TIMEOUT)

    return (orders, size)


def handle_optimization(request, orders: ORD, num_generations: int, out_range: int, size_value: float)->Callable:
    ga_instance = run_genetic_algorithm(request,orders, size_value, out_range, num_generations)
    fitness_values, output_data = get_outputs(ga_instance)
    init_order_number, foll_order_number = ORD.handle_orders_logic(output_data)
    results = results_format(ga_instance, output_data, size_value, fitness_values, init_order_number, foll_order_number)
    
    if abs(fitness_values) <= 3 and abs(fitness_values) >= 1:
        messages.success(request, "Optimizing finished.")
        return cache.set("optimization_results", results, CACHE_TIMEOUT)
    
    if "auto" in request.POST:
        return recursive_auto_logic(request)
    
    satisfied  = 1 if request.POST.get("satisfied") == "true" else 0
    if satisfied:
        return handle_optimization(request, orders, num_generations, out_range, size_value)
    
    messages.error(request, "Optimizing finished with unsatisfied result, please try again.")
    return cache.set("optimization_results", results, CACHE_TIMEOUT)

def results_format(ga_instance: object, output_data: dict, size_value: int, fitness_values: float, init_order_number: int, foll_order_number: int) -> Dict:
    return {
        "output": output_data,
        "roll": ga_instance.PAPER_SIZE,
        "fitness": size_value + fitness_values,
        "trim": abs(fitness_values),
        "init_order_number": init_order_number,
        "foll_order_number": foll_order_number
    }

def recursive_auto_logic(request):
    again = cache.get("try_again", 0)
    if again <= 4:
        again+=1
        cache.set("try_again", again, CACHE_TIMEOUT)
        return auto_configuration(request) 
    
    cache.delete("try_again")
    return messages.error(request, "Error : Auto config malfuncioned, please contact admin.")

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
        size_value = item["cut_width"] + results["trim"]
        orders = get_orders(request, file_id,size_value,deadline_scope=-1,tuning_values=3, filter=False,common=True)
        ga_instance = run_genetic_algorithm(orders, size_value)
    

        if abs(ga_instance.fitness_values) < abs(best_fitness):
            best_fitness, best_output = get_outputs(ga_instance)
            best_index = i

    if best_index is not None:
        update_results(results, best_index, best_output, best_fitness, size_value)
        messages.success(request, "Common order found.")
    else:
        messages.error(request, "No suitable common order found.")

    return cache.set("optimization_results", results, CACHE_TIMEOUT)

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
        selector = handle_selector(request)['order_id']
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

def run_genetic_algorithm(
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
        selector=handle_selector(request)
    )
    ga_instance.get(update_progress=update_progress).run()

    return ga_instance

def update_results(results: Dict, best_index: int, best_output: List[Dict], best_fitness: float, size_value: float) -> None:
    """Update results with the best common order."""
    results["output"][best_index]["out"] -= 1
    results["output"] = [item for item in results["output"] if item.get("out", 0) >= 1]
    results["output"].extend(best_output)
    results["fitness"] = (
        results["fitness"]
        - results["output"][best_index]["cut_width"]
        + best_fitness
        + size_value
    )
    results["trim"] = abs(best_fitness)

def handle_file_upload(request):
    form = CSVFileForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        messages.success(request, "File uploaded successfully.")
    else:
        messages.error(request, "Error uploading file.")

def handle_file_deletion(request):
    file_id = request.POST.get("file_id")
    csv_file = get_object_or_404(CSVFile, id=file_id)
    csv_file.delete()
    messages.success(request, "File deleted successfully.")

def get_file_preview(request):
    file_id = request.GET.get("file_id")
    cache_key = f"file_preview_{file_id}"

    df = cache.get(cache_key)

    if df:
        return JsonResponse({'file_preview': df})

    csv_file = get_object_or_404(CSVFile, id=file_id)
    file_path = csv_file.file.path

    # Load the CSV file into a DataFrame
    df = (ORD(path=file_path).get()).to_dict('records')

    cache.set(cache_key, df, CACHE_TIMEOUT)
    return JsonResponse({'file_preview': df})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("optimize_order")
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})

def get_progress(request):
    progress = cache.get("optimization_progress", 0)
    return JsonResponse({'progress': progress})

def update_progress(progress):
    cache.set("optimization_progress", progress, CACHE_TIMEOUT)