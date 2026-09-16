from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.main, name='main'),
    path('explore/', views.explore, name='explore'),
    path('detail/', views.detail, name='detail'),
    path('planner/', views.planner, name='planner'),
    path('mypage/', views.mypage, name='mypage'),
    path('mypage/delete/<str:itinerary_code>/', views.delete_itinerary, name='delete_itinerary'),
    path('login/', views.login, name='login'),
    path('login/login_ok/', views.login_ok, name='login_ok'),
    path('logout/', views.logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    path('admin/', views.admin, name='admin'),
]