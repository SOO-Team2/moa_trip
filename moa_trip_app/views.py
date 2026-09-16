from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Avg, Count
from .models import TouristSpot, Region, Users, Itinerary
from .utils import fetch_public_data

# ==============================================================================
# 1. 메인 (공공데이터 추천 관광지 노출)
# ==============================================================================
def main(request):
    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "contentTypeId": "12",
        "numOfRows": 8,
        "arrange": "O",
    }
    tour_raw = fetch_public_data(tour_url, extra_params=extra_params)
    tour_items = []
    if tour_raw and isinstance(tour_raw, dict):
        body = tour_raw.get('response', {}).get('body', {})
        items_box = body.get('items') if isinstance(body, dict) else None
        if isinstance(items_box, dict):
            res_items = items_box.get('item', [])
            tour_items = res_items if isinstance(res_items, list) else [res_items]

    context = {
        "tour_items": tour_items,
    }
    return render(request, 'main.html', context)


# ==============================================================================
# 2. 관광지 탐색 (DB 필터링 기반 + fallback API 지원)
# ==============================================================================
# ===== explore(관광지 탐색) =====
def explore(request):
    selected_region = request.GET.get('region', '39')  # 기본 제주(39)
    selected_rating = request.GET.get('min_rating', '4.5')
    selected_sort = request.GET.get('sort', 'rating')

    # 한국관광공사 공공데이터 API 호출
    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "contentTypeId": "12",  # 관광지
        "numOfRows": 12,        # 12개 출력
        "arrange": "O",         # 사진 있는 곳 우선
    }

    # 전국('all')이 아니면 지역 코드 적용
    if selected_region and selected_region != 'all':
        extra_params["areaCode"] = selected_region

    tour_raw = fetch_public_data(tour_url, extra_params=extra_params)
    
    spots = []
    if tour_raw and isinstance(tour_raw, dict):
        body = tour_raw.get('response', {}).get('body', {})
        items_box = body.get('items') if isinstance(body, dict) else None
        if isinstance(items_box, dict):
            res_items = items_box.get('item', [])
            spots = res_items if isinstance(res_items, list) else [res_items]

    # 평점/후기순 정렬 시뮬레이션 (API 목록 역순 등)
    if selected_sort == 'review':
        spots = list(reversed(spots))

    context = {
        'spots': spots,
        'selected_region': selected_region,
        'selected_rating': selected_rating,
        'selected_sort': selected_sort,
    }
    return render(request, 'explore.html', context)


# ==============================================================================
# 3. 상세 페이지 (관광공사 정보 + 기상청 중기 날씨)
# ==============================================================================
def detail(request):
    content_id = request.GET.get('contentid', '126508')

    # 관광공사 공통 정보
    detail_url = "http://apis.data.go.kr/B551011/KorService2/detailCommon2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "contentId": content_id,
        "defaultYN": "Y",
        "firstImageYN": "Y",
        "areacodeYN": "Y",
        "addrinfoYN": "Y",
        "overviewYN": "Y",
    }
    raw_common = fetch_public_data(detail_url, extra_params=extra_params)

    spot = {}
    area_code = "39"
    if raw_common and isinstance(raw_common, dict):
        body = raw_common.get('response', {}).get('body', {})
        items_box = body.get('items') if isinstance(body, dict) else None
        if isinstance(items_box, dict):
            items = items_box.get('item', [])
            if items:
                spot = items[0] if isinstance(items, list) else items
                area_code = str(spot.get('areacode', '39'))

    # 반려동물 동반 정보
    pet_url = "http://apis.data.go.kr/B551011/KorPetTourService2/detailPetTour2"
    pet_extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "contentId": content_id,
    }
    raw_pet = fetch_public_data(pet_url, extra_params=pet_extra_params)
    pet = {}
    if raw_pet and isinstance(raw_pet, dict):
        body = raw_pet.get('response', {}).get('body', {})
        items_box = body.get('items') if isinstance(body, dict) else None
        if isinstance(items_box, dict):
            pet_items = items_box.get('item', [])
            if pet_items:
                pet = pet_items[0] if isinstance(pet_items, list) else pet_items

    # 기상청 권역 매핑
    land_reg_map = {
        "39": "11G00000", "11": "11B00000", "31": "11B00000",
        "51": "11D10000", "21": "11H20000", "35": "11H10000", "38": "11F20000"
    }
    temp_reg_map = {
        "39": "11G00201", "11": "11B10101", "31": "11B20601",
        "51": "11D10301", "21": "11H20201", "35": "11H10201", "38": "11F20501"
    }

    reg_land = land_reg_map.get(area_code, "11G00000")
    reg_temp = temp_reg_map.get(area_code, "11G00201")

    now = datetime.now()
    tm_fc = (now - timedelta(days=1)).strftime("%Y%m%d") + "1800" if now.hour < 6 else now.strftime("%Y%m%d") + "0600"

    raw_land = fetch_public_data(
        "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst",
        extra_params={"regId": reg_land, "tmFc": tm_fc}
    )
    raw_temp = fetch_public_data(
        "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa",
        extra_params={"regId": reg_temp, "tmFc": tm_fc}
    )

    land_data, temp_data = {}, {}
    if raw_land and isinstance(raw_land, dict):
        body = raw_land.get('response', {}).get('body', {})
        items_box = body.get('items') if isinstance(body, dict) else None
        if isinstance(items_box, dict):
            l_item = items_box.get('item', [])
            land_data = l_item[0] if isinstance(l_item, list) else (l_item or {})

    if raw_temp and isinstance(raw_temp, dict):
        body = raw_temp.get('response', {}).get('body', {})
        items_box = body.get('items') if isinstance(body, dict) else None
        if isinstance(items_box, dict):
            t_item = items_box.get('item', [])
            temp_data = t_item[0] if isinstance(t_item, list) else (t_item or {})

    # 주간 예보 가공
    days_kr = ["월", "화", "수", "목", "금", "토", "일"]
    weekly_forecast = []
    icon_map = {"맑음": "☀️", "구름많음": "⛅", "흐림": "☁️", "비": "🌧️", "눈": "❄️"}

    for i in range(7):
        target_date = now + timedelta(days=i)
        date_label = f"오늘 {target_date.month}/{target_date.day}" if i == 0 else f"{days_kr[target_date.weekday()]} {target_date.month}/{target_date.day}"
        day_idx = min(max(i + 1, 3), 7)
        wf = land_data.get(f"wf{day_idx}Pm", land_data.get(f"wf{day_idx}", "맑음"))
        rn_st = land_data.get(f"rnSt{day_idx}Pm", land_data.get(f"rnSt{day_idx}", 10))
        ta_max = temp_data.get(f"taMax{day_idx}", 24)
        icon = next((v for k, v in icon_map.items() if k in wf), "☀️")

        weekly_forecast.append({
            "date": date_label,
            "icon": icon,
            "desc": wf,
            "temp": f"{ta_max}°",
            "rain_prob": rn_st,
        })

    today_weather = weekly_forecast[0]

    context = {
        "spot": spot,
        "pet": pet,
        "weekly_forecast": weekly_forecast,
        "today_weather": today_weather,
    }
    return render(request, 'detail.html', context)


