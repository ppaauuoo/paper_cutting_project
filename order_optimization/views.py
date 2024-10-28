from django.core.cache import cache
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.http import HttpRequest

from order_optimization.controller import optimizer_controller
from order_optimization.formatter import plan_orders_formatter

from .models import CSVFile
from .forms import CSVFileForm, LoginForm
from .handler import (
    handle_export,
    handle_reset,
    handle_saving,
)

from typing import Dict, Callable

from icecream import ic

from ordplan_project.settings import (
    ROLL_PAPER,
    FILTER,
    OUT_RANGE,
    TUNING_VALUE,
)


@login_required
def order_optimizer_view(request: HttpRequest):
    if request.method == "POST":
        handlers: Dict[str, Callable] = {
            "save": handle_saving,
            "reset": handle_reset,
            "export": handle_export,
            "ai": optimizer_controller,
        }
        for action, handler in handlers.items():
            if action in request.POST:
                ic(action, handler)  # Debug print
                handler(request)

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
        "progress": 0,
    }
    return render(request, "optimize.html", context)


def order_optimizer_api(request: HttpRequest):
    if request.method == "POST":
        handlers: Dict[str, Callable] = {
            "save": handle_saving,
            "reset": handle_reset,
            "export": handle_export,
            "ai": optimizer_controller,
        }
        for action, handler in handlers.items():
            if action in request.POST:
                ic(action, handler)  # Debug print
                handler(request)


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
        "progress": round(progress, 3),
    }
    return render(request, "progress_bar.html", context)


def progress_api(request):
    progress = cache.get("api_progress", 0)
    context = {
        "progress": round(progress, 3),
    }
    return context


def optimized_orders_view(request):
    df = plan_orders_formatter()
    optimized_output = df.to_dict("records")
    return render(request, "saved_orders_table.html", {"data": optimized_output})


def optimized_orders_api(request):
    df = plan_orders_formatter()
    optimized_output = df.to_dict("records")
    return optimized_output


def test(request):
    csv_files = CSVFile.objects.all()
    context = {
        "csv_files": csv_files,
    }
    return render(request, "test.html", context)


def test_data(request):

    return render(request, "test_table.html")
