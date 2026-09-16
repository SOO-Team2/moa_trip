from datetime import datetime
from django.shortcuts import render
from .utils import fetch_public_data 

def main(request):
    # 한국관광공사 국문 관광정보 서비스(KorService2) 지역기반 목록 엔드포인트
    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    
    extra_params = {
        "_type": "json",    
        "MobileOS": "ETC",    
        "MobileApp": "MoaTrip", 
        "areaCode": "39",       
        "numOfRows": 6,         
    }
    
    tour_raw = fetch_public_data(tour_url, extra_params=extra_params)
    
    tour_items = []
    if tour_raw:
        items_container = tour_raw.get('response', {}).get('body', {}).get('items', {})
        if items_container:
            tour_items = items_container.get('item', [])

    context = {
        "tour_items": tour_items,
    }
    return render(request, 'main.html', context)

def explore(request):
    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    
    # 기본 제주도 목록 조회, 4개 노출
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "areaCode": "39",
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
    return render(request, 'detail.html')

def planner(request):
    selected_region = request.GET.get('region', 'jeju')
    
    # 포맷터 충돌 방지용 지역 목록 구성
    regions = [
        {"code": "jeju", "name": "제주도", "is_selected": (selected_region == "jeju")},
        {"code": "seoul", "name": "서울", "is_selected": (selected_region == "seoul")},
        {"code": "busan", "name": "부산", "is_selected": (selected_region == "busan")},
        {"code": "gangwon", "name": "강원도", "is_selected": (selected_region == "gangwon")},
        {"code": "gyeongju", "name": "경주", "is_selected": (selected_region == "gyeongju")},
    ]

    region_code_map = {
        'jeju': '39',
        'seoul': '11',
        'gangwon': '51',
        'gyeongju': '35',
        'busan': '21',
    }
    target_code = region_code_map.get(selected_region, '39')

    pet_url = "http://apis.data.go.kr/B551011/KorPetTourService2/areaBasedList2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "lDongRegnCd": target_code,
        "numOfRows": 4,
        "arrange": "O",
    }
    
    pet_raw = fetch_public_data(pet_url, extra_params=extra_params)
    
    plan_spots = []
    if pet_raw:
        items_container = pet_raw.get('response', {}).get('body', {}).get('items', {})
        if items_container:
            plan_spots = items_container.get('item', [])

    time_slots = ["오전 09:30", "오후 12:00", "오후 02:30", "오후 05:30"]
    timeline_items = []
    for idx, spot in enumerate(plan_spots):
        timeline_items.append({
            "time": time_slots[idx] if idx < len(time_slots) else "시간 미정",
            "title": spot.get("title", "추천 장소"),
            "addr": spot.get("addr1", "주소 정보 없음"),
            "contentid": spot.get("contentid", "")
        })

    context = {
        "regions": regions,
        "selected_region": selected_region,
        "timeline_items": timeline_items,
        "spot_count": len(timeline_items),
    }
    return render(request, 'planner.html', context)

def mypage(request):
    # 1. 사용자가 즐겨찾기한 관광지 목록 조회 (기본 5개)
    tour_url = "http://apis.data.go.kr/B551011/KorPetTourService2/areaBasedList2"
    extra_params = {
        "_type": "json",
        "MobileOS": "ETC",
        "MobileApp": "MoaTrip",
        "lDongRegnCd": "39",  # 제주 기준
        "numOfRows": 5,
        "arrange": "O",
    }
    
    tour_raw = fetch_public_data(tour_url, extra_params=extra_params)
    bookmarks = []
    if tour_raw:
        items_container = tour_raw.get('response', {}).get('body', {}).get('items', {})
        if items_container:
            bookmarks = items_container.get('item', [])

    # 2. 사용자 프로필 및 통계 데이터 구성
    user_info = {
        "name": "최주원",
        "user_id": "U-10428",
        "grade": "일반 회원",
        "join_date": "2026.03",
        "bookmark_count": len(bookmarks),
        "review_count": 7,
        "itinerary_count": 3,
    }

    # 3. 저장된 여행 일정 데이터
    saved_itineraries = [
        {"title": "제주도 · 반려견 동반 1일", "date": "2026.09.12 (토)", "spot_cnt": 4},
        {"title": "속초 2일 코스", "date": "2026.10.03", "spot_cnt": 6},
        {"title": "여수 야경 코스", "date": "임시 저장", "spot_cnt": 2},
    ]

    context = {
        "user": user_info,
        "bookmarks": bookmarks,
        "saved_itineraries": saved_itineraries,
    }
    return render(request, 'mypage.html', context)

def login(request):
    return render(request, 'login.html')

def admin(request):
    return render(request, 'admin.html')