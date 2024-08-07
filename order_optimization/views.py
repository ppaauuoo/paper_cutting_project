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


ROLL_PAPER = [66, 68, 70, 73, 74, 75, 79, 82, 85, 88, 91, 93, 95, 97]
FILTER = [16,8,6,4,2]
OUT_RANGE = [7,5,3]
TUNING_VALUE = [3,2]
CACHE_TIMEOUT = 300  # Cache timeout in seconds (e.g., 5 min)


@login_required
def optimize_order(request):
    cache.delete("optimization_progress")  # Clear previous progress
    cache.delete("try_again")  # Clear previous progress
    results = cache.get("optimization_results")
    csv_files = CSVFile.objects.all()
    form = CSVFileForm()

    if request.method == "POST":
        if "optimize" in request.POST:
            results = manual_configuration(request)
            cache.set("optimization_results", results, CACHE_TIMEOUT)
        elif "upload" in request.POST:
            handle_file_upload(request)
        elif "delete" in request.POST:
            handle_file_deletion(request)
        elif "auto" in request.POST:
            results = auto_configuration(request)
            cache.set("optimization_results", results, CACHE_TIMEOUT)
        elif "common_trim" in request.POST:
            results = handle_common(request,'trim')
            cache.set("optimization_results", results, CACHE_TIMEOUT)
        elif "common_order" in request.POST:
            results = handle_common(request,'order')
            cache.set("optimization_results", results, CACHE_TIMEOUT)

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


def manual_configuration(request):
    tuning_value = int(request.POST.get("tuning_value"))
    size_value = int(request.POST.get("size_value"))
    filter_value = int(request.POST.get("filter_value"))
    file_id = request.POST.get("file_id")
    num_generations = int(request.POST.get("num_generations"))
    out_range = int(request.POST.get("out_range"))

    deadline_toggle = 0 if request.POST.get("deadline_toggle") == "true" else -1

    csv_file = get_object_or_404(CSVFile, id=file_id)
    file_path = csv_file.file.path

    orders = ORD(
        file_path,
        deadline_scope=deadline_toggle,
        filter=True,
        filter_value=filter_value,
        size=size_value,
        tuning_values=tuning_value,
    ).get()

    if len(orders) <= 0:
        messages.error(request, "Eror 404: No orders were found. Please try again.")
        return

    return handle_optimization(request, orders, num_generations, out_range, size_value)


def auto_configuration(request):
    cache.delete("optimization_progress")  # Clear previous progress
    again = cache.get("try_again", 0)
    file_id = request.POST.get("file_id")
    csv_file = get_object_or_404(CSVFile, id=file_id)
    file_path = csv_file.file.path

    num_generations = 50+(10*again)
    deadline_toggle = 0
    tuning_value = 2 if again is None else 3
    out_range = 3+again

    orders = []
    i = 0
    j = 0
    while len(orders) == 0:
        orders = ORD(
            filter_value=FILTER[-i],
            size=ROLL_PAPER[j],
            path=file_path,
            deadline_scope=deadline_toggle,
            filter=True,
            tuning_values=tuning_value,
        ).get()
        i += 1
        if i > len(FILTER):
            i = 0
            j += 1

    return handle_optimization(request, orders, num_generations, out_range, ROLL_PAPER[j])


def handle_optimization(request, orders, num_generations, out_range, size_value):
    ga_instance = GA(
        orders,
        size=size_value,
        num_generations=num_generations,
        out_range=out_range,
        showOutput=False,
        save_solutions=False,
        showZero=False,
    )
    ga_instance.get(update_progress=update_progress).run()

    fitness_values = ga_instance.fitness_values

    output_data = ga_instance.output.to_dict("records")

    init_order_number, foll_order_number = ORD.handle_orders_logic(output_data)

    results = {
        "output": output_data,
        "roll": ga_instance.PAPER_SIZE,
        "fitness": size_value + fitness_values,
        "trim": abs(fitness_values),
        "init_order_number": init_order_number,
        "foll_order_number": foll_order_number
    }

    if abs(fitness_values) > 3.10:
        again = cache.get("try_again", 0)

        if "auto" in request.POST and again <= 4:
            again+=1
            cache.set("try_again", again, CACHE_TIMEOUT)
            return auto_configuration(request)

        messages.error(
            request, "Optimizing finished with unsatisfied result, please try again."
        )
        return results

    messages.success(request, "Optimizing finished.")
    return results


def handle_common(request, action):
    results = cache.get("optimization_results")
    best_fitness = -results["trim"]
    best_output = None
    best_index = None

    for i, item in enumerate(results["output"]):
        if action == "order" and i == 0:
            continue
        
        size_value = item["cut_width"] + results["trim"] if action=="order" else item['cut_width']
        file_path = "./data/true_ordplan.csv"

        orders = ORD(
            path=file_path,
            deadline_scope=-1,
            filter=False,
            filter_value=16,
            size=size_value,
            tuning_values=2 if action=="trim" else 1,
            common=True,
        ).get()

        match action:
            case 'trim':
                cache.delete("optimization_progress")  # Clear previous progress
                ga_instance = GA(orders, size=size_value, out_range=3, num_generations=50)
                ga_instance.get(update_progress=update_progress).run()
                if abs(ga_instance.fitness_values) < abs(best_fitness):
                    best_fitness = ga_instance.fitness_values
                    best_output = ga_instance.output.to_dict("records")
                    best_index = i
            case 'order':
                first_common_order = orders[0]
                if first_common_order['จำนวนสั่งขาย']+results['output'][-1]['num_orders'] > results['foll_order_number']:
                    best_fitness = ga_instance.fitness_values
                    output = pd.DataFrame(
                        {
                            "order_number": first_common_order["เลขที่ใบสั่งขาย"],
                            "num_orders": first_common_order["จำนวนสั่งขาย"],
                            "cut_width": first_common_order["ตัดกว้าง"],
                            "cut_len": first_common_order["ตัดยาว"],
                            "type": first_common_order["ประเภททับเส้น"],
                            "deadline": first_common_order["กำหนดส่ง"],
                            "diff": first_common_order["diff"],
                            "out": 1,
                        }
                    )                    
                    best_output = output.todict('records')
                    best_index = i


    if best_index is not None:
        match action:
            case 'trim':
                results["output"].pop(best_index) 
                results["output"] = [
                    item for item in results["output"] if item.get("out", 0) >= 1
                ]
                results["output"].extend(best_output)
                results["fitness"] = (
                    results["fitness"]
                    - results["output"][best_index]["cut_width"]
                    + best_fitness
                    + size_value
                )
                results["trim"] = abs(best_fitness)
            case 'order':
                results["output"].extend(best_output)


        messages.success(request, "Common order found.")
    else:
        messages.error(request, "No suitable common order found.")

    return results


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