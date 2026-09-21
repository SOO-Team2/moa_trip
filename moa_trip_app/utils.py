import requests, xmltodict, math
from django.conf import settings
from datetime import datetime, timedelta
from .constants import get_region

def fetch_public_data(url, extra_params=None):
    api_key = getattr(settings, 'DATA_GO_KR_KEY', getattr(settings, 'KMA_API_KEY', ''))
    
    # 공통 필수 파라미터
    params = {
        "serviceKey": api_key,
        "numOfRows": 10,
        "pageNo": 1,
    }

    # 기관별 JSON 파라미터 분기
    if "kma.go.kr" in url or "MidFcstInfoService" in url:
        # 기상청 규칙
        params["dataType"] = "JSON"
    else:
        # 한국관광공사 규칙
        params["_type"] = "json"
        params["MobileOS"] = "ETC" #정부 보고용
        params["MobileApp"] = "MoaTrip"

    if extra_params:
        params.update(extra_params)
        
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                return xmltodict.parse(response.text) #xml로 줄 경우
    except requests.RequestException as e:
        print(f"{e}")
        
    return None


def api_items(raw_json):
    #공공데이터 4겹에서 items 리스트 안전하게 추출
    if not raw_json or not isinstance(raw_json, dict):
        return []
    body = raw_json.get('response', {}).get('body', {})
    if not isinstance(body, dict):
        return []
    items_box = body.get('items')
    if not items_box or not isinstance(items_box, dict):
        return []
    items = items_box.get('item', [])
    if isinstance(items, list):
        return items
    return [items] if items else [] #결과가 1개일 경우


def api_totalcount(raw_json):
    #공공데이터 body 안의 totalCount 추출
    if not raw_json or not isinstance(raw_json, dict):
        return 0
    body = raw_json.get('response', {}).get('body', {})
    if isinstance(body, dict):
        try:
            return int(body.get('totalCount', 0) or 0) #문자열 또는 null
        except (ValueError, TypeError):
            return 0
    return 0


def short_address(address, max_words=3, default='주소 정보 준비 중'):
    #주소에서 앞의 n개 어절만 추출 (기본 3어절)
    if address and isinstance(address, str): #타입 검사
        words = address.strip().split()
        if words:
            return ' '.join(words[:max_words])
    return default

def to_grid(lat, lon):
    """
    기상청 단기예보 투영 공식
    lat(위도, mapy), lon(경도, mapx) -> (nx, ny)
    """
    PI = math.pi
    DEGRAD = PI / 180.0  #라디안으로 바꾸는 계수

    re = 6371.00877 / 5.0  # 지구 반지름을 격자 1칸 크기(5km)로 나눈 값
    slat1 = 30.0 * DEGRAD  # 북위 30도
    slat2 = 60.0 * DEGRAD  # 북위 60도
    olon = 126.0 * DEGRAD  # 동경 126도
    olat = 38.0 * DEGRAD   # 북위 38도

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
    return nx, ny #기상청 격자 좌표


def get_weather(lat, lon, areacode):
    """
    기상청 초단기실황, 단기예보, 중기예보 조합하여 날씨 데이터 반환
    """
    region_info = get_region(areacode)
    now = datetime.now()

    # 격자 좌표 결정
    nx, ny = None, None
    try:
        if lat and lon and float(lat) > 0 and float(lon) > 0:
            nx, ny = to_grid(float(lat), float(lon))
    except Exception:
        pass

    if not nx or not ny:
        nx, ny = region_info["grid"]

    # [초단기실황] 실시간 기온 및 강수량 조회
    ncst_dt = now - timedelta(minutes=40) # 매시 40분 이후 API 제공
    ncst_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    ncst_raw = fetch_public_data(ncst_url, extra_params={
        "dataType": "JSON", "numOfRows": 10, "pageNo": 1,
        "base_date": ncst_dt.strftime("%Y%m%d"), "base_time": ncst_dt.strftime("%H00"), "nx": nx, "ny": ny
    })
    ncst_items = api_items(ncst_raw)

    current_temp = None
    current_rain = None
    for it in ncst_items:
        category = it.get('category')
        if category == 'T1H': #1시간 기온
            try:
                v = float(it.get('obsrValue', -999)) #관측값
                if -50 <= v <= 60:  # 비정상 수치(-999 등) 필터링
                    current_temp = v
            except ValueError:
                pass

        elif category == 'RN1': #강수량 (mm)
            try:
                v = float(it.get('obsrValue', -999))
                if v >= 0:
                    current_rain = v
            except (ValueError, TypeError):
                pass

        if current_temp is not None and current_rain is not None:
            break

    # [단기예보] 발표 시각 계산 후 호출
    base_hours = [2, 5, 8, 11, 14, 17, 20, 23] #단기예보 정규 발표 시각
    cur_date = now.strftime("%Y%m%d")
    available_hour = None

    for h in reversed(base_hours):
        if now.hour > h or (now.hour == h and now.minute >= 15): # 기상청 API 배포는 매 발표시각 10분 이후, 15분 기준으로 컷
            available_hour = h
            break
    if available_hour is not None:
        v_base_time = f"{available_hour:02d}00"
        v_base_date = cur_date
    else:
        v_base_time = "2300"
        v_base_date = (now - timedelta(days=1)).strftime("%Y%m%d") #0시~2시 14분 사이 예보 없음

    vilage_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    vilage_raw = fetch_public_data(vilage_url, extra_params={
        "dataType": "JSON", "numOfRows": 1000, "pageNo": 1,
        "base_date": v_base_date, "base_time": v_base_time, "nx": nx, "ny": ny
    })
    v_items = api_items(vilage_raw)

    # [중기예보] 지역 및 시각 계산 후 조회
    reg_land = region_info["land"] #날씨 상태
    reg_temp = region_info["temp"] #최고 기온

    tm_fc = (now - timedelta(days=1)).strftime("%Y%m%d") + "1800" if now.hour < 6 else now.strftime("%Y%m%d") + "0600" #매일 6시, 18시 발표
    raw_land = fetch_public_data(
        "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst",
        extra_params={"regId": reg_land, "tmFc": tm_fc}
    )
    raw_temp = fetch_public_data(
        "http://apis.data.go.kr/1360000/MidFcstInfoService/getMidTa",
        extra_params={"regId": reg_temp, "tmFc": tm_fc}
    )

    land_data = (api_items(raw_land) or [{}])[0] #데이터 1건
    temp_data = (api_items(raw_temp) or [{}])[0]

    # 단기 + 중기 데이터 가공
    icon_map = {"맑음": "☀️", "구름많음": "⛅", "흐림": "☁️", "비": "🌧️", "눈": "❄️", "소나기": "🌦️"}

    # 단기예보 데이터 파싱 (TMP: 1시간 기온, SKY: 하늘상태, PTY: 강수형태)
    daily_short = {}
    for item in v_items:
        f_date = item.get('fcstDate') #예보 날짜
        f_time = item.get('fcstTime') #예보 시각
        cat = item.get('category') #항목
        val = item.get('fcstValue') #값
        if not f_date:
            continue
        if f_date not in daily_short:
            daily_short[f_date] = {'TMP': [], 'SKY': {}, 'PTY': {}}

        try:
            if cat == 'TMP': #최고 기온 계산 위해 리스트에 담음
                daily_short[f_date]['TMP'].append(float(val))
            elif cat == 'SKY':
                daily_short[f_date]['SKY'][f_time] = val #날씨 대표 아이콘 12시~14시
            elif cat == 'PTY':
                daily_short[f_date]['PTY'][f_time] = val
        except (ValueError, TypeError):
            pass

    days_kr = ["월", "화", "수", "목", "금", "토", "일"] #weekday()와 매치
    weekly_forecast = []

    for i in range(7):
        target_dt = now + timedelta(days=i)
        t_date_str = target_dt.strftime("%Y%m%d")
        date_label = f"오늘 {target_dt.month}/{target_dt.day}" if i == 0 else f"{days_kr[target_dt.weekday()]} {target_dt.month}/{target_dt.day}"

        # 1순위: 단기예보 데이터 우선 반영 (보통 0~4일차까지)
        if t_date_str in daily_short and daily_short[t_date_str]['TMP']:
            dg = daily_short[t_date_str]
            t_max = int(round(max(dg['TMP']))) #대표 기온=낮 최고 기온

            # 12시와 14시 날씨 우선 추출, 없으면 가장 늦은 시간대 채택
            sky_val = str(dg['SKY'].get('1400', dg['SKY'].get('1200', list(dg['SKY'].values())[-1] if dg['SKY'] else '1')))
            pty_val = str(dg['PTY'].get('1400', dg['PTY'].get('1200', list(dg['PTY'].values())[-1] if dg['PTY'] else '0')))

            if pty_val in ['1', '4']: #비나 눈 먼저 검사
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
            })

        # 2순위: 5~6일차 이후는 중기예보 데이터 적용
        else:
            day_idx = i  # i=3일차 -> taMax3, i=4일차 -> taMax4 (JSON 키 이름 뒤)
            wf = land_data.get(f"wf{day_idx}Pm", land_data.get(f"wf{day_idx}", "맑음")) #오후 -> 종일 -> 맑음
            ta_max = temp_data.get(f"taMax{day_idx}")

            if ta_max is not None:
                final_temp = int(ta_max)
            else:
                prev_temp = int(weekly_forecast[-1]['temp'].replace('°', '')) if weekly_forecast else 22
                final_temp = prev_temp + (i % 2) #전날 기온에서 +-1도

            icon = next((v for k, v in icon_map.items() if k in wf), "☀️") #구름많고 비, 숫자 아님

            weekly_forecast.append({
                "date": date_label,
                "icon": icon,
                "desc": wf,
                "temp": f"{final_temp}°",
            })

    # 6. 사이드바 실시간 날씨 (현재 기온 및 결측치 보정)
    if weekly_forecast:
        today_w = weekly_forecast[0].copy()
    else:
        today_w = {"date": "오늘", "icon": "☀️", "desc": "맑음", "temp": "20°"}

    if current_temp is not None: #초단기실황 기온
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
        elif weekly_forecast:
            today_w['temp'] = weekly_forecast[0]['temp']

    # 강수량 설정 (초단기실황)
    if current_rain is not None:
        if current_rain > 0:
            today_w['rain'] = f"{current_rain:.1f}mm" if (current_rain % 1 != 0) else f"{int(current_rain)}mm"
        else:
            today_w['rain'] = "0mm"
    else:
        today_w['rain'] = "0mm"

    return {
        "weekly_forecast": weekly_forecast,
        "today_weather": today_w,
    }