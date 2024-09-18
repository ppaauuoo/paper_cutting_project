from django.shortcuts import render

def paper_subsitution_view(request):
    return render(request,'paper.html')