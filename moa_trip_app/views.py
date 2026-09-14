import uuid
from django.shortcuts import render, redirect
from django.db.models import Avg, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

from .forms import LoginForm, SignupForm
from .models import Region, TouristSpot, Users, Review, WeatherCache


def main(request):
    spots = (
        TouristSpot.objects
        .annotate(avg_rating=Avg('review__rating'), review_count=Count('review'))
        .order_by('-avg_rating')[:4]
    )
    return render(request, 'main.html', {'spots': spots})


def base(request):
    spots = (
        TouristSpot.objects
        .annotate(avg_rating=Avg('review__rating'), review_count=Count('review'))
        .order_by('-avg_rating')[:4]
    )
    return render(request, 'base.html', {'spots': spots})


# ===== 임시 더미 데이터 (나중에 Region, TouristSpot 모델의 실제 쿼리셋으로 교체) =====
DUMMY_REGIONS = [
    {'code': 'seoul', 'name': '서울특별시'},
    {'code': 'gyeonggi', 'name': '경기도'},
    {'code': 'chungnam', 'name': '충청남도'},
    {'code': 'chungbuk', 'name': '충청북도'},
    {'code': 'jeju', 'name': '제주도'},
    {'code': 'gangwon', 'name': '강원도'},
    {'code': 'gyeongbuk', 'name': '경상북도'},
    {'code': 'gyeongnam', 'name': '경상남도'},
    {'code': 'jeonbuk', 'name': '전라북도'},
    {'code': 'jeonnam', 'name': '전라남도'},
]

DUMMY_SPOTS = [
    {'id': 1, 'name': '관광지 A', 'address': '지역명', 'fee': 0, 'rating': 4.6, 'review_count': 212, 'pet_allowed': True, 'image': None, 'region_code': 'jeju'},
    {'id': 2, 'name': '관광지 B', 'address': '지역명', 'fee': 5000, 'rating': 4.8, 'review_count': 1043, 'pet_allowed': False, 'image': None, 'region_code': 'jeju'},
    {'id': 3, 'name': '관광지 C', 'address': '지역명', 'fee': 0, 'rating': 4.7, 'review_count': 486, 'pet_allowed': True, 'image': None, 'region_code': 'jeju'},
    {'id': 4, 'name': '관광지 D', 'address': '지역명', 'fee': 0, 'rating': 4.4, 'review_count': 298, 'pet_allowed': True, 'image': None, 'region_code': 'jeju'},
]


def explore(request):
    region = request.GET.get('region', 'jeju')
    page_number = request.GET.get('page', 1)

    valid_codes = [r['code'] for r in DUMMY_REGIONS]
    if region not in valid_codes:
        region = 'jeju'

    spots = [s for s in DUMMY_SPOTS if s['region_code'] == region]

    paginator = Paginator(spots, 12)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'region': region,
        'regions': DUMMY_REGIONS,
        'total_count': len(spots),
    }
    return render(request, 'explore.html', context)


def spot_detail(request, spot_code):
    spot = (
        TouristSpot.objects
        .filter(spot_code=spot_code)
        .annotate(avg_rating=Avg('review__rating'))
        .first()
    )

    if spot:
        reviews = spot.review_set.all().order_by('-create_date')
        weathers = WeatherCache.objects.filter(region=spot.region).order_by('forecast_date')
    else:
        reviews = Review.objects.none()
        weathers = WeatherCache.objects.none()

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
        'spot': spot,
        'reviews': reviews,
        'today_weather': today_weather,
        'weekly_weather': weekly_weather,
    }
    return render(request, 'spot_detail.html', context)


def mypage(request):
    user_id = request.session.get('user_id')
    user = None
    if user_id:
        try:
            user = Users.objects.get(pk=user_id)
        except Users.DoesNotExist:
            user = None

    context = {
        'user': user,
    }
    return render(request, 'mypage.html', context)


def login_view(request):
    login_form = LoginForm()
    signup_form = SignupForm()
    active_tab = 'login'

    if request.method == 'POST' and 'password2' not in request.POST:
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            email = login_form.cleaned_data['email']
            password = login_form.cleaned_data['password']
            try:
                user = Users.objects.get(email=email)
            except Users.DoesNotExist:
                user = None

            if user is not None and check_password(password, user.pw):
                request.session['user_id'] = user.user_id
                if not login_form.cleaned_data['remember']:
                    request.session.set_expiry(0)
                return redirect('main')
            login_form.add_error(None, '이메일 또는 비밀번호가 올바르지 않습니다.')

    elif request.method == 'POST':
        active_tab = 'signup'
        signup_form = SignupForm(request.POST)
        if signup_form.is_valid():
            user = Users.objects.create(
                user_id=uuid.uuid4().hex[:20],
                email=signup_form.cleaned_data['email'],
                nickname=signup_form.cleaned_data['nickname'],
                pw=make_password(signup_form.cleaned_data['password']),
                join_date=timezone.now().date(),
            )
            request.session['user_id'] = user.user_id
            return redirect('main')

    return render(request, 'login.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'active_tab': active_tab,
    })