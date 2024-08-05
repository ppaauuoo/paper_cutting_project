from django.core.cache import cache
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
import pandas as pd
from .models import CSVFile
from .forms import CSVFileForm
from .modules.ordplan import ORD
from .modules.ga import GA
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.shortcuts import redirect
from .forms import LoginForm

ROLL_PAPER = [68, 73, 75, 79, 82, 85, 88, 91, 95, 97]
CACHE_TIMEOUT = 300  # Cache timeout in seconds (e.g., 5 min)

@login_required
def optimize_order(request):
    results = cache.get('optimization_results')
    csv_files = CSVFile.objects.all()
    form = CSVFileForm()

    if request.method == 'POST':
        if 'optimize' in request.POST:
            results = manual_configuration(request)
            cache.set('optimization_results', results, CACHE_TIMEOUT)
        elif 'upload' in request.POST:
            handle_file_upload(request)
        elif 'delete' in request.POST:
            handle_file_deletion(request)
        elif 'auto' in request.POST:
            results=auto_configuration(request)
            cache.set('optimization_results', results, CACHE_TIMEOUT)

    context = {
        'results': results,
        'roll_paper': ROLL_PAPER,
        'csv_files': csv_files,
        'form': form
    }
    return render(request, 'optimize.html', context)

def manual_configuration(request):
    tuning_value = int(request.POST.get('tuning_value'))
    size_value = int(request.POST.get('size_value'))
    filter_value = int(request.POST.get('filter_value'))
    file_id = request.POST.get('file_id')
    num_generations = int(request.POST.get('num_generations'))

    deadline_toggle = 0 if request.POST.get('deadline_toggle') == 'true' else -1

    csv_file = get_object_or_404(CSVFile, id=file_id)
    file_path = csv_file.file.path


    orders = ORD(file_path, deadline_scope=deadline_toggle, filter=True, filter_value=filter_value, size=size_value, tuning_values=tuning_value).get()
    
    if len(orders) <=0:
        messages.error(request, 'Eror 404: No orders were found. Please try again.')
        return
    
    return handle_optimization(request, orders, num_generations,size_value)

def auto_configuration(request):

    file_id = request.POST.get('file_id')
    csv_file = get_object_or_404(CSVFile, id=file_id)
    file_path = csv_file.file.path

    filter_value = 8
    num_generations = 50
    deadline_toggle = 0
    size_value = 0
    tuning_value = 0

    orders = ORD(auto=True, path=file_path, deadline_scope=deadline_toggle, filter=True, filter_value=filter_value, size=size_value, tuning_values=tuning_value).get()

    if len(orders) <=0:
        filter_value = 16
        orders = ORD(auto=True, path=file_path, deadline_scope=deadline_toggle, filter=True, filter_value=filter_value, size=size_value, tuning_values=tuning_value).get()

    return handle_optimization(request, orders, num_generations,size_value)
    


def handle_optimization(request, orders, num_generations,size_value):
    ga_instance = GA(orders, size=size_value, num_generations=num_generations,showOutput=False,save_solutions=False,showZero=False)
    ga_instance.get().run()
    
    fitness_values = ga_instance.fitness_values

    output_data = ga_instance.output.to_dict('records')

    results = {
        'output': output_data,
        'roll': ga_instance.PAPER_SIZE,
        'fitness': size_value + fitness_values,
        'trim': abs(fitness_values)
    }

    if abs(fitness_values) > 3.10:
        messages.error(request, 'Optimizing finished with unsatisfied result, please try again.')
        return results
    
    messages.success(request, 'Optimizing finished.')
    return results

def handle_file_upload(request):
    form = CSVFileForm(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        messages.success(request, 'File uploaded successfully.')
    else:
        messages.error(request, 'Error uploading file.')

def handle_file_deletion(request):
    file_id = request.POST.get('file_id')
    csv_file = get_object_or_404(CSVFile, id=file_id)
    csv_file.delete()
    messages.success(request, 'File deleted successfully.')



def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('optimize_order')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})