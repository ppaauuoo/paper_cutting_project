from django.urls import path
from . import views

urlpatterns = [
    path('', views.optimize_order, name='optimize_order'),
    path('get_progress/', views.get_progress, name='get_progress'),
]
