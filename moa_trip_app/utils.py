import requests
from django.conf import settings

def fetch_public_data(url, extra_params=None):
    params = {
        "serviceKey": settings.KMA_API_KEY,
        "type": "json",
        "numOfRows": 10,
        "pageNo": 1,
    }
    if extra_params:
        params.update(extra_params)
        
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None