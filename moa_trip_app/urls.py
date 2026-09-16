from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.main, name='main'),
    path('explore/', views.explore, name='explore'),
    path('detail/', views.detail, name='detail'),
    path('planner/', views.planner, name='planner'),
    path('mypage/', views.mypage, name='mypage'),
    path('login/', views.login, name='login'),
    path('login/login_ok/', views.login_ok, name='login_ok'),
    path('logout/', views.logout, name='logout'),
    path('admin/', views.admin, name='admin'),
]