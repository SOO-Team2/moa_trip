import uuid
from django.db.models import Avg
from django.http import JsonResponse
from django.utils import timezone
import math
import random
import re
from django.conf import settings
from django.shortcuts import render
from ..models import Favorite, Review, TouristSpot, Users
from ..utils import fetch_public_data, api_items, api_totalcount, get_weather, to_grid
from ..constants import REGION_FILTERS, get_region


# ==============================================================================
# 1. 메인 (랜덤 추천 관광지 8개 + 반려동물 동반 가능 관광지 랜덤 3개 조회)
# ==============================================================================
def main(request):
    # 1. 랜덤 추천 관광지 8개
    tour_url = "http://apis.data.go.kr/B551011/KorService2/areaBasedList2"
    extra_params = {
        "contentTypeId": "12",
        "numOfRows": 30,
        "pageNo" : random.randint(1, 10),
        "arrange": "Q",
    }
    tour_raw = fetch_public_data(tour_url, extra_params=extra_params)
    all_tour_items = api_items(tour_raw)
    tour_items = random.sample(all_tour_items, min(len(all_tour_items), 8))
    
    # 2. 반려동물 동반 가능 관광지 랜덤 조회
    pet_url = "http://apis.data.go.kr/B551011/KorPetTourService2/areaBasedList2"
    pet_params ={
        "contentTypeId": "12",
        "numOfRows" : 30,
        "pageNo" : random.randint(1, 5),
        "arrange" : "Q",
    }
    pet_raw = fetch_public_data(pet_url, extra_params=pet_params)
    all_pet_items = api_items(pet_raw)

    pet_items = random.sample(all_pet_items, min(len(all_pet_items), 3))

    return render(request, 'main.html', {"tour_items": tour_items, "pet_items": pet_items,})

# ==============================================================================
# 2. 관광지 (explore)
# ==============================================================================
def explore(request):
    selected_region = request.GET.get('region', 'all')
    selected_rating = request.GET.get('min_rating')
    selected_pet = request.GET.get('pet_allowed')
    selected_sort = request.GET.get('sort', 'rating')
    try:
        cur_page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        cur_page = 1

    num_of_rows = 10

    #API 호출 기본 정보
    service_name = "KorPetTourService2" if selected_pet else "KorService2"
    tour_url = f"http://apis.data.go.kr/B551011/{service_name}/areaBasedList2"

    extra_params = {
        "contentTypeId": "12",
        "numOfRows": num_of_rows,
        "pageNo": cur_page,
        "arrange": "O",
    }

    if selected_region and selected_region != 'all':
        extra_params["areaCode"] = selected_region

    tour_raw = fetch_public_data(tour_url, extra_params=extra_params)
    spots = api_items(tour_raw)
    total_count = api_totalcount(tour_raw)

    if selected_sort == 'review':
        spots = list(reversed(spots))

    # 반려동물 동반 가능 필터: KorPetTourService2 API에서 조회하므로 모두 True
    is_pet = bool(selected_pet)
    for spot in spots:
        spot['is_pet_allowed'] = is_pet

    user_id = request.session.get('user_id')
    favorited_spot_codes = set(
        Favorite.objects.filter(user_id=user_id).values_list('spot_id', flat=True)
    ) if user_id else set()

    # 페이징 계산 (5개 페이지 블록 단위)
    total_pages = math.ceil(total_count / num_of_rows) if total_count > 0 else 1
    page_block = 5
    start_page = ((cur_page - 1) // page_block) * page_block + 1
    end_page = min(total_pages, start_page + page_block - 1)
    has_prev = start_page > 1
    has_next = end_page < total_pages
    prev_page = start_page - 1
    next_page = end_page + 1
    page_range = range(start_page, end_page + 1)

    # 선택된 지역 이름 및 헤더 타이틀 작성
    selected_region_name = next(
        (r['name'] for r in REGION_FILTERS if r['code'] == selected_region),
        '전체'
    )
    if selected_region == 'all' or not selected_region:
        region_title = "전체 관광지"
    else:
        region_title = f"{selected_region_name} 지역 관광지"

    context = {
        'spots': spots,
        'tour_regions': REGION_FILTERS,
        'selected_region': selected_region,
        'selected_region_name': selected_region_name,
        'region_title': region_title,
        'selected_rating': selected_rating,
        'selected_pet': selected_pet,
        'selected_sort': selected_sort,
        'favorited_spot_codes': favorited_spot_codes,
        'cur_page': cur_page,
        'total_count': total_count,
        'total_pages': total_pages,
        'page_range': page_range,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': prev_page,
        'next_page': next_page,
    }
    return render(request, 'explore.html', context)


# ==============================================================================
# 3. 상세 페이지 (관광지 상세 + 반려동물 정보 + 기상청 예보)
# ==============================================================================
def detail(request):
    content_id = request.GET.get('contentid', '').strip()
    req_areacode = request.GET.get('areacode', '').strip()

    # --- 추가 (로그인 회원 및 해당 관광지 즐겨찾기 여부 조회)
    user_id = request.session.get('user_id')
    is_favorited = False
    if user_id and content_id:
        is_favorited = Favorite.objects.filter(user_id=user_id, spot_id=content_id).exists()

    # ---추가 (해당 관광지의 후기 목록 및 평점 통계 조회)
    reviews = []
    review_count = 0
    avg_rating = 0.0
    if content_id:
        reviews = Review.objects.filter(spot_id=content_id).select_related('user').order_by('-create_date')
        review_count = reviews.count()
        if review_count > 0:
            avg = reviews.aggregate(Avg('rating'))['rating__avg']
            avg_rating = round(avg, 1) if avg else 0.0

    spot = {}
    area_code = req_areacode if req_areacode and req_areacode != 'all' else "39"

    # 1. 한국관광공사 공통 상세조회 (detailCommon2 단독 호출: 타입 불문 100% 응답)
    if content_id:
        raw_detail = fetch_public_data(
            "http://apis.data.go.kr/B551011/KorService2/detailCommon2",
            extra_params={
                "contentId": str(content_id),
            }
        )
        items = api_items(raw_detail)
        if items and items[0].get('title'):
            spot = items[0]
            if spot.get('areacode'):
                area_code = str(spot.get('areacode'))

    # 3. 권역 명칭 매핑
    region_info = get_region(area_code)
    region_name = region_info["name"]

    # 4-1. 반려동물 동반 상세 정보 조회 (detailPetTour2)
    pet = {}
    if content_id:
        pet_url = "http://apis.data.go.kr/B551011/KorPetTourService2/detailPetTour2"
        raw_pet = fetch_public_data(pet_url, extra_params={
            "contentId": str(content_id),
        })
        pet_items = api_items(raw_pet)
        if pet_items:
            pet = pet_items[0]

    # 4-2. 관광지 상세 소개정보 및 반복정보 조회 (detailIntro2 & detailInfo2)
    intro = {}
    repeat_info_items = []
    if content_id:
        c_type = spot.get('contenttypeid') or spot.get('contentTypeId') or "12"
        raw_intro = fetch_public_data(
            "http://apis.data.go.kr/B551011/KorService2/detailIntro2",
            extra_params={
                "contentId": str(content_id),
                "contentTypeId": str(c_type),
            }
        )
        intro_items = api_items(raw_intro)
        if intro_items:
            intro = intro_items[0]

        # detailInfo2 (입장료, 주차요금 등 세부 반복 정보 전수 조회)
        raw_repeat_info = fetch_public_data(
            "http://apis.data.go.kr/B551011/KorService2/detailInfo2",
            extra_params={
                "contentId": str(content_id),
                "contentTypeId": str(c_type),
            }
        )
        repeat_info_items = api_items(raw_repeat_info)

    # 4-3. 관광지 추가 이미지 목록 조회 (detailImage1/detailImage2)
    images = []
    main_img = spot.get('firstimage') or ""

    if main_img:
        images.append(main_img)

    if content_id:
        img_url = "http://apis.data.go.kr/B551011/KorService2/detailImage2"
        raw_img = fetch_public_data(img_url, extra_params={
            "contentId": str(content_id), "numOfRows": 20,
        })
        img_items = api_items(raw_img)

        for it in img_items:
            u = it.get('originimgurl') or it.get('smallimageurl')
            if u and u not in images:
                # 같은 사진(동일 파일명) 중복 유입 방지
                u_name = u.split('/')[-1]
                if not any(u_name == exist.split('/')[-1] for exist in images):
                    images.append(u)

    # 3장의 사진이 반드시 서로 다르게 나오도록 보장하는 로직
    backup_pool = [
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80", # 푸른 바다/하늘
        "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=800&q=80", # 잔디/자연
        "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=800&q=80", # 풍경/산
        "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=800&q=80", # 호수/여행
        "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=800&q=80", # 로드트립
    ]

    selected_photos = []
    # 1. API에서 가져온 실제 관광지 사진 중 중복 없이 순차 수집
    for img in images:
        if img and img not in selected_photos and len(selected_photos) < 3:
            selected_photos.append(img)

    # 2. 3장이 부족한 경우 백업 이미지 풀에서 중복 없이 보충
    for b_img in backup_pool:
        if len(selected_photos) >= 3:
            break
        if b_img not in selected_photos:
            selected_photos.append(b_img)

    gallery_photos = {
        "photo1": selected_photos[0],
        "photo2": selected_photos[1],
        "photo3": selected_photos[2],
    }

    def clean_multiline_text(raw_text, max_lines=6, max_len=400):
        if not raw_text:
            return ""
        s = str(raw_text)
        s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
        s = re.sub(r'</?(?:p|div|li)[^>]*>', '\n', s, flags=re.I)
        s = re.sub(r'<[^>]+>', '', s)
        # 붙어있는 대괄호 구분 [3월~5월]... 앞에 줄바꿈
        s = re.sub(r'([^\n\s])(\[[^\]]+\])', r'\1\n\2', s)
        # 붙어있는 대시 구분 - 주말... 앞에 줄바꿈
        s = re.sub(r'([^\n\s])(-\s*[^\n]+)', r'\1\n\2', s)
        lines = [line.strip() for line in s.split('\n') if line.strip()]
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
        res = '<br>'.join(lines)
        if len(res) > max_len:
            res = res[:max_len-3] + '...'
        return res

    # 5. 상세 안내 테이블 정보 조립
    # 5-1) 입장료 (detailInfo2 반복 정보 우선 -> intro -> spot)
    raw_fee = ""
    for r_item in repeat_info_items:
        iname = (r_item.get('infoname') or '').replace(' ', '')
        itext = (r_item.get('infotext') or '').strip()
        if any(w in iname for w in ['입장료', '관람료', '이용요금', '이용료', '체험료', '요금']):
            if itext:
                raw_fee = itext
                break

    if not raw_fee:
        raw_fee = (
            intro.get('usefee') or 
            intro.get('usefeeleports') or 
            intro.get('spendtimefestival') or 
            spot.get('usefee')
        )

    if raw_fee:
        clean_check = re.sub(r'<[^>]+>', '', str(raw_fee)).strip()
        if clean_check in ['무료', '무료입장', '무료 관람', '무료관람', '없음']:
            use_fee = "무료"
        else:
            use_fee = clean_multiline_text(raw_fee, max_lines=6, max_len=350)
    else:
        use_fee = "무료"

    # 5-2) 주차 (detailInfo2 주차요금 정보 보강)
    info_parking = ""
    for r_item in repeat_info_items:
        iname = (r_item.get('infoname') or '').replace(' ', '')
        itext = (r_item.get('infotext') or '').strip()
        if '주차' in iname and itext:
            info_parking = clean_multiline_text(itext, max_lines=4, max_len=250)
            break

    raw_parking = (
        info_parking or
        pet.get('parking') or pet.get('parkinfo') or 
        intro.get('parking') or intro.get('parkinfo') or 
        spot.get('parking')
    )

    if raw_parking:
        parking_info = clean_multiline_text(raw_parking, max_lines=4, max_len=250)
    else:
        parking_info = "인근 공영주차장 이용 가능"

    # 5-3) 반려동물 규정 판별
    pet_need = (pet.get('acmpyNeedMtr') or '').strip()
    pet_etc = (pet.get('etcAcmpyInfo') or '').strip()
    pet_type = (pet.get('acmpyTypeCd') or '').strip()
    pet_cpam = (pet.get('acmpyPsblCpam') or '').strip()
    chk_pet = (intro.get('chkpet') or '').strip()

    is_pet_allowed = False
    pet_status = "unknown"
    pet_rule = ""

    if pet_need or pet_etc or pet_type or pet_cpam:
        # detailPetTour2에 등록된 반려동물 동반 관광지
        is_pet_allowed = True
        pet_status = "allowed"
        pet_rule_parts = [p for p in [pet_need, pet_etc, pet_cpam] if p]
        if pet_rule_parts:
            pet_rule = clean_multiline_text('<br>'.join(pet_rule_parts), max_lines=4, max_len=250)
        else:
            pet_rule = pet_type or "동반 가능 (목줄 착용 필수)"
    elif chk_pet:
        clean_chk = re.sub(r'<[^>]+>', '', chk_pet).strip()
        if any(keyword in clean_chk for keyword in ["불가", "금지", "안됨", "제한"]):
            is_pet_allowed = False
            pet_status = "disallowed"
            pet_rule = clean_multiline_text(clean_chk, max_lines=3, max_len=200) or "반려동물 동반 불가"
        elif any(keyword in clean_chk for keyword in ["가능", "허용", "목줄", "케이지"]):
            is_pet_allowed = True
            pet_status = "allowed"
            pet_rule = clean_multiline_text(clean_chk, max_lines=3, max_len=200) or "동반 가능 (목줄/케이지 필수)"
        else:
            pet_rule = clean_multiline_text(clean_chk, max_lines=3, max_len=200)
            is_pet_allowed = "가능" in clean_chk
            pet_status = "allowed" if is_pet_allowed else "disallowed"
    else:
        # 두 API 모두 정보가 없거나 미등록된 경우
        is_pet_allowed = False
        pet_status = "unknown"
        pet_rule = "방문 전 문의 필요"

    # 5-4) 이용 시간
    raw_time = (
        intro.get('usetime') or 
        intro.get('usetimefestival') or 
        intro.get('usetimeleports') or 
        intro.get('opentime') or 
        intro.get('opentimefood') or 
        intro.get('playtime') or 
        spot.get('usetime') or 
        spot.get('opentime')
    )
    if raw_time:
        use_time = clean_multiline_text(raw_time, max_lines=6, max_len=350)
    else:
        use_time = "상시 개방 (연중무휴)"

    # 5) 문의 전화 (전수 조사)
    raw_contact = (
        intro.get('infocenter') or
        spot.get('tel') or
        intro.get('infocentertourcourse') or
        intro.get('sponsor1tel') or
        intro.get('sponsor2tel') or
        pet.get('tel') or
        spot.get('infocenter')
    )

    if raw_contact:
        contact_tel = re.sub(r'<[^>]+>', '', str(raw_contact)).strip()
    else:
        contact_tel = region_info["tel"]

    detail_info = {
        "fee": use_fee,
        "parking": parking_info,
        "pet": pet_rule,
        "pet_rule": pet_rule,
        "is_pet_allowed": is_pet_allowed,
        "pet_status": pet_status,
        "use_time": use_time,
        "contact": contact_tel,
    }

    # 6. 날씨 데이터 조회 (단기예보 + 중기예보 조합)
    weather_info = get_weather(spot.get('mapy'), spot.get('mapx'), area_code)

    # 7. 회원 닉네임 조회
    user_id = request.session.get('user_id')
    user_obj = Users.objects.filter(user_id=user_id).first()
    user_nickname = user_obj.nickname

    context = {
        "spot": spot,
        "detail_info": detail_info,
        "weekly_forecast": weather_info["weekly_forecast"],
        "today_weather": weather_info["today_weather"],
        "gallery": gallery_photos,
        "naver_client_id": getattr(settings, 'NAVER_CLIENT_ID', ''),
        "is_favorited": is_favorited,
        "reviews": reviews,
        "review_count": review_count,
        "avg_rating": avg_rating,
        "user_id": user_id,
        "user_nickname": user_nickname,
    }
    return render(request, 'detail.html', context)

def review_add(request):
    if request.method != 'POST':
        return JsonResponse({'result': 'fail', 'message': '잘못된 요청입니다.'}, status=405)

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'result': 'fail', 'message': '로그인이 필요합니다.'}, status=401)

    spot_code = request.POST.get('spot_code', '').strip()
    rating = request.POST.get('rating', '5').strip()
    content = request.POST.get('content', '').strip()

    if not spot_code:
        return JsonResponse({'result': 'fail', 'message': '관광지 정보가 없습니다.'}, status=400)
    if not content:
        return JsonResponse({'result': 'fail', 'message': '후기 내용을 입력해주세요.'}, status=400)

    try:
        rating_val = int(rating)
        if rating_val < 1 or rating_val > 5:
            rating_val = 5
    except ValueError:
        rating_val = 5

    # 관광지가 DB에 없으면 자동 등록
    spot = TouristSpot.objects.insert_from_api(spot_code)
    if not spot:
        return JsonResponse({'result': 'fail', 'message': '관광지 정보를 불러올 수 없습니다.'}, status=404)

    # 후기 생성 (REVIEW 테이블 INSERT)
    review_code = 'REV' + uuid.uuid4().hex[:17].upper()
    Review.objects.create(
        review_code=review_code,
        user_id=user_id,
        spot=spot,
        rating=rating_val,
        create_date=timezone.now(),
        content=content,
    )

    return JsonResponse({'result': 'ok'})