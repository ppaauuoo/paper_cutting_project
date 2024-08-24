from django.core.cache import cache
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.conf import settings
import pandas as pd

from .models import CSVFile, OptimizationPlan, OrderList, PlanOrder
from .forms import CSVFileForm, LoginForm
from .handler import handle_common, handle_filler, handle_manual_config, handle_auto_config, handle_reset, handle_saving
from .getter import get_csv_file, get_orders

from icecream import ic

ROLL_PAPER = settings.ROLL_PAPER 
FILTER = settings.FILTER 
OUT_RANGE = settings.OUT_RANGE 
TUNING_VALUE = settings.TUNING_VALUE 
CACHE_TIMEOUT = settings.CACHE_TIMEOUT 

@login_required
def order_optimizer_view(request):
    if request.method == "POST":
        match request.POST:
            case {"optimize": _}:
                handle_manual_config(request)
            case {"upload": _}:
                file_upload_view(request)
            case {"delete": _}:
                file_deletion_view(request)
            case {"auto": _}:
                handle_auto_config(request)
            case {"common_trim": _}:
                handle_common(request)
            case {"common_order": _}:
                handle_filler(request)
            case {"save": _}:
                handle_saving(request)
            case {"reset": _}:
                handle_reset()

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
        "progress": 0
    }
    return render(request, "optimize.html", context)

def file_upload_view(request):
    form = CSVFileForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        messages.success(request, "File uploaded successfully.")
    else:
        messages.error(request, "Error uploading file.")

def file_deletion_view(request):
    csv_file = get_csv_file(request.POST.get("file_id"))
    csv_file.delete()
    messages.success(request, "File deleted successfully.")

def login_view(request):
    if request.method != "POST":
        return render(request, "login.html", {"form": LoginForm()})

    form = LoginForm(request, data=request.POST)
    if form.is_valid():
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("order_optimizer_view")
    
    return render(request, "login.html", {"form": form})

def progress_view(request):
    progress = cache.get("optimization_progress", 0)
    context = {
        'progress': round(progress, 3),
    }
    return render(request, 'progress_bar.html', context)

def optimized_orders_view(request):
    # Get all PlanOrder objects as a list of dictionaries
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
    
     
    return render(request, 'saved_orders_table.html', {'data': ic(optimized_output)})

def preview_data(request):
    file_id = request.GET.get("file_id")
    cache_key = f"file_selector_{file_id}"
    df = cache.get(cache_key)

    if df is not None:
        return render(request, 'preview_table.html', {'preview_data': df})

    df = get_orders(request, file_id, filter_diff=False)

    # Format datetime columns as per the instruction
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            df[column] = df[column].dt.strftime("%m/%d/%y")
    df = df.to_dict(orient='records')
    cache.set(cache_key, df, CACHE_TIMEOUT)
    return render(request, 'preview_table.html', {'preview_data': df})

def search_preview_data(request):
    search_term = request.GET.get('previewSearchInput')
    file_id = request.GET.get("file_id")
    cache_key = f"file_selector_{file_id}"
    data_dict = cache.get(cache_key)

    if search_term:
        # Filter the dictionary
        filtered_dict = {key: value for key, value in data_dict.items() 
                         if any(search_term in str(v).lower() for v in value.values())}
    else:
        filtered_dict = data_dict

    return render(request, 'preview_table.html', {'data': filtered_dict})

def test(request):
    csv_files = CSVFile.objects.all()
    context = {
        "csv_files": csv_files,
    }
    return render(request, 'test.html',context)

def test_data(request):
    
    return render(request, 'test_table.html')