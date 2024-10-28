from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_optimizer_view, name='order_optimizer_view'),
    path('api/optimize', views.order_optimizer_api,
         name='order_optimizer_api'),
    path('api/progress', views.progress_api, name='progress_api'),
    path('api/optimized', views.optimized_orders_api,
         name='optimized_orders_api'),
    path('progress/', views.progress_view, name='progress_view'),
    path('optimized_orders/', views.optimized_orders_view,
         name='optimized_orders_view'),
    path('test/', views.test, name='test'),
    path('test_data/', views.test_data, name='test_data'),

]
