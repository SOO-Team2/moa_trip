from django.shortcuts import render, redirect
from django.core.paginator import Paginator
#from .models import Region, TouristSpot, Users

def main(request):
    return render(request, 'main.html')

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
    {
        'id': 1, 'name': '관광지 A', 'address': '지역명', 'fee': 0,
        'rating': 4.6, 'review_count': 212, 'pet_allowed': True,
        'image': None, 'region_code': 'jeju',
    },
    {
        'id': 2, 'name': '관광지 B', 'address': '지역명', 'fee': 5000,
        'rating': 4.8, 'review_count': 1043, 'pet_allowed': False,
        'image': None, 'region_code': 'jeju',
    },
    {
        'id': 3, 'name': '관광지 C', 'address': '지역명', 'fee': 0,
        'rating': 4.7, 'review_count': 486, 'pet_allowed': True,
        'image': None, 'region_code': 'jeju',
    },
    {
        'id': 4, 'name': '관광지 D', 'address': '지역명', 'fee': 0,
        'rating': 4.4, 'review_count': 298, 'pet_allowed': True,
        'image': None, 'region_code': 'jeju',
    },
]

def explore(request):
    region = request.GET.get('region', 'jeju')
    page_number = request.GET.get('page', 1)

    # ===== API/DB 연동 전: 더미 데이터 사용 =====
    valid_codes = [r['code'] for r in DUMMY_REGIONS]
    if region not in valid_codes:
        region = 'jeju'

    spots = [s for s in DUMMY_SPOTS if s['region_code'] == region]

    # ===== 나중에 이 두 줄을 아래 실제 쿼리로 교체 =====
    # regions_qs = Region.objects.all()
    # spots_qs = TouristSpot.objects.filter(region__code=region)

    # all_regions = Region.objects.all()
    # if not all_regions.filter(code=region).exists():
    #     region = 'jeju'

    # spots = TouristSpot.objects.filter(region__code=region)

    paginator = Paginator(spots, 12)
    page_obj = paginator.get_page(page_number)

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