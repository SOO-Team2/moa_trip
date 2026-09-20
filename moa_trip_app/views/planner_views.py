import uuid
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from ..models import TouristSpot, Region, Itinerary, ItineraryTime, Favorite

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

    # 마이페이지 '저장한 여행 일정'에서 '열기'로 들어온 경우, 저장된 일정 내용을 불러옴
    itinerary = None
    itinerary_items_data = []
    itinerary_code = request.GET.get('itinerary_code')

    if itinerary_code:
        itinerary = Itinerary.objects.filter(itinerary_code=itinerary_code, user_id=user_id).first()
        if itinerary:
            itinerary_times = ItineraryTime.objects.filter(itinerary=itinerary).select_related('spot', 'spot__region')
            itinerary_items_data = [
                {
                    'itinerary_code': itinerary.itinerary_code,
                    'spot_code': it.spot.spot_code,
                    't_name': it.spot.t_name,
                    'entry_fee': it.spot.entry_fee,
                    'pet_allowed': it.spot.pet_allowed,
                    'visit_time': it.visit_time,
                    'region_code': it.spot.region.region_code,
                }
                for it in itinerary_times
            ]

    # detail 페이지 '여행 일정 만들기' 버튼
    initial_spot_data = None
    spot_code = request.GET.get('spot_code')
    if spot_code:
        spot = TouristSpot.objects.insert_from_api(spot_code)
        if spot:
            initial_spot_data = {
                'spot_code': spot.spot_code,
                't_name': spot.t_name,
                'entry_fee': spot.entry_fee,
                'pet_allowed': spot.pet_allowed == 1,
                'region_code': spot.region.region_code if spot.region else None,
                'region_name': spot.region.region_name if spot.region else '',
            }

    return render(request, 'planner.html', {
        'regions': regions,
        'spots_data': spots_data,
        'favorites': favorites,
        'itinerary': itinerary,
        'itinerary_items_data': itinerary_items_data,
        'initial_spot_data': initial_spot_data,
    })

def planner_update_itinerary(request):
    if request.method != 'POST':
        return JsonResponse({'result': 'fail', 'message': '잘못된 요청입니다.'}, status=405)

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'result': 'fail', 'message': '로그인이 필요합니다.'}, status=401)

    itinerary_code = request.POST.get('itinerary_code')

    try:
        itinerary = Itinerary.objects.get(itinerary_code=itinerary_code, user_id=user_id)
    except Itinerary.DoesNotExist:
        return JsonResponse({'result': 'fail', 'message': '수정할 일정을 찾을 수 없습니다.'}, status=404)

    itinerary.itinerary_title = request.POST.get('itinerary_title') or itinerary.itinerary_title
    itinerary.itinerary_date = request.POST.get('itinerary_date') or itinerary.itinerary_date
    itinerary.companion = request.POST.get('companion') or None
    itinerary.pet_accompanied = request.POST.get('pet_accompanied') == 'true'
    itinerary.save()

    return JsonResponse({'result': 'ok'})

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

    spot = TouristSpot.objects.insert_from_api(spot_code)
    if not spot:
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
    spot_code = request.POST.get('spot_code')

    try:
        itinerary = Itinerary.objects.get(itinerary_code=itinerary_code, user_id=user_id)
    except Itinerary.DoesNotExist:
        return JsonResponse({'result': 'fail', 'message':'삭제할 일정을 찾을 수 없습니다.'}, status=404)
    if spot_code:
        # 플래너 타임라인에서 장소 하나만 삭제
        deleted_count, _ = ItineraryTime.objects.filter(itinerary=itinerary, spot_id=spot_code).delete()
        if deleted_count == 0:
            return JsonResponse({'result': 'fail', 'message':'삭제할 장소를 찾을 수 없습니다.'}, status=404)
    else:
        # 마이페이지에서 일정 전체 삭제
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

    spot = TouristSpot.objects.insert_from_api(spot_code)
    if not spot:
        return JsonResponse({'result': 'fail', 'message': '관광지 정보를 불러올 수 없습니다.'}, status=404)

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