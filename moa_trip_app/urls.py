from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='main'),
    path('base/', views.base, name='base'),
    path('explore/', views.explore, name='explore'),
    path('spot/<str:spot_code>/', views.spot_detail, name='spot_detail'),
    path('mypage/', views.mypage, name='mypage'),
    path('login/', views.login_view, name='login'),
]