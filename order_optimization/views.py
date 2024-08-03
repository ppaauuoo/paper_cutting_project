from django.core.cache import cache
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from .models import CSVFile
from .forms import CSVFileForm
from .modules.ordplan import ORD
from .modules.ga import GA

ROLL_PAPER = [68, 73, 75, 79, 82, 85, 88, 91, 95, 97]
CACHE_TIMEOUT = 300  # Cache timeout in seconds (e.g., 5 min)

def optimize_order(request):
    results = cache.get('optimization_results')
    csv_files = CSVFile.objects.all()
    form = CSVFileForm()

    if request.method == 'POST':
        if 'optimize' in request.POST:
            results = handle_optimization(request)
            cache.set('optimization_results', results, CACHE_TIMEOUT)
        elif 'upload' in request.POST:
            handle_file_upload(request)
        elif 'delete' in request.POST:
            handle_file_deletion(request)

    context = {
        'results': results,
        'roll_paper': ROLL_PAPER,
        'csv_files': csv_files,
        'form': form
    }
    return render(request, 'optimize.html', context)

def handle_optimization(request):
    tuning_value = int(request.POST.get('tuning_value'))
    size_value = int(request.POST.get('size_value'))
    file_id = request.POST.get('file_id')

    csv_file = get_object_or_404(CSVFile, id=file_id)
    file_path = csv_file.file.path

    orders = ORD(file_path, deadline_scope=-1).get()
    
    ga_instance = GA(orders, size=size_value, tuning_values=tuning_value, num_generations=50)
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