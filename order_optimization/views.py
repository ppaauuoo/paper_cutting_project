from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import CSVFile
from .forms import CSVFileForm
from .modules.ordplan import ORD
from .modules.ga import GA
from .modules.lp import LP
import pandas as pd

roll_paper = [68, 73, 75, 79, 82, 85, 88, 91, 95, 97]

def optimize_order(request):
    results = None
    csv_files = CSVFile.objects.all()
    form = CSVFileForm()

    if request.method == 'POST':
        if 'optimize' in request.POST:
            tuning_value = int(request.POST.get('tuning_value', 2))
            size_value = int(request.POST.get('size_value', 73))
            file_id = request.POST.get('file_id')
            
            csv_file = get_object_or_404(CSVFile, id=file_id)
            file_path = csv_file.file.path

            orders = ORD(file_path, deadline_scope=0).get(deadline=False)
            
            for i, width in enumerate(orders['ตัดกว้าง']):
                roll = ORD.calculate_roll_tuning(width, tuning_value)
                if roll:
                    break
            
            ga_instance = GA(orders, size=size_value, tuning_values=tuning_value, num_generations=50)  # Updated line
            ga_instance.get().run()
            
            fitness_values = ga_instance.fitness_values
            paper_size = size_value

            # Convert DataFrame to list of dictionaries
            output_data = ga_instance.output.to_dict('records')

            results = {
                'output': output_data,
                'roll': ga_instance.PAPER_SIZE,
                'fitness': paper_size + fitness_values,
                'trim': abs(fitness_values)
            }
        
        elif 'upload' in request.POST:
            form = CSVFileForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, 'File uploaded successfully.')
            else:
                messages.error(request, 'Error uploading file.')

        elif 'delete' in request.POST:
            file_id = request.POST.get('file_id')
            csv_file = get_object_or_404(CSVFile, id=file_id)
            csv_file.delete()
            messages.success(request, 'File deleted successfully.')
        

    return render(request, 'optimize.html', {
        'results': results,
        'roll_paper': roll_paper,
        'csv_files': csv_files,
        'form': form
    })
