from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.main, name='main'),
    path('explore/', views.explore, name='explore'),
    path('mypage/', views.mypage, name='mypage'),
]