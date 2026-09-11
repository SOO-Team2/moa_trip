from django.urls import path
from . import views

urlpatterns = [
    path('', views.base, name='base'),
    path('spot/<str:spot_code>/', views.spot_detail, name='spot_detail'),
]