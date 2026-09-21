from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Count
from ..models import Users

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
        request.session['nickname'] = user.nickname
        return redirect('../../')
    return render(request, 'login_ok.html')

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