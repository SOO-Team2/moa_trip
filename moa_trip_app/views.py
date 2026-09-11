from django.shortcuts import render
from django.db.models import Avg, Count
from .models import Touristspot, Review, Weathercache


def base(request):
    spots = (
        Touristspot.objects
        .annotate(avg_rating=Avg('review__rating'), review_count=Count('review'))
        .order_by('-avg_rating')[:4]
    )
    return render(request, 'base.html', {'spots': spots})


def spot_detail(request, spot_code):
    spot = (
        Touristspot.objects
        .filter(spot_code=spot_code)
        .annotate(avg_rating=Avg('review__rating'))
        .first()
    )

    if spot:
        reviews = spot.review_set.all().order_by('-create_date')
        weathers = Weathercache.objects.filter(region=spot.region).order_by('forecast_date')
    else:
        reviews = Review.objects.none()
        weathers = Weathercache.objects.none()

    today_weather = weathers.first() if weathers.exists() else None

    weekday_kr = ['월', '화', '수', '목', '금', '토', '일']

    weekly_weather = []
    for i, w in enumerate(weathers[:7]):
        weekly_weather.append({
            'label': '오늘' if i == 0 else weekday_kr[w.forecast_date.weekday()],
            'date': w.forecast_date,
            'desc': w.weather_condition,
            'temp_high': w.temp_high,
            'precip_pct': w.precip_pct,
        })

    context = {
        'page_obj': page_obj,
        'region': region,
        'regions': DUMMY_REGIONS,
        #'regions': all_regions,
        'total_count': len(spots),
        #total_count': spots.count(),

    }
    return render(request, 'explore.html', context)

def mypage(request):
    # user_id = request.session.get('user_id')
    # if not user_id:
    #     return redirect('login')

    # user = Users.objects.get(pk=user_id)

    # context = {
    #     "user": user,
    #     "favorites": user.favorite_set.select_related("spot"),
    #     "reviews": user.review_set.select_related("spot"),
    #     "itineraries": user.itinerary_set.all(),
    #     "pet_ok": request.GET.get("pet_ok") == "1",
    #     "free_only": request.GET.get("free") == "1",
    # }
    return render(request, "mypage.html") #context )