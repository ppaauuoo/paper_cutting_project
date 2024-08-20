from django.core.cache import cache
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CSVFile, OptimizedOrder
from .forms import CSVFileForm, LoginForm

from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.http import JsonResponse

from .handler import handle_common, handle_filler, handle_manual_config, handle_auto_config, handle_reset, handle_saving
from .getter import get_csv_file, get_orders

from django.conf import settings

ROLL_PAPER = settings.ROLL_PAPER 
FILTER = settings.FILTER 
OUT_RANGE = settings.OUT_RANGE 
TUNING_VALUE = settings.TUNING_VALUE 
CACHE_TIMEOUT = settings.CACHE_TIMEOUT 

from icecream import ic


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
                handle_saving()
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

def file_selector_view(request):
    file_id = request.GET.get("file_id")
    cache_key = f"file_selector_{file_id}"
    df = cache.get(cache_key)

    if df:
        return JsonResponse({'file_selector': df})

    df = get_orders(request, file_id, filter_diff=False).to_dict(orient='records')
    cache.set(cache_key, df, CACHE_TIMEOUT)
    return JsonResponse({'file_selector': df})

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
    return JsonResponse({'progress': cache.get("optimization_progress", 0)})

def optimized_orders_view(request):
    saved_list = OptimizedOrder.objects.all()
    saved_list_data = [order.output for order in saved_list]
    return JsonResponse({'optimized_orders': saved_list_data})