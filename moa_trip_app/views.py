from django.shortcuts import render
from .models import TouristSpot, Region
from django.db.models import Avg, Count

def main(request):
    return render(request, 'main.html')

def explore(request):
    selected_region = request.GET.get('region')
    selected_rating = request.GET.get('min_rating')
    spots = TouristSpot.objects.select_related('region').annotate(
        avg_rating=Avg('review__rating'),
        review_count=Count('review'),
    )
    if selected_region:
        spots = spots.filter(region_id=selected_region)
    if selected_rating:
        try:
            spots = spots.filter(avg_rating__gte=float(selected_rating))
        except ValueError:
            pass
    context = {
        'spots': spots,
        'regions': Region.objects.all(),
        'selected_region': selected_region,
        'selected_rating': selected_rating,
    }
    return render(request, 'explore.html', context)

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