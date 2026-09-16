from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Avg, Count
from .models import TouristSpot, Region, Users, Itinerary
from .utils import fetch_public_data

# ==============================================================================
# 1. 메인 (추천 관광지 8개)
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

    return render(request, 'main.html', {"tour_items": tour_items})


# ==============================================================================
# 2. 관광지 탐색 (explore 에러 해결 핵심)
# ==============================================================================
def explore(request):
    selected_region = request.GET.get('region', '39')
    selected_rating = request.GET.get('min_rating', '4.5')
    selected_sort = request.GET.get('sort', 'rating')

    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "contentTypeId": "12",
        "numOfRows": 12,
        "arrange": "O",
    }
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
# 3. 상세 페이지 (관광지 상세 + 반려동물 정보 + 기상청 중기예보)
# ==============================================================================
def detail(request):
    content_id = request.GET.get('contentid', '').strip()
    req_areacode = request.GET.get('areacode', '').strip()

    def extract_items(raw_json):
        if not raw_json or not isinstance(raw_json, dict):
            return []
        body = raw_json.get('response', {}).get('body', {})
        if not isinstance(body, dict):
            return []
        items_box = body.get('items')
        if not items_box or not isinstance(items_box, dict):
            return []
        item = items_box.get('item', [])
        return item if isinstance(item, list) else ([item] if item else [])

    spot = {}
    area_code = req_areacode if req_areacode else "39"

    # 1. 한국관광공사 공통 상세조회
    params = {
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
    raw_detail = fetch_public_data("http://apis.data.go.kr/B551011/KorService2/detailCommon1", extra_params=params)
    items = extract_items(raw_detail)
    if items:
        spot = items[0]
        area_code = str(spot.get('areacode', area_code))
    else:
        raw_c2 = fetch_public_data("http://apis.data.go.kr/B551011/KorService2/detailCommon2", extra_params=params)
        items_c2 = extract_items(raw_c2)
        if items_c2:
            spot = items_c2[0]
            area_code = str(spot.get('areacode', area_code))

    # 2. 목록 API에서 매칭 보완
    if not spot or not spot.get('title'):
        list_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
        search_areas = [area_code, "32", "39", "38", "35", "11", "21"]
        for ac in dict.fromkeys(search_areas):
            raw_list = fetch_public_data(list_url, extra_params={
                "_type": "json", "MobileOS": "ETC", "MobileApp": "MoaTrip",
                "contentTypeId": "12", "numOfRows": 60, "arrange": "O", "areaCode": ac
            })
            list_items = extract_items(raw_list)
            matched = next((item for item in list_items if str(item.get('contentid')) == str(content_id)), None)
            if matched:
                spot = matched
                area_code = ac
                break

    # 3. 권역 명칭 매핑 (데이터 부재 시 지역 맞춤 문구 생성용)
    area_name_map = {
        "32": "강원", "51": "강원", "39": "제주", "11": "서울",
        "31": "경기", "21": "부산", "35": "경북", "38": "전남"
    }
    region_name = area_name_map.get(str(area_code), "해당 지역")

    # 4. 반려동물 동반 상세 정보 조회
    pet = {}
    if content_id:
        pet_url = "http://apis.data.go.kr/B551011/KorPetTourService2/detailPetTour2"
        raw_pet = fetch_public_data(pet_url, extra_params={
            "_type": "json", "MobileOS": "ETC", "MobileApp": "MoaTrip", "contentId": content_id
        })
        pet_items = extract_items(raw_pet)
        if pet_items:
            pet = pet_items[0]

    # 5. 상세 안내 테이블 정보 조립 (API 실제 데이터 우선 -> 누락 시 지역별 안내 조합)
    overview_text = spot.get('overview', '').strip()
    if not overview_text:
        overview_text = f"{region_name}의 청정한 자연 풍경과 여유로운 산책로가 조성된 대표적인 힐링 여행지입니다."

    detail_info = {
        "fee": "무료 (시설별 일부 체험 프로그램 상이)",
        "parking": pet.get('parking') or pet.get('parkinfo') or f"{region_name} 관광지 전용 및 인근 공영주차장 이용 가능",
        "pet_rule": pet.get('acmpyNeedMtr') or pet.get('etcAcmpyInfo') or "동반 가능 (목줄 착용 및 배변봉투 필수 지참)",
        "pet_size": pet.get('relaAcmdCode') or pet.get('acmpyPsblCpam') or "소형견 / 중형견 동반 가능 (대형견 사전 확인 권장)",
        "facilities": pet.get('relaPosesFclty') or pet.get('relaPurcPrdlst') or f"{region_name} 반려견 산책 코스 및 야외 쉼터 구비",
        "overview": overview_text,
    }

    # 6. 기상청 날씨 매핑 (강원도 32 완벽 대응)
    land_reg_map = {
        "32": "11D10000", "51": "11D10000", "39": "11G00000", "11": "11B00000",
        "31": "11B00000", "21": "11H20000", "35": "11H10000", "38": "11F20000"
    }
    temp_reg_map = {
        "32": "11D10301", "51": "11D10301", "39": "11G00201", "11": "11B10101",
        "31": "11B20601", "21": "11H20201", "35": "11H10701", "38": "11F20501"
    }

    reg_land = land_reg_map.get(area_code, "11D10000" if area_code in ["32", "51"] else "11G00000")
    reg_temp = temp_reg_map.get(area_code, "11D10301" if area_code in ["32", "51"] else "11G00201")

    now = datetime.now()
    tm_fc = (now - timedelta(days=1)).strftime("%Y%m%d") + "1800" if now.hour < 6 else now.strftime("%Y%m%d") + "0600"

    raw_land = fetch_public_data("http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst", extra_params={"regId": reg_land, "tmFc": tm_fc})
    raw_temp = fetch_public_data("http://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa", extra_params={"regId": reg_temp, "tmFc": tm_fc})

    land_items = extract_items(raw_land)
    land_data = land_items[0] if land_items else {}

    temp_items = extract_items(raw_temp)
    temp_data = temp_items[0] if temp_items else {}

    # 7. 주간 날씨 가공
    days_kr = ["월", "화", "수", "목", "금", "토", "일"]
    weekly_forecast = []
    icon_map = {"맑음": "☀️", "구름많음": "⛅", "흐림": "☁️", "비": "🌧️", "눈": "❄️"}

    for i in range(7):
        target_date = now + timedelta(days=i)
        date_label = f"오늘 {target_date.month}/{target_date.day}" if i == 0 else f"{days_kr[target_date.weekday()]} {target_date.month}/{target_date.day}"
        day_idx = min(max(i + 1, 3), 7)
        wf = land_data.get(f"wf{day_idx}Pm", land_data.get(f"wf{day_idx}", "맑음"))
        rn_st = land_data.get(f"rnSt{day_idx}Pm", land_data.get(f"rnSt{day_idx}", 10))
        ta_max = temp_data.get(f"taMax{day_idx}", 22 + (i % 4))
        icon = next((v for k, v in icon_map.items() if k in wf), "☀️")

        weekly_forecast.append({
            "date": date_label,
            "icon": icon,
            "desc": wf,
            "temp": f"{ta_max}°",
            "rain_prob": rn_st,
        })

    context = {
        "spot": spot,
        "detail_info": detail_info,
        "weekly_forecast": weekly_forecast,
        "today_weather": weekly_forecast[0],
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
    region_code_map = {'jeju': '39', 'seoul': '11', 'gangwon': '51', 'gyeongju': '35', 'busan': '21'}

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
# 5. 마이페이지
# ==============================================================================
def mypage(request):
    user_id = request.session.get('user_id', None)
    if not user_id:
        return HttpResponse('<script>alert("로그인이 필요한 페이지입니다."); location.href="../login/";</script>')

    try:
        user = Users.objects.get(user_id=user_id)
    except Users.DoesNotExist:
        request.session.flush()
        return redirect('login')

    saved_itineraries = Itinerary.objects.filter(user_id=user_id)

    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    tour_raw = fetch_public_data(tour_url, extra_params={
        "_type": "json", "MobileOS": "ETC", "MobileApp": "MoaTrip", "contentTypeId": "12", "numOfRows": 4, "arrange": "O"
    })
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
# 6. 인증 (로그인/로그아웃/회원가입/관리자)
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

    if user and check_password(pw, user.pw):
        request.session['user_id'] = user.user_id
        return redirect('../../')
    return render(request, 'login_ok.html', {'result': 1 if user else 0})

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
        result = 2
    elif '@' not in email:
        result = 3
    else:
        if Users.objects.filter(user_id=user_id).exists():
            result = 1
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