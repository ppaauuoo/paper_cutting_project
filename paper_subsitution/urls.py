from django.urls import path
from . import views

urlpatterns = [
    path('paper', views.paper_subsitution_view, name='paper_subsitution_view'),
]