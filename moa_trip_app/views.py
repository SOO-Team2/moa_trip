import json
import uuid
from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from .models import TouristSpot, Region, Users, Itinerary, ItineraryTime, Review, Favorite
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Avg, Count

def main(request):
    return render(request, 'main.html')

def explore(request):
    selected_region = request.GET.get('region')
    selected_rating = request.GET.get('min_rating')
    selected_pet = request.GET.get('pet_allowed')
    selected_sort = request.GET.get('sort', 'rating')
    spots = TouristSpot.objects.select_related('region').annotate(
        avg_rating=Avg('review__rating'),
        review_count=Count('review'),
    )
    if selected_region:
        spots = spots.filter(region_id=selected_region)
    if selected_rating:
        try:
            spots = spots.filter(avg_rating__gte=float(selected_rating))
        except ValueError:
            pass

    if selected_pet:
        spots = spots.filter(pet_allowed=1)

    if selected_sort == 'review':
        spots = spots.order_by('-review_count')
    else:
        spots = spots.order_by('-avg_rating')


    context = {
        'spots': spots,
        'regions': Region.objects.all(),
        'selected_region': selected_region,
        'selected_rating': selected_rating,
        'selected_pet': selected_pet,
        'selected_sort': selected_sort,   
    }
    return render(request, 'explore.html', context)

def detail(request):
    return render(request, 'detail.html')

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
    return render(request, 'planner.html', {'regions':regions, 'spots_data': spots_data})

def planner_add_spot(request):
    if request.method != 'POST':
        return JsonResponse({'result': 'fail', 'message': '잘못된 요청입니다.'}, status=405)

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'result': 'fail', 'message': '로그인이 필요합니다.'}, status=401)

    spot_code = request.POST.get('spot_code')
    itinerary_title = request.POST.get('itinerary_title') or None
    itinerary_date = request.POST.get('itinerary_date')
    companion = request.POST.get('companion') or None
    pet_accompanied = request.POST.get('pet_accompanied') == 'true'
    visit_time = request.POST.get('visit_time') or None

    if not spot_code or not itinerary_date:
        return JsonResponse({'result': 'fail', 'message': '장소와 날짜는 필수입니다.'}, status=400)

    try:
        spot = TouristSpot.objects.get(spot_code=spot_code)
    except TouristSpot.DoesNotExist:
        return JsonResponse({'result': 'fail', 'message': '존재하지 않는 관광지입니다.'}, status=404)

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

def delete_itinerary(request, itinerary_code):
    itinerary = Itinerary.objects.get(itinerary_code=itinerary_code)
    itinerary.delete()

def login(request):
    return render(request, 'login.html')

def login_ok(request):
    user_id = request.POST.get('user_id', None)
    pw = request.POST.get('pw', None)

    try:
        user = Users.objects.get(user_id=user_id)
    except Users.DoesNotExist:
        user = None
    if user != None:
        # 해당 회원 존재함
        if check_password(pw, user.pw):
            # 로그인 정보 세션에 저장
            request.session['user_id'] = user.user_id

            return redirect('../../')
        else:
            # 비밀번호 틀림
            result = 1
    else:
        # 해당 회원 존재하지 않음
        result = 0

    return render(request, 'login_ok.html', { 'result':result, })

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
        #입력값 누락
        result = 2
    elif '@' not in email:
        #이메일 형식 오류
        result = 3
    else:

        try:
            user = Users.objects.get(user_id=user_id)
        except Users.DoesNotExist:
            user = None

        if user is not None:
            #이미 존재하는 아이디
            result = 1
        else:
            #신규 회원 저장
            Users.objects.create(
                user_id=user_id,
                pw=make_password(pw),
                nickname=nickname,
                email=email,
                join_date=timezone.now().date(),
            )
            result = 0

    return render(request, 'signup_ok.html', {'result':result})

def admin(request):
    return render(request, 'admin.html')