from django.db import models


# ==============================================================================
# 1. 회원 (USERS)
# ==============================================================================
class Users(models.Model):
    user_id = models.CharField(db_column='USER_ID', primary_key=True, max_length=20, verbose_name='회원 ID')
    nickname = models.CharField(db_column='NICKNAME', max_length=20, verbose_name='닉네임')
    email = models.CharField(db_column='EMAIL', max_length=255, verbose_name='이메일')
    pw = models.CharField(db_column='PW', max_length=20, verbose_name='비밀번호')
    join_date = models.DateField(db_column='JOIN_DATE', blank=True, null=True, verbose_name='가입일자')

    class Meta:
        managed = False
        db_table = 'USERS'
        verbose_name = '회원'
        verbose_name_plural = '회원 목록'

    def __str__(self):
        return f"{self.nickname} ({self.user_id})"


# ==============================================================================
# 2. 지역 (REGION)
# ==============================================================================
class Region(models.Model):
    region_code = models.CharField(db_column='REGION_CODE', primary_key=True, max_length=20, verbose_name='지역 코드')
    region_name = models.CharField(db_column='REGION_NAME', max_length=255, verbose_name='지역명')

    class Meta:
        managed = False
        db_table = 'REGION'
        verbose_name = '지역'
        verbose_name_plural = '지역 목록'

    def __str__(self):
        return self.region_name


# ==============================================================================
# 3. 관광지 (TOURISTSPOT)
# ==============================================================================
class TouristSpot(models.Model):
    spot_code = models.CharField(db_column='SPOT_CODE', primary_key=True, max_length=20, verbose_name='관광지 코드')
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column='REGION_CODE', verbose_name='지역')
    t_name = models.CharField(db_column='T_NAME', max_length=255, verbose_name='관광지명')
    address = models.CharField(db_column='ADDRESS', max_length=255, verbose_name='주소')
    category = models.CharField(db_column='CATEGORY', max_length=20, blank=True, null=True, verbose_name='카테고리')
    entry_fee = models.IntegerField(db_column='ENTRY_FEE', verbose_name='입장료')
    parking_info = models.CharField(db_column='PARKING_INFO', max_length=20, blank=True, null=True, verbose_name='주차 정보')
    operating_hours = models.CharField(db_column='OPERATING_HOURS', max_length=255, verbose_name='운영 시간')
    phone = models.CharField(db_column='PHONE', max_length=20, verbose_name='문의 전화번호')
    pet_allowed = models.BooleanField(db_column='PET_ALLOWED', verbose_name='반려동물 동반 가능 여부')

    class Meta:
        managed = False
        db_table = 'TOURISTSPOT'
        verbose_name = '관광지'
        verbose_name_plural = '관광지 목록'

    def __str__(self):
        return self.t_name


# ==============================================================================
# 4. 축제 (FESTIVAL)
# ==============================================================================
class Festival(models.Model):
    festival_id = models.CharField(db_column='FESTIVAL_ID', primary_key=True, max_length=20, verbose_name='축제 ID')
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column='REGION_CODE', verbose_name='지역')
    festival_name = models.CharField(db_column='FESTIVAL_NAME', max_length=255, verbose_name='축제명')
    start_date = models.DateField(db_column='START_DATE', verbose_name='시작일자')
    end_date = models.DateField(db_column='END_DATE', verbose_name='종료일자')
    festival_location = models.CharField(db_column='FESTIVAL_LOCATION', max_length=255, blank=True, null=True, verbose_name='축제 장소')

    class Meta:
        managed = False
        db_table = 'FESTIVAL'
        verbose_name = '축제'
        verbose_name_plural = '축제 목록'

    def __str__(self):
        return self.festival_name


# ==============================================================================
# 5. 날씨 캐시 (WEATHERCACHE)
# * 실제 DB 복합 PK (WEATHER_CONDITION, REGION_CODE) -> Django 단일 PK + unique_together 처리
# ==============================================================================
class WeatherCache(models.Model):
    weather_condition = models.CharField(db_column='WEATHER_CONDITION', primary_key=True, max_length=20, verbose_name='기상 상태')
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column='REGION_CODE', verbose_name='지역')
    forecast_date = models.DateField(db_column='FORECAST_DATE', verbose_name='예보 날짜')
    temp_high = models.IntegerField(db_column='TEMP_HIGH', blank=True, null=True, verbose_name='최고 기온')
    precip_pct = models.IntegerField(db_column='PRECIP_PCT', blank=True, null=True, verbose_name='강수 확률(%)')

    class Meta:
        managed = False
        db_table = 'WEATHERCACHE'
        unique_together = (('weather_condition', 'region'),)
        verbose_name = '날씨 캐시'
        verbose_name_plural = '날씨 캐시 목록'

    def __str__(self):
        return f"{self.region.region_name} - {self.forecast_date} ({self.weather_condition})"


# ==============================================================================
# 6. 즐겨찾기 (FAVORITE)
# ==============================================================================
class Favorite(models.Model):
    fav_code = models.CharField(db_column='FAV_CODE', primary_key=True, max_length=20, verbose_name='즐겨찾기 코드')
    user = models.ForeignKey(Users, on_delete=models.DO_NOTHING, db_column='USER_ID', verbose_name='회원')
    spot = models.ForeignKey(TouristSpot, on_delete=models.DO_NOTHING, db_column='SPOT_CODE', verbose_name='관광지')

    class Meta:
        managed = False
        db_table = 'FAVORITE'
        verbose_name = '즐겨찾기'
        verbose_name_plural = '즐겨찾기 목록'

    def __str__(self):
        return f"{self.user.nickname} - {self.spot.t_name}"


# ==============================================================================
# 7. 후기 (REVIEW)
# ==============================================================================
class Review(models.Model):
    review_code = models.CharField(db_column='REVIEW_CODE', primary_key=True, max_length=20, verbose_name='후기 코드')
    user = models.ForeignKey(Users, on_delete=models.DO_NOTHING, db_column='USER_ID', verbose_name='작성 회원')
    spot = models.ForeignKey(TouristSpot, on_delete=models.DO_NOTHING, db_column='SPOT_CODE', verbose_name='관광지')
    rating = models.IntegerField(db_column='RATING', verbose_name='평점')
    create_date = models.DateTimeField(db_column='CREATE_DATE', verbose_name='작성 일시')
    content = models.CharField(db_column='CONTENT', max_length=255, blank=True, null=True, verbose_name='후기 내용')

    class Meta:
        managed = False
        db_table = 'REVIEW'
        verbose_name = '후기'
        verbose_name_plural = '후기 목록'

    def __str__(self):
        return f"{self.spot.t_name} 후기 - {self.user.nickname} ({self.rating}점)"


# ==============================================================================
# 8. 여행 일정 (ITINERARY)
# ==============================================================================
class Itinerary(models.Model):
    itinerary_code = models.CharField(db_column='ITINERARY_CODE', primary_key=True, max_length=20, verbose_name='일정 코드')
    user = models.ForeignKey(Users, on_delete=models.DO_NOTHING, db_column='USER_ID', verbose_name='회원')
    spot = models.ForeignKey(TouristSpot, on_delete=models.DO_NOTHING, db_column='SPOT_CODE', verbose_name='관광지')
    itinerary_title = models.CharField(db_column='ITINERARY_TITLE', max_length=255, blank=True, null=True, verbose_name='일정 제목')
    itinerary_date = models.DateField(db_column='ITINERARY_DATE', verbose_name='일정 일자')
    pet_accompanied = models.BooleanField(db_column='PET_ACCOMPANIED', verbose_name='반려동물 동반 여부')
    memo = models.CharField(db_column='MEMO', max_length=255, blank=True, null=True, verbose_name='메모')

    class Meta:
        managed = False
        db_table = 'ITINERARY'
        verbose_name = '여행 일정'
        verbose_name_plural = '여행 일정 목록'

    def __str__(self):
        return f"{self.itinerary_title or self.itinerary_code} ({self.user.nickname})"


# ==============================================================================
# 하위 호환성 별칭 (Alias)
# ==============================================================================
Touristspot = TouristSpot
Weathercache = WeatherCache