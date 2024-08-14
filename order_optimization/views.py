from django.core.cache import cache
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import CSVFile
from .forms import CSVFileForm, LoginForm

from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.http import JsonResponse

from .handler import handle_common, handle_filler, handle_manual_config, handle_auto_config, handle_saving
from .modules.ordplan import ORD

from django.conf import settings

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
    file_id = request.POST.get("file_id")
    csv_file = get_object_or_404(CSVFile, id=file_id)
    csv_file.delete()
    messages.success(request, "File deleted successfully.")

def file_selector_view(request):
    file_id = request.GET.get("file_id")
    cache_key = f"file_selector_{file_id}"

    df = cache.get(cache_key)

    if df:
        return JsonResponse({'file_selector': df})

    csv_file = get_object_or_404(CSVFile, id=file_id)
    file_path = csv_file.file.path

    # Load the CSV file into a DataFrame
    df = (ORD(path=file_path).get()).to_dict('records')

    cache.set(cache_key, df, CACHE_TIMEOUT)
    return JsonResponse({'file_selector': df})

def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect("order_optimizer_view")
    else:
        form = LoginForm()
    return render(request, "login.html", {"form": form})

def progress_view(request):
    progress = cache.get("optimization_progress", 0)
    return JsonResponse({'progress': progress})

def optimized_orders_view(request):
    df = cache.get("optimized_orders_view")
    return JsonResponse({'optimized_orders': df})