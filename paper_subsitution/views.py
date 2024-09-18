from django.shortcuts import render
from modules.yggdrasil import YDF


def paper_subsitution_view(request):
    test_input = {
        "front_sheet-O": ["CM97"],
        "c_wave-O": ["CM127"],
        "middle_sheet-O": ["CM127"],
        "b_wave-O": ["CM127"],
        "back_sheet-O": ["KB160"],
    }
    model = YDF()
    prediction = model.predict(test_input)

    test_input = {key.replace('-O', ''): value for key, value in test_input.items()}
    context = {
            'prediction' : prediction,
            'input': test_input
    }
    return render(request,'paper.html', context)
