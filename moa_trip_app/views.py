from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import TouristSpot, Region, Users, Itinerary
from django.db.models import Avg, Count

def main(request):
    return render(request, 'main.html')

def explore(request):
    selected_region = request.GET.get('region')
    selected_rating = request.GET.get('min_rating')
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
    context = {
        'spots': spots,
        'regions': Region.objects.all(),
        'selected_region': selected_region,
        'selected_rating': selected_rating,
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
        itinerary = Itinerary.objects.get(user_id=user_id)
    except Users.DoesNotExist:
        # 세션은 남아있는데 데이터 없으면 초기화
        request.session.flush()

    return render(request, 'mypage.html', { 'user':user, 'itinerary':itinerary })

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
        if user.pw == pw:
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

def admin(request):
    return render(request, 'admin.html')