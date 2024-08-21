from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_optimizer_view, name='order_optimizer_view'),
    path('progress/', views.progress_view, name='progress_view'),
    path('preview_data/', views.preview_data, name='preview_data'),
    path('optimized_orders/', views.optimized_orders_view, name='optimized_orders_view'),
    path('test/', views.test, name='test'),
    path('test_data/', views.test_data, name='test_data'),

]
