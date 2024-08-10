from django.urls import path
from . import views

urlpatterns = [
    path('', views.optimize_order, name='optimize_order'),
    path('get_progress/', views.get_progress, name='get_progress'),
    path('get_file_preview/', views.get_file_preview, name='get_file_preview'),
]
