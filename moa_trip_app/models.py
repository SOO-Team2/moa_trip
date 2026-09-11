from django.db import models


# ===== 회원 =====
class Users(models.Model):
    user_id = models.CharField(max_length=20, primary_key=True, db_column='USER_ID')
    nickname = models.CharField(max_length=20, db_column='NICKNAME')
    email = models.CharField(max_length=255, db_column='EMAIL')
    pw = models.CharField(max_length=255, db_column='PW')
    join_date = models.DateField(db_column='JOIN_DATE')

    class Meta:
        db_table = 'USERS'

    def __str__(self):
        return self.nickname
    
# ===== 지역 =====
class Region(models.Model):
    region_code = models.CharField(max_length=20, primary_key=True, db_column='REGION_CODE')
    region_name = models.CharField(max_length=255, db_column='REGION_NAME')

    class Meta:
        db_table = 'REGION'

    def __str__(self):
        return self.region_name

# ===== 관광지 =====
class TouristSpot(models.Model):
    spot_code = models.CharField(max_length=20, primary_key=True, db_column='SPOT_CODE')
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, db_column='REGION_CODE'
    )
    t_name = models.CharField(max_length=255, db_column='T_NAME')
    address = models.CharField(max_length=255, db_column='ADDRESS')
    category = models.CharField(max_length=20, null=True, blank=True, db_column='CATEGORY')
    entry_fee = models.IntegerField(db_column='ENTRY_FEE')
    parking_info = models.CharField(max_length=20, null=True, blank=True, db_column='PARKING_INFO')
    operating_hours = models.CharField(max_length=20, null=True, blank=True, db_column='OPERATING_HOURS')
    phone = models.CharField(max_length=20, null=True, blank=True, db_column='PHONE')
    pet_allowed = models.BooleanField(db_column='PET_ALLOWED')

    class Meta:
        db_table = 'TOURISTSPOT'

    def __str__(self):
        return self.t_name

# ===== 축제 =====
class Festival(models.Model):
    festival_id = models.CharField(max_length=20, primary_key=True, db_column='FESTIVAL_ID')
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, db_column='REGION_CODE'
    )
    festival_name = models.CharField(max_length=255, db_column='FESTIVAL_NAME')
    start_date = models.DateField(db_column='START_DATE')
    end_date = models.DateField(db_column='END_DATE')
    festival_location = models.CharField(max_length=255, null=True, blank=True, db_column='FESTIVAL_LOCATION')

    class Meta:
        db_table = 'FESTIVAL'

    def __str__(self):
        return self.festival_name

# ===== 여행일정 =====
class Itinerary(models.Model):
    itinerary_code = models.CharField(max_length=20, primary_key=True, db_column='ITINERARY_CODE')
    user = models.ForeignKey(
        Users, on_delete=models.CASCADE, db_column='USER_ID'
    )
    spot = models.ForeignKey(
        TouristSpot, on_delete=models.CASCADE, db_column='SPOT_CODE'
    )
    itinerary_title = models.CharField(max_length=255, null=True, blank=True, db_column='ITINERARY_TITLE')
    itinerary_date = models.DateField(db_column='ITINERARY_DATE')
    pet_accompanied = models.BooleanField(db_column='PET_ACCOMPANIED')
    memo = models.CharField(max_length=255, null=True, blank=True, db_column='MEMO')

    class Meta:
        db_table = 'ITINERARY'

    def __str__(self):
        return self.itinerary_title or self.itinerary_code

# ===== 즐겨찾기 =====
class Favorite(models.Model):
    fav_code = models.CharField(max_length=20, primary_key=True, db_column='FAV_CODE')
    user = models.ForeignKey(
        Users, on_delete=models.CASCADE, db_column='USER_ID'
    )
    spot = models.ForeignKey(
        TouristSpot, on_delete=models.CASCADE, db_column='SPOT_CODE'
    )

    class Meta:
        db_table = 'FAVORITE'

# ===== 후기 =====
class Review(models.Model):
    review_code = models.CharField(max_length=20, primary_key=True, db_column='REVIEW_CODE')
    user = models.ForeignKey(
        Users, on_delete=models.CASCADE, db_column='USER_ID'
    )
    spot = models.ForeignKey(
        TouristSpot, on_delete=models.CASCADE, db_column='SPOT_CODE'
    )
    rating = models.DecimalField(max_digits=4, decimal_places=1, db_column='RATING')
    create_date = models.DateField(db_column='CREATE_DATE')
    content = models.CharField(max_length=255, null=True, blank=True, db_column='CONTENT')

    class Meta:
        db_table = 'REVIEW'

    def __str__(self):
        return f"{self.spot_id} · {self.rating}"

# ===== 날씨캐시 =====
class WeatherCache(models.Model):
    # 이미지 상 PK가 WEATHER_CONDITION으로 표시됨 — 의도 확인 필요 (위 참고 참조)
    weather_condition = models.CharField(max_length=20, primary_key=True, db_column='WEATHER_CONDITION')
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE, db_column='REGION_CODE'
    )
    forecast_date = models.DateField(db_column='FORECAST_DATE')
    temp_high = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, db_column='TEMP_HIGH')
    precip_pct = models.IntegerField(null=True, blank=True, db_column='PRECIP_PCT')

    class Meta:
        db_table = 'WEATHERCACHE'