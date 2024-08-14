from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_optimizer_view, name='order_optimizer_view'),
    path('progress/', views.progress_view, name='progress_view'),
    path('file_selector/', views.file_selector_view, name='file_selector_view'),
    path('optimized_orders/', views.optimized_orders_view, name='optimized_orders_view'),
]
