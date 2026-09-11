from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='main'),
    path('explore/', views.explore, name='explore'),
    path('mypage/', views.mypage, name='mypage'),
    path('login/', views.login_view, name='login'),
]