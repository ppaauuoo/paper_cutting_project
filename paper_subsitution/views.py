from django.shortcuts import render
from modules.yggdrasil import YDF
from modules.cnb import CNB
from icecream import ic
from order_optimization.models import CSVFile
from order_optimization.getter import get_orders_cache
from typing import Dict, Callable

def paper_subsitution_view(request):
    # Make prediction using the model
    models:Dict[str,Callable] = {'ydf': YDF, 'cnb': CNB}
    labels = {
            "front_sheet": ['KS231','KS161','KB230','KS121','KB160','KB120','KAC125','KI128','KA125','KL250','CM97','KAV150','KAC155','KAC185','KA155','CM127','WLK154','KL125','KA185','KA225','KI158','KAC225','KI188','WLK174','KM120'],
            "c_wave": ['CM127','CM147','CM112','None','CM197','CM100','CME100'],
            "middle_sheet": ['None','CM127','CM147','CME100','CM112','CM197','CM97','CM100'],
            "b_wave": ['None','CM127','CM112','CM147','CM197','CM100','CME100','CM97'],
            "back_sheet": ['KB160','KB120','KB230','CM127','CM112','CM97','CM147','KL250','KAV150','CM100','CM197','CME100','KA155','KA225','KA185','KAC155']
        }


    if request.method == 'POST':
        file_id = request.POST.get('file_id')
        df_data = get_orders_cache(file_id)
        model = models.get(request.POST.get('models'))
        if model is None:
            raise ValueError("Model not found")

        model_instance = model()
        test_input = {
            "front_sheet-O": [request.POST.get('front_sheet')],
            "c_wave-O": [request.POST.get("c_wave")],
            "middle_sheet-O": [request.POST.get("middle_sheet")],
            "b_wave-O": [request.POST.get("b_wave")],
            "back_sheet-O": [request.POST.get('back_sheet')]
        }
        prediction = model_instance.predict(test_input)
        ic(prediction)

    else:
        # If no POST request, set prediction to None
        prediction = None

    csv_files = CSVFile.objects.all()
    context = {
            'prediction' : prediction,
            'labels': labels,
            "csv_files": csv_files,
            'post_data': request.POST
    }
    return render(request,'paper.html', context)
