from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import TouristSpot, Region, Users, Itinerary, Review
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
    regions = Region.objects.all()
    return render(request, 'planner.html', {'regions':regions})

def mypage(request):
    user_id = request.session.get('user_id', None)
    if not user_id:
        return HttpResponse('<script>alert("로그인이 필요한 페이지입니다."); location.href="../login/";</script>')
    try:
        user = Users.objects.get(user_id=user_id)
        itineraries = Itinerary.objects.filter(user_id=user_id)
        reviews = Review.objects.filter(user_id=user_id).select_related('spot') #models.py 필드 이름
        context = { 'user':user, 'itineraries':itineraries, 'reviews':reviews }
    except Users.DoesNotExist:
        # 세션은 남아있는데 데이터 없으면 초기화
        request.session.flush()

    return render(request, 'mypage.html', context)

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