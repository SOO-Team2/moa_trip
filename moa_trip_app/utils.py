import requests
import xmltodict
from django.conf import settings

def fetch_public_data(url, extra_params=None):
    api_key = getattr(settings, 'DATA_GO_KR_KEY', getattr(settings, 'KMA_API_KEY', ''))
    
    # 공통 필수 파라미터
    params = {
        "serviceKey": api_key,
        "numOfRows": 10,
        "pageNo": 1,
    }

    # API 제공 기관별 JSON 파라미터 자동 분기
    if "kma.go.kr" in url or "MidFcstInfoService" in url:
        # 기상청 API 규격
        params["dataType"] = "JSON"
    else:
        # 한국관광공사 API 규격
        params["_type"] = "json"

    if extra_params:
        params.update(extra_params)
        
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                return xmltodict.parse(response.text)
    except requests.RequestException as e:
        print(f"[API 호출 오류] {url} : {e}")
        
    return None