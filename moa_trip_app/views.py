from datetime import datetime, timedelta
from django.shortcuts import render
from .utils import fetch_public_data 

#===== main =====
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
    if tour_raw:
        # 단일 건이거나 배열일 때 모두 처리
        items_container = tour_raw.get('response', {}).get('body', {}).get('items', {})
        if items_container:
            res_items = items_container.get('item', [])
            tour_items = res_items if isinstance(res_items, list) else [res_items]

    context = {
        "tour_items": tour_items,
    }
    return render(request, 'main.html', context)

#===== explore(관광지) =====
def explore(request):
    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    
    # 기본 제주도 목록 조회, 4개 노출
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "areaCode": "39",
        "contentTypeId": "12",
        "numOfRows": 4,
    }
    
    tour_raw = fetch_public_data(tour_url, extra_params=extra_params)
    
    spots = []
    if tour_raw:
        items_container = tour_raw.get('response', {}).get('body', {}).get('items', {})
        if items_container:
            spots = items_container.get('item', [])

    return render(request, 'explore.html', {'spots': spots})

def detail(request):
    content_id = request.GET.get('contentid', '126508')  # 기본값 제주 관광지

    # 1. 한국관광공사 공통 정보 (기본/주소/개요/이미지)
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

    # 2. 한국관광공사 반려동물 정보 (규정/편의시설)
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

    # 3. 기상청 중기예보 코드 매핑
    land_reg_map = {
        "39": "11G00000",  # 제주
        "11": "11B00000",  # 서울/수도권
        "31": "11B00000",  # 경기
        "51": "11D10000",  # 강원
        "21": "11H20000",  # 부산/경남
        "35": "11H10000",  # 대구/경북
        "38": "11F20000",  # 광주/전남
    }
    temp_reg_map = {
        "39": "11G00201",   # 제주
        "11": "11B10101",  # 서울
        "31": "11B20601",  # 수원
        "51": "11D10301",  # 춘천
        "21": "11H20201",  # 부산
        "35": "11H10201",  # 대구
        "38": "11F20501",  # 광주
    }

    reg_land = land_reg_map.get(area_code, "11G00000")
    reg_temp = temp_reg_map.get(area_code, "11G0201")

    # 기상청 발표시각 생성 (당일 06시 발표 기준)
    now = datetime.now()
    if now.hour < 6:
        tm_fc = (now - timedelta(days=1)).strftime("%Y%m%d") + "1800"
    else:
        tm_fc = now.strftime("%Y%m%d") + "0600"

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

    # 4. 7일 주간 예보 조립
    days_kr = ["월", "화", "수", "목", "금", "토", "일"]
    weekly_forecast = []
    icon_map = {"맑음": "☀️", "구름많음": "⛅", "흐림": "☁️", "비": "🌧️", "눈": "❄️"}

    for i in range(7):
        target_date = now + timedelta(days=i)
        if i == 0:
            date_label = f"오늘 {target_date.month}/{target_date.day}"
        else:
            date_label = f"{days_kr[target_date.weekday()]} {target_date.month}/{target_date.day}"

        # 중기예보(3일차 이상) 데이터 매핑
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

#===== planner (여행일지) =====
def planner(request):
    # 기본값을 'all'(전국)로 설정
    selected_region = request.GET.get('region', 'all')
    
    # 지역 목록에 '전국' 옵션 추가
    regions = [
        {"code": "all", "name": "전국", "is_selected": (selected_region == "all")},
        {"code": "jeju", "name": "제주도", "is_selected": (selected_region == "jeju")},
        {"code": "seoul", "name": "서울", "is_selected": (selected_region == "seoul")},
        {"code": "gangwon", "name": "강원도", "is_selected": (selected_region == "gangwon")},
        {"code": "busan", "name": "부산", "is_selected": (selected_region == "busan")},
        {"code": "gyeongju", "name": "경주", "is_selected": (selected_region == "gyeongju")},
    ]

    region_code_map = {
        'jeju': '39',
        'seoul': '11',
        'gangwon': '51',
        'gyeongju': '35',
        'busan': '21',
    }

    pet_url = "http://apis.data.go.kr/B551011/KorPetTourService2/areaBasedList2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "contentTypeId": "12",  # 자연 및 순수 관광지만 필터링 (식당 제외)
        "numOfRows": 4,
        "arrange": "O",         # 이미지 있는 관광지 우선
    }
    
    # 'all'(전국)이 아닐 때만 특정 지역 코드 파라미터 추가
    if selected_region in region_code_map:
        extra_params["lDongRegnCd"] = region_code_map[selected_region]
    
    pet_raw = fetch_public_data(pet_url, extra_params=extra_params)
    
    plan_spots = []
    if pet_raw:
        items_container = pet_raw.get('response', {}).get('body', {}).get('items', {})
        if items_container:
            res_items = items_container.get('item', [])
            plan_spots = res_items if isinstance(res_items, list) else [res_items]

    time_slots = ["오전 09:30", "오후 12:00", "오후 02:30", "오후 05:30"]
    timeline_items = []
    for idx, spot in enumerate(plan_spots):
        timeline_items.append({
            "time": time_slots[idx] if idx < len(time_slots) else "시간 미정",
            "title": spot.get("title", "추천 장소"),
            "addr": spot.get("addr1", "주소 정보 없음"),
            "contentid": spot.get("contentid", ""),
            "image": spot.get("firstimage", ""),
        })

    context = {
        "regions": regions,
        "selected_region": selected_region,
        "timeline_items": timeline_items,
        "spot_count": len(timeline_items),
    }
    return render(request, 'planner.html', context)

#===== mypage =====
def mypage(request):
    # 1. 템플릿의 user.* 객체 구조에 맞춘 프로필 데이터
    user_data = {
        "grade": "골드 트래블러",
        "name": request.user.username if request.user.is_authenticated else "모아여행러",
        "user_id": request.user.email if (request.user.is_authenticated and request.user.email) else "traveler@moatrip.kr",
        "join_date": "2026.03.15",
        "bookmark_count": 4,
        "review_count": 2,
        "itinerary_count": 2,
    }

    # 2. 우측 사이드바: 저장한 여행 일정 목록 (saved_itineraries)
    saved_itineraries = [
        {
            "id": 1,
            "title": "제주 가을 댕댕이 힐링 투어",
            "date": "2026.09.20",
            "spot_cnt": 4,
        },
        {
            "id": 2,
            "title": "강릉 안목해변 바다산책 코스",
            "date": "2026.10.03",
            "spot_cnt": 3,
        }
    ]

    # 3. 중앙 즐겨찾기: 관광공사 API 연동 (자연/관광지 명소 추출)
    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "contentTypeId": "12",  # 자연 및 관광지
        "numOfRows": 5,         # 즐겨찾기 표시 개수
        "arrange": "O",         # 사진 있는 곳 우선
    }
    
    tour_raw = fetch_public_data(tour_url, extra_params=extra_params)
    bookmarks = []
    if tour_raw and isinstance(tour_raw, dict):
        body = tour_raw.get('response', {}).get('body', {})
        items_box = body.get('items') if isinstance(body, dict) else None
        if isinstance(items_box, dict):
            res_items = items_box.get('item', [])
            bookmarks = res_items if isinstance(res_items, list) else [res_items]

    # 즐겨찾기 실제 건수로 통계 동기화
    if bookmarks:
        user_data["bookmark_count"] = len(bookmarks)

    context = {
        "user": user_data,
        "bookmarks": bookmarks,
        "saved_itineraries": saved_itineraries,
    }
    return render(request, 'mypage.html', context)

def login(request):
    return render(request, 'login.html')

def admin(request):
    return render(request, 'admin.html')