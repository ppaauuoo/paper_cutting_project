from django.shortcuts import render
from .project import ORD, GA, LP
import pandas as pd

roll_paper = [68, 73, 75, 79, 82, 85, 88, 91, 95, 97]

def optimize_order(request):
    results = None
    if request.method == 'POST':
        tuning_value = int(request.POST.get('tuning_value', 2))
        size_value = int(request.POST.get('size_value', 73))
        
        # Use your existing code here
        orders = ORD("data/true_ordplan.csv", deadline_scope=0).get(deadline=False)
        
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
    
    return render(request, 'optimize.html', {'results': results, 'roll_paper': roll_paper})
