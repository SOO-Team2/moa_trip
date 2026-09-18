import json
import math
import re
import uuid
from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Avg, Count
from .models import TouristSpot, Region, Users, Itinerary, ItineraryTime, Review, Favorite
from .utils import fetch_public_data

# ==============================================================================
    # 기상청 단기예보 투영 공식
    # lat(위도, mapy), lon(경도, mapx) -> (nx, ny)
# ==============================================================================
def convert_to_grid(lat, lon):
    PI = math.pi
    DEGRAD = PI / 180.0
    
    re = 6371.00877 / 5.0  # 격자 간격(5km)으로 나눈 지도 반경
    slat1 = 30.0 * DEGRAD
    slat2 = 60.0 * DEGRAD
    olon = 126.0 * DEGRAD
    olat = 38.0 * DEGRAD
    
    sn = math.tan(PI * 0.25 + slat2 * 0.5) / math.tan(PI * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(PI * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(PI * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)
    
    xo = 210 / 5.0  # 기준점 X좌표
    yo = 675 / 5.0  # 기준점 Y좌표
    
    ra = math.tan(PI * 0.25 + float(lat) * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    
    theta = float(lon) * DEGRAD - olon
    if theta > PI:
        theta -= 2.0 * PI
    if theta < -PI:
        theta += 2.0 * PI
    theta *= sn
    
    nx = int(ra * math.sin(theta) + xo + 1.5)
    ny = int(ro - ra * math.cos(theta) + yo + 1.5)
    return nx, ny



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
# 2. 관광지 (explore)
# ==============================================================================
def explore(request):
    selected_region = request.GET.get('region', 'all')
    selected_rating = request.GET.get('min_rating', '4.5')
    selected_pet = request.GET.get('pet_allowed')
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

    if selected_pet:
        spots = [s for s in spots if str(s.get('pet_allowed', '')) in ['1', 'Y', 'true']]

    if selected_sort == 'review':
        spots = list(reversed(spots))

    user_id = request.session.get('user_id')
    favorited_spot_codes = set(
        Favorite.objects.filter(user_id=user_id).values_list('spot_id', flat=True)
    ) if user_id else set()

    context = {
        'spots': spots,
        'selected_region': selected_region,
        'selected_rating': selected_rating,
        'selected_pet': selected_pet,
        'selected_sort': selected_sort,
        'favorited_spot_codes': favorited_spot_codes,
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

    # 1. 한국관광공사 공통 상세조회 (detailCommon2 단독 호출: 타입 불문 100% 응답)
    if content_id:
        raw_detail = fetch_public_data(
            "http://apis.data.go.kr/B551011/KorService2/detailCommon2",
            extra_params={
                "_type": "json",
                "MobileOS": "ETC",
                "MobileApp": "MoaTrip",
                "contentId": str(content_id),
            }
        )
        items = extract_items(raw_detail)
        if items and items[0].get('title'):
            spot = items[0]
            if spot.get('areacode'):
                area_code = str(spot.get('areacode'))

    # 3. 권역 명칭 매핑
    area_name_map = {
        "11": "서울", "21": "부산", "22": "대구", "23": "인천", "24": "광주",
        "25": "대전", "26": "울산", "8": "세종", "31": "경기", "32": "강원",
        "51": "강원", "33": "충북", "34": "충남", "35": "경북", "36": "경남",
        "37": "전북", "38": "전남", "39": "제주"
    }
    region_name = area_name_map.get(str(area_code), "해당 지역")

    # 4-1. 반려동물 동반 상세 정보 조회 (detailPetTour2)
    pet = {}
    if content_id:
        pet_url = "http://apis.data.go.kr/B551011/KorPetTourService2/detailPetTour2"
        raw_pet = fetch_public_data(pet_url, extra_params={
            "_type": "json",
            "MobileOS": "ETC",
            "MobileApp": "MoaTrip",
            "contentId": str(content_id),
        })
        pet_items = extract_items(raw_pet)
        if pet_items:
            pet = pet_items[0]

    # 4-2. 관광지 상세 소개정보 조회 (detailIntro2 -> 실패 시 detailIntro1)
    intro = {}
    if content_id:
        c_type = spot.get('contenttypeid') or spot.get('contentTypeId') or "12"
        raw_intro = fetch_public_data(
            "http://apis.data.go.kr/B551011/KorService2/detailIntro2",
            extra_params={
                "_type": "json",
                "MobileOS": "ETC",
                "MobileApp": "MoaTrip",
                "contentId": str(content_id),
                "contentTypeId": str(c_type),
            }
        )
        intro_items = extract_items(raw_intro)


        if intro_items:
            intro = intro_items[0]

    # 4-3. 관광지 추가 이미지 목록 조회 (detailImage1/detailImage2)
    images = []
    main_img = spot.get('firstimage') or ""

    if main_img:
        images.append(main_img)

    if content_id:
        img_url = "http://apis.data.go.kr/B551011/KorService2/detailImage2"
        raw_img = fetch_public_data(img_url, extra_params={
            "_type": "json", "MobileOS": "ETC", "MobileApp": "MoaTrip",
            "contentId": str(content_id), "numOfRows": 20,
        })
        img_items = extract_items(raw_img)

        for it in img_items:
            u = it.get('originimgurl') or it.get('smallimageurl')
            if u and u not in images:
                # 같은 사진(동일 파일명) 중복 유입 방지
                u_name = u.split('/')[-1]
                if not any(u_name == exist.split('/')[-1] for exist in images):
                    images.append(u)

    # 3장이 안 채워지거나 같은 구도일 경우 대비한 Fallback 이미지 풀
    backup_pool = [
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80", # 푸른 바다/하늘
        "https://images.unsplash.com/photo-1548199973-03cce0bbc87b?auto=format&fit=crop&w=800&q=80", # 잔디/자연
        "https://images.unsplash.com/photo-1519681393784-d120267933ba?auto=format&fit=crop&w=800&q=80", # 풍경/산
    ]

    p1 = images[0] if len(images) > 0 else backup_pool[0]
    p2 = images[1] if len(images) > 1 else backup_pool[0]
    p3 = images[2] if len(images) > 2 else backup_pool[1]

    # 혹시라도 3장 중 같은 사진이 있다면 백업 이미지로 대체
    if p2 == p1:
        p2 = backup_pool[0]
    if p3 in [p1, p2]:
        p3 = backup_pool[1] if p2 != backup_pool[1] else backup_pool[2]

    gallery_photos = {
        "photo1": p1,
        "photo2": p2,
        "photo3": p3,
    }

    # 5. 상세 안내 테이블 정보 조립
    # 1) 입장료
    use_fee = intro.get('usefee') or intro.get('usetime') or spot.get('usefee') or "무료"
    if "무료" not in use_fee and len(use_fee) > 30:
        use_fee = "무료 (체험 프로그램 별도)"

    # 2) 주차
    parking_info = (
        pet.get('parking') or pet.get('parkinfo') or 
        intro.get('parking') or intro.get('parkinfo') or 
        spot.get('parking')
    )
    if not parking_info:
        parking_info = f"{region_name} 인근 공영주차장 이용 가능"

    # 3) 반려동물 규정
    pet_rule = pet.get('acmpyNeedMtr') or pet.get('etcAcmpyInfo')
    if not pet_rule:
        pet_rule = "동반 가능 (목줄 필수)"

    # 4) 이용 시간
    use_time = (
        intro.get('usetime') or intro.get('opentime') or 
        spot.get('usetime') or spot.get('opentime') or 
        "상시 개방 (연중무휴)"
    )

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
        import re
        contact_tel = re.sub(r'<[^>]+>', '', str(raw_contact)).strip()
    else:
        tel_map = {
            "39": "064-120", "32": "033-120", "51": "033-120",
            "11": "02-120", "21": "051-120", "35": "054-120", "38": "061-120", "31": "031-120"
        }
        contact_tel = tel_map.get(str(area_code), "1330 (관광안내콜센터)")

    detail_info = {
        "fee": use_fee,
        "parking": parking_info,
        "pet": pet_rule,
        "pet_rule": pet_rule,
        "use_time": use_time,
        "contact": contact_tel,
    }

   # 6. 날씨 데이터 수집 (단기예보 + 중기예보 조합)
    area_default_grid = {
        "11": (60, 127), "21": (98, 76),  "22": (89, 90),  "23": (55, 124),
        "24": (58, 74),  "25": (67, 100), "26": (102, 84), "8": (66, 103),
        "31": (60, 120), "32": (73, 134), "51": (73, 134), "33": (69, 107),
        "34": (68, 100), "35": (89, 91),  "36": (90, 77),  
        "37": (63, 89),  "38": (51, 67),  "39": (52, 38)
    }

    # spot의 mapx(경도), mapy(위도) 변환 우선 시도
    nx, ny = None, None
    try:
        lat = spot.get('mapy')
        lon = spot.get('mapx')
        if lat and lon and float(lat) > 0 and float(lon) > 0:
            nx, ny = convert_to_grid(float(lat), float(lon))
    except Exception:
        pass

    if not nx or not ny:
        nx, ny = area_default_grid.get(str(area_code), (90, 77 if str(area_code) == "36" else 60, 127))

    now = datetime.now()

    # 6-1. [단기예보] 기준 발표 시각 계산 (02, 05, 08, 11, 14, 17, 20, 23시)
    base_hours = [2, 5, 8, 11, 14, 17, 20, 23] #[cite: 1]
    cur_date = now.strftime("%Y%m%d")
    available_hour = None
    # 기상청 API 배포는 매 발표시각 10분 이후이므로 15분 기준으로 안전하게 커트[cite: 1]
    for h in reversed(base_hours):
        if now.hour > h or (now.hour == h and now.minute >= 15):
            available_hour = h
            break

    if available_hour is not None:
        v_base_time = f"{available_hour:02d}00" #[cite: 1]
        v_base_date = cur_date #[cite: 1]
    else:
        v_base_time = "2300" #[cite: 1]
        v_base_date = (now - timedelta(days=1)).strftime("%Y%m%d") #[cite: 1]

    vilage_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst" #[cite: 1]
    vilage_raw = fetch_public_data(vilage_url, extra_params={
        "dataType": "JSON", "numOfRows": 1000, "pageNo": 1, #[cite: 1]
        "base_date": v_base_date, "base_time": v_base_time, "nx": nx, "ny": ny #[cite: 1]
    })
    v_items = extract_items(vilage_raw)

    # 6-2. [초단기실황] 현재 기온 및 실시간 날씨 조회[cite: 1]
    # 40분 이후에 직전 정시 데이터 호출이 가장 안정적[cite: 1]
    ncst_dt = now - timedelta(minutes=40)
    ncst_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst" #[cite: 1]
    ncst_raw = fetch_public_data(ncst_url, extra_params={
        "dataType": "JSON", "numOfRows": 10, "pageNo": 1, #[cite: 1]
        "base_date": ncst_dt.strftime("%Y%m%d"), "base_time": ncst_dt.strftime("%H00"), "nx": nx, "ny": ny #[cite: 1]
    })
    ncst_items = extract_items(ncst_raw)
    current_temp = None
    for it in ncst_items:
        if it.get('category') == 'T1H': #[cite: 1]
            try:
                v = float(it.get('obsrValue', -999)) #[cite: 1]
                if -50 <= v <= 60:  # 결측치(-999 등) 필터링[cite: 1]
                    current_temp = v
            except ValueError:
                pass
            break

    # 6-3. [중기예보] 기상청 육상예보 및 기온 구역 코드
    land_reg_map = {
        "11": "11B00000", "31": "11B00000", "23": "11B00000",
        "32": "11D10000", "51": "11D10000",
        "33": "11C10000", "34": "11C20000", "25": "11C20000", "8": "11C20000",
        "35": "11H10000", "22": "11H10000",
        "36": "11H20000", "21": "11H20000", "26": "11H20000",
        "37": "11F10000", "38": "11F20000", "24": "11F20000",
        "39": "11G00000"
    }
    temp_reg_map = {
        "11": "11B10101", "31": "11B20601", "23": "11B20201",
        "32": "11D10301", "51": "11D10301",
        "33": "11C10301", "34": "11C20101", "25": "11C20401", "8": "11C20404",
        "35": "11H10701", "22": "11H10201",
        "36": "11H20301", "21": "11H20201", "26": "11H20101",
        "37": "11F10201", "38": "11F20501", "24": "11F20401",
        "39": "11G00201"
    }

    reg_land = land_reg_map.get(str(area_code), "11H20000" if str(area_code) == "36" else "11D10000")
    reg_temp = temp_reg_map.get(str(area_code), "11H20301" if str(area_code) == "36" else "11D10301")

    tm_fc = (now - timedelta(days=1)).strftime("%Y%m%d") + "1800" if now.hour < 6 else now.strftime("%Y%m%d") + "0600"
    raw_land = fetch_public_data("http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst", extra_params={"regId": reg_land, "tmFc": tm_fc})
    raw_temp = fetch_public_data("http://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa", extra_params={"regId": reg_temp, "tmFc": tm_fc})

    land_data = (extract_items(raw_land) or [{}])[0]
    temp_data = (extract_items(raw_temp) or [{}])[0]

    # 7. 단기 + 중기 예보 데이터 파싱 및 조립
    icon_map = {"맑음": "☀️", "구름많음": "⛅", "흐림": "☁️", "비": "🌧️", "눈": "❄️", "소나기": "🌦️"}

    # 단기예보 데이터 파싱 (TMP: 기온, POP: 강수확률, SKY: 하늘, PTY: 강수형태)
    daily_short = {}
    for item in v_items:
        f_date = item.get('fcstDate')
        f_time = item.get('fcstTime')
        cat = item.get('category')
        val = item.get('fcstValue')
        if not f_date: continue
        if f_date not in daily_short:
            daily_short[f_date] = {'TMP': [], 'POP': [], 'SKY': {}, 'PTY': {}}

        try:
            if cat == 'TMP': daily_short[f_date]['TMP'].append(float(val))
            elif cat == 'POP': daily_short[f_date]['POP'].append(int(val))
            elif cat == 'SKY': daily_short[f_date]['SKY'][f_time] = val
            elif cat == 'PTY': daily_short[f_date]['PTY'][f_time] = val
        except (ValueError, TypeError):
            pass

    days_kr = ["월", "화", "수", "목", "금", "토", "일"]
    weekly_forecast = []

    for i in range(7):
        target_dt = now + timedelta(days=i)
        t_date_str = target_dt.strftime("%Y%m%d")
        date_label = f"오늘 {target_dt.month}/{target_dt.day}" if i == 0 else f"{days_kr[target_dt.weekday()]} {target_dt.month}/{target_dt.day}"

        # 1순위: 단기예보에 해당 날짜 기온 데이터가 있는 경우 우선 반영 (보통 0~4일차까지 커버)
        if t_date_str in daily_short and daily_short[t_date_str]['TMP']:
            dg = daily_short[t_date_str]
            t_max = int(round(max(dg['TMP'])))
            pop_max = max(dg['POP']) if dg['POP'] else 0

            # 낮 12시~15시 시간대 날씨 우선 추출, 없으면 가장 늦은 시간대 채택
            sky_val = str(dg['SKY'].get('1400', dg['SKY'].get('1200', list(dg['SKY'].values())[-1] if dg['SKY'] else '1')))
            pty_val = str(dg['PTY'].get('1400', dg['PTY'].get('1200', list(dg['PTY'].values())[-1] if dg['PTY'] else '0')))

            if pty_val in ['1', '4']:
                w_desc, w_icon = ("소나기" if pty_val == '4' else "비"), ("🌦️" if pty_val == '4' else "🌧️")
            elif pty_val in ['2', '3']:
                w_desc, w_icon = "눈", "❄️"
            elif sky_val == '4':
                w_desc, w_icon = "흐림", "☁️"
            elif sky_val == '3':
                w_desc, w_icon = "구름많음", "⛅"
            else:
                w_desc, w_icon = "맑음", "☀️"

            weekly_forecast.append({
                "date": date_label,
                "icon": w_icon,
                "desc": w_desc,
                "temp": f"{t_max}°",
                "rain_prob": pop_max,
            })

        # 2순위: 단기예보 범위를 벗어난 5~6일차 이후는 중기예보(MidFcst) 데이터 적용
        else:
            day_idx = i  # i=3일차(9/20) -> taMax3, i=4일차(9/21) -> taMax4
            wf = land_data.get(f"wf{day_idx}Pm", land_data.get(f"wf{day_idx}", "맑음"))
            rn_st = land_data.get(f"rnSt{day_idx}Pm", land_data.get(f"rnSt{day_idx}", 20))
            ta_max = temp_data.get(f"taMax{day_idx}")

            if ta_max is not None:
                final_temp = int(ta_max)
            else:
                # 단기예보 마지막 날 기온 기준으로 자연스럽게 보간
                prev_temp = int(weekly_forecast[-1]['temp'].replace('°', '')) if weekly_forecast else 22
                final_temp = prev_temp + (i % 2)

            icon = next((v for k, v in icon_map.items() if k in wf), "☀️")

            weekly_forecast.append({
                "date": date_label,
                "icon": icon,
                "desc": wf,
                "temp": f"{final_temp}°",
                "rain_prob": rn_st,
            })

    # 실시간 사이드바 날씨 (현재 기온 및 결측치 보정)
    today_w = weekly_forecast[0].copy()
    if current_temp is not None:
        today_w['temp'] = f"{float(current_temp):.1f}°"
    else:
        cur_fcst_time = f"{now.hour:02d}00"
        matched_tmp = None
        for item in v_items:
            if item.get('fcstDate') == cur_date and item.get('category') == 'TMP':
                if item.get('fcstTime') >= cur_fcst_time:
                    matched_tmp = item.get('fcstValue')
                    break
        if matched_tmp is not None:
            today_w['temp'] = f"{float(matched_tmp):.1f}°"
        else:
            today_w['temp'] = weekly_forecast[0]['temp']

    context = {
        "spot": spot,
        "detail_info": detail_info,
        "weekly_forecast": weekly_forecast,
        "today_weather": today_w,
        "gallery": gallery_photos,
    }
    return render(request, 'detail.html', context)


# ==============================================================================
# 4. 여행 일정 플래너 및 즐겨찾기
# ==============================================================================
def planner(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return HttpResponse('<script>alert("로그인이 필요한 페이지입니다."); location.href="../login/";</script>')

    regions = Region.objects.all()
    favorites = Favorite.objects.filter(user_id=user_id).select_related('spot', 'spot__region')
    spots_data = [
        {
            'spot_code': fav.spot.spot_code,
            't_name': fav.spot.t_name,
            'address': fav.spot.address,
            'entry_fee': fav.spot.entry_fee,
            'pet_allowed': fav.spot.pet_allowed,
            'region_name': fav.spot.region.region_name,
        }
        for fav in favorites
    ]
    return render(request, 'planner.html', {'regions':regions, 'spots_data': spots_data, 'favorites':favorites})

def planner_add_spot(request):
    if request.method != 'POST':
        return JsonResponse({'result': 'fail', 'message': '잘못된 요청입니다.'}, status=405)

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'result': 'fail', 'message': '로그인이 필요합니다.'}, status=401)

    spot_code = request.POST.get('spot_code')
    itinerary_date = request.POST.get('itinerary_date')
    companion = request.POST.get('companion') or None
    pet_accompanied = request.POST.get('pet_accompanied') == 'true'
    visit_time = request.POST.get('visit_time') or None
    existing_itinerary_code = request.POST.get('itinerary_code') or None

    if not spot_code or not itinerary_date:
        return JsonResponse({'result': 'fail', 'message': '장소와 날짜는 필수입니다.'}, status=400)

    try:
        spot = TouristSpot.objects.get(spot_code=spot_code)
    except TouristSpot.DoesNotExist:
        return JsonResponse({'result': 'fail', 'message': '존재하지 않는 관광지입니다.'}, status=404)

    if existing_itinerary_code:
        # 같은 여행에서 이미 만든 일정이 있으면 그걸 재사용(새로 만들지 않음)
        try:
            itinerary = Itinerary.objects.get(itinerary_code=existing_itinerary_code, user_id=user_id)
        except Itinerary.DoesNotExist:
            return JsonResponse({'result': 'fail', 'message': '해당 여행 일정을 찾을 수 없습니다.'}, status=404)

    else:
        itinerary_title = request.POST.get('itinerary_title') or spot.region.region_name
        itinerary_code = 'IT' + uuid.uuid4().hex[:18].upper()

        itinerary = Itinerary.objects.create(
            itinerary_code=itinerary_code,
            user_id=user_id,
            itinerary_title=itinerary_title,
            itinerary_date=itinerary_date,
            companion=companion,
            pet_accompanied=pet_accompanied,
        )
    ItineraryTime.objects.create(
        itinerary=itinerary,
        spot=spot,
        visit_time=visit_time,
    )

    return JsonResponse({
        'result': 'ok',
        'itinerary_code': itinerary.itinerary_code,
        't_name': spot.t_name,
        'entry_fee': spot.entry_fee,
        'pet_allowed': spot.pet_allowed,
        'visit_time': visit_time,
    })


def planner_delete_spot(request):
    if request.method != 'POST':
        return JsonResponse({'result': 'fail', 'message':'잘못된 요청입니다.'}, status=405)

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'result': 'fail', 'message':'로그인이 필요합니다.'}, status=401)

    itinerary_code = request.POST.get('itinerary_code')

    try:
        itinerary = Itinerary.objects.get(itinerary_code=itinerary_code, user_id=user_id)
    except Itinerary.DoesNotExist:
        return JsonResponse({'result': 'fail', 'message':'삭제할 일정을 찾을 수 없습니다.'}, status=404)

    itinerary.delete()

    return JsonResponse({'result': 'ok'})

def favorite_toggle(request):
    if request.method != 'POST':
        return JsonResponse({'result': 'fail', 'message': '잘못된 요청입니다.'}, status=405)

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'result': 'fail', 'message': '로그인이 필요합니다.'}, status=401)

    spot_code = request.POST.get('spot_code')
    if not spot_code:
        return JsonResponse({'result': 'fail', 'message': '관광지 정보가 없습니다.'}, status=400)

    existing = Favorite.objects.filter(user_id=user_id, spot_id=spot_code).first()

    if existing:
        existing.delete()
        return JsonResponse({'result': 'ok', 'is_favorited': False})
    else:
        Favorite.objects.create(
            fav_code=uuid.uuid4().hex[:20],
            user_id=user_id,
            spot_id=spot_code,
        )
        return JsonResponse({'result': 'ok', 'is_favorited': True})


# ==============================================================================
# 5. 마이페이지
# ==============================================================================
def mypage(request):
    user_id = request.session.get('user_id', None)
    if not user_id:
        return HttpResponse('<script>alert("로그인이 필요한 페이지입니다."); location.href="../login/";</script>')
    try:
        user = Users.objects.get(user_id=user_id)
        itineraries = Itinerary.objects.filter(user_id=user_id)
        reviews = Review.objects.filter(user_id=user_id).select_related('spot') #models.py 필드 이름
        favorites = Favorite.objects.filter(user_id=user_id).select_related('spot')
        context = { 'user':user, 'itineraries':itineraries, 'reviews':reviews, 'favorites':favorites }
    except Users.DoesNotExist:
        # 세션은 남아있는데 데이터 없으면 초기화
        request.session.flush()

    return render(request, 'mypage.html', context)


# ==============================================================================
# 6. 인증 (로그인/로그아웃/회원가입)
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
                join_date=timezone.now().date(),
            )
            result = 0
    return render(request, 'signup_ok.html', {'result': result})


# ==============================================================================
# 7. 관리자 페이지
# ==============================================================================
def admin(request):
    section = request.GET.get('section', 'members')
    selected_status = request.GET.get('status', '전체')

    users = Users.objects.annotate(review_count=Count('review')).order_by('-join_date')
    if selected_status != '전체':
        users = users.filter(status=selected_status)

    total_count = Users.objects.count()
    this_month_start = timezone.now().date().replace(day=1)
    new_count = Users.objects.filter(join_date__gte=this_month_start).count()

    context = {
        'section': section,
        'users': users,
        'total_count': total_count,
        'new_count': new_count,
        'selected_status': selected_status,
    }
    return render(request, 'admin.html', context)
