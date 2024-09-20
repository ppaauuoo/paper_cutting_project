from django.shortcuts import render
from modules.yggdrasil import YDF
from icecream import ic

def paper_subsitution_view(request):
    # Make prediction using the model
    model = YDF()
    if request.method == 'POST':
        test_input = {
            "front_sheet-O": [request.POST.get('front_sheet')],
            "c_wave-O": [request.POST.get("c_wave")],
            "middle_sheet-O": [request.POST.get("middle_sheet")],
            "b_wave-O": [request.POST.get("b_wave")],
            "back_sheet-O": [request.POST.get('back_sheet')]
        }
        prediction = model.predict(test_input)

    else:
        # If no POST request, set prediction to None
        prediction = None

    context = {
            'prediction' : prediction,
            'labels': model.labels,
            'post_data': request.POST
    }
    return render(request,'paper.html', context)