# ==============================================================================
# 4. 여행 일정 플래너
# ==============================================================================
def planner(request):
    selected_region = request.GET.get('region', 'all')
    regions = [
        {"code": "all", "name": "전국", "is_selected": (selected_region == "all")},
        {"code": "jeju", "name": "제주도", "is_selected": (selected_region == "jeju")},
        {"code": "seoul", "name": "서울", "is_selected": (selected_region == "seoul")},
        {"code": "gangwon", "name": "강원도", "is_selected": (selected_region == "gangwon")},
        {"code": "busan", "name": "부산", "is_selected": (selected_region == "busan")},
        {"code": "gyeongju", "name": "경주", "is_selected": (selected_region == "gyeongju")},
    ]
    region_code_map = {
        'jeju': '39', 'seoul': '11', 'gangwon': '51', 'gyeongju': '35', 'busan': '21',
    }

    pet_url = "http://apis.data.go.kr/B551011/KorPetTourService2/areaBasedList2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "contentTypeId": "12",
        "numOfRows": 4,
        "arrange": "O",
    }
    if selected_region in region_code_map:
        extra_params["lDongRegnCd"] = region_code_map[selected_region]

    pet_raw = fetch_public_data(pet_url, extra_params=extra_params)
    plan_spots = []
    if pet_raw and isinstance(pet_raw, dict):
        body = pet_raw.get('response', {}).get('body', {})
        items_box = body.get('items') if isinstance(body, dict) else None
        if isinstance(items_box, dict):
            res_items = items_box.get('item', [])
            plan_spots = res_items if isinstance(res_items, list) else [res_items]

    time_slots = ["오전 09:30", "오후 12:00", "오후 02:30", "오후 05:30"]
    timeline_items = []
    for idx, s in enumerate(plan_spots):
        timeline_items.append({
            "time": time_slots[idx] if idx < len(time_slots) else "시간 미정",
            "title": s.get("title", "추천 장소"),
            "addr": s.get("addr1", "주소 정보 없음"),
            "contentid": s.get("contentid", ""),
            "image": s.get("firstimage", ""),
        })

    context = {
        "regions": regions,
        "selected_region": selected_region,
        "timeline_items": timeline_items,
        "spot_count": len(timeline_items),
    }
    return render(request, 'planner.html', context)


# ==============================================================================
# 5. 마이페이지 (회원 세션/DB 연동 + 북마크 API 연동)
# ==============================================================================
def mypage(request):
    user_id = request.session.get('user_id', None)
    if not user_id:
        return HttpResponse('<script>alert("로그인이 필요한 페이지입니다."); location.href="../login/";</script>')

    # 회원 정보 및 저장된 일정 조회
    try:
        user = Users.objects.get(user_id=user_id)
    except Users.DoesNotExist:
        request.session.flush()
        return redirect('login')

    saved_itineraries = Itinerary.objects.filter(user_id=user_id)

    # 북마크 관광지 조회 (공공데이터)
    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "contentTypeId": "12",
        "numOfRows": 4,
        "arrange": "O",
    }
    tour_raw = fetch_public_data(tour_url, extra_params=extra_params)
    bookmarks = []
    if tour_raw and isinstance(tour_raw, dict):
        body = tour_raw.get('response', {}).get('body', {})
        items_box = body.get('items') if isinstance(body, dict) else None
        if isinstance(items_box, dict):
            res_items = items_box.get('item', [])
            bookmarks = res_items if isinstance(res_items, list) else [res_items]

    context = {
        'user': user,
        'bookmarks': bookmarks,
        'saved_itineraries': saved_itineraries,
    }
    return render(request, 'mypage.html', context)


# ==============================================================================
# 6. 계정 및 인증 (로그인/로그아웃/회원가입/관리자)
# ==============================================================================
def login(request):
    return render(request, 'login.html')

def login_ok(request):
    user_id = request.POST.get('user_id', None)
    pw = request.POST.get('pw', None)

    try:
        user = Users.objects.get(user_id=user_id)
    except Users.DoesNotExist:
        user = None

    if user is not None:
        if check_password(pw, user.pw):
            request.session['user_id'] = user.user_id
            return redirect('../../')
        else:
            result = 1  # 비밀번호 불일치
    else:
        result = 0      # 사용자 미존재

    return render(request, 'login_ok.html', {'result': result})

def logout(request):
    if 'user_id' in request.session:
        del request.session['user_id']
    request.session.flush()
    return redirect('main')

def signup(request):
    if request.method != 'POST':
        return redirect('login')

    user_id = request.POST.get('user_id', None)
    pw = request.POST.get('pw', None)
    nickname = request.POST.get('nickname', None)
    email = request.POST.get('email', None)

    if not user_id or not pw or not nickname or not email:
        result = 2  # 입력값 누락
    elif '@' not in email:
        result = 3  # 이메일 포맷 오류
    else:
        try:
            user = Users.objects.get(user_id=user_id)
        except Users.DoesNotExist:
            user = None

        if user is not None:
            result = 1  # 아이디 중복
        else:
            Users.objects.create(
                user_id=user_id,
                pw=make_password(pw),
                nickname=nickname,
                email=email,
            )
            result = 0

    return render(request, 'signup_ok.html', {'result': result})

def admin(request):
    return render(request, 'admin.html')