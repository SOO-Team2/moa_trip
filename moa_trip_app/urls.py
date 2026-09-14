from django.urls import path
from . import views

urlpatterns = [
<<<<<<< HEAD
    path('', views.base, name='base'),
    path('spot/<str:spot_code>/', views.spot_detail, name='spot_detail'),
=======
    path('', views.main, name='main'),
    path('explore/', views.explore, name='explore'),
    path('mypage/', views.mypage, name='mypage'),
    path('login/', views.login_view, name='login'),
>>>>>>> 2365b38490fff92721b7193d72d60b4980e05894
]