from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db.models import Count
from ..models import Users, Itinerary, Review, Favorite

# ==============================================================================
# 5. 마이페이지
# ==============================================================================
def mypage(request):
    user_id = request.session.get('user_id', None)
    if not user_id:
        return HttpResponse('<script>alert("로그인이 필요한 페이지입니다."); location.href="../login/";</script>')
    try:
        user = Users.objects.get(user_id=user_id)
        itineraries = Itinerary.objects.filter(user_id=user_id).annotate(spot_count=Count('itinerarytime'))
        reviews = Review.objects.filter(user_id=user_id).select_related('spot').order_by('-create_date') #models.py 필드 이름
        favorites = Favorite.objects.filter(user_id=user_id).select_related('spot').order_by('-create_date')
        context = { 'user':user, 'itineraries':itineraries, 'reviews':reviews, 'favorites':favorites }
    except Users.DoesNotExist:
        # 세션은 남아있는데 DB에 회원이 없으면 세션 비우고 로그인 페이지로 이동
        request.session.flush()
        return redirect('login')

    return render(request, 'mypage.html', context)