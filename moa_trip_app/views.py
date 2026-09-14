from django.shortcuts import render

def main(request):
    return render(request, 'main.html')

def explore(request):
    return render(request, 'explore.html')

def detail(request):
    return render(request, 'detail.html')

def planner(request):
    return render(request, 'planner.html')

def mypage(request):
    return render(request, 'mypage.html')

def login(request):
    return render(request, 'login.html')

def admin(request):
    return render(request, 'admin.html')