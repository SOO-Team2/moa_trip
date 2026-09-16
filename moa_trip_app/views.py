from django.shortcuts import render, redirect
from .models import TouristSpot, Region
from django.db.models import Avg, Count

def main(request):
    return render(request, 'main.html')

def explore(request):
    selected_region = request.GET.get('region')
    selected_rating = request.GET.get('min_rating')
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

    if selected_sort == 'review':
        spots = spots.order_by('-review_count')
    else:
        spots = spots.order_by('-avg_rating')


    context = {
        'spots': spots,
        'regions': Region.objects.all(),
        'selected_region': selected_region,
        'selected_rating': selected_rating,
        'selected_sort': selected_sort,
    }
    return render(request, 'explore.html', context)

def detail(request):
    return render(request, 'detail.html')

def planner(request):
    regions = Region.objects.all()
    return render(request, 'planner.html', {'regions':regions})

def mypage(request):
    return render(request, 'mypage.html')

def login(request):
    return render(request, 'login.html')

from .models import Users
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