from django.db import models


class Region(models.Model):
    region_code = models.CharField(db_column='REGION_CODE', primary_key=True, max_length=20)
    region_name = models.CharField(db_column='REGION_NAME', max_length=255)

    class Meta:
        managed = False
        db_table = 'REGION'

    def __str__(self):
        return self.region_name


class Touristspot(models.Model):
    spot_code = models.CharField(db_column='SPOT_CODE', primary_key=True, max_length=20)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, db_column='REGION_CODE')
    t_name = models.CharField(db_column='T_NAME', max_length=255)
    address = models.CharField(db_column='ADDRESS', max_length=255)
    category = models.CharField(db_column='CATEGORY', max_length=20, blank=True, null=True)
    entry_fee = models.IntegerField(db_column='ENTRY_FEE')
    parking_info = models.CharField(db_column='PARKING_INFO', max_length=20, blank=True, null=True)
    operating_hours = models.CharField(db_column='OPERATING_HOURS', max_length=255)
    phone = models.CharField(db_column='PHONE', max_length=20)
    pet_allowed = models.IntegerField(db_column='PET_ALLOWED')

    class Meta:
        managed = False
        db_table = 'TOURISTSPOT'

    def __str__(self):
        return self.t_name


class Users(models.Model):
    user_id = models.CharField(db_column='USER_ID', primary_key=True, max_length=20)
    nickname = models.CharField(db_column='NICKNAME', max_length=20)
    email = models.CharField(db_column='EMAIL', max_length=255)
    pw = models.CharField(db_column='PW', max_length=20)
    join_date = models.DateField(db_column='JOIN_DATE', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'USERS'

    def __str__(self):
        return self.nickname


class Review(models.Model):
    review_code = models.CharField(db_column='REVIEW_CODE', primary_key=True, max_length=20)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='USER_ID')
    spot = models.ForeignKey(Touristspot, on_delete=models.CASCADE, db_column='SPOT_CODE')
    rating = models.IntegerField(db_column='RATING')
    create_date = models.DateTimeField(db_column='CREATE_DATE')
    content = models.CharField(db_column='CONTENT', max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'REVIEW'


class Favorite(models.Model):
    fav_code = models.CharField(db_column='FAV_CODE', primary_key=True, max_length=20)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='USER_ID')
    spot = models.ForeignKey(Touristspot, on_delete=models.CASCADE, db_column='SPOT_CODE')

    class Meta:
        managed = False
        db_table = 'FAVORITE'


class Itinerary(models.Model):
    itinerary_code = models.CharField(db_column='ITINERARY_CODE', primary_key=True, max_length=20)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, db_column='USER_ID')
    spot = models.ForeignKey(Touristspot, on_delete=models.CASCADE, db_column='SPOT_CODE')
    itinerary_title = models.CharField(db_column='ITINERARY_TITLE', max_length=255, blank=True, null=True)
    itinerary_date = models.DateField(db_column='ITINERARY_DATE')
    pet_accompanied = models.IntegerField(db_column='PET_ACCOMPANIED')
    memo = models.CharField(db_column='MEMO', max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'ITINERARY'


class Festival(models.Model):
    festival_id = models.CharField(db_column='FESTIVAL_ID', primary_key=True, max_length=20)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, db_column='REGION_CODE')
    festival_name = models.CharField(db_column='FESTIVAL_NAME', max_length=255)
    start_date = models.DateField(db_column='START_DATE')
    end_date = models.DateField(db_column='END_DATE')
    festival_location = models.CharField(db_column='FESTIVAL_LOCATION', max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'FESTIVAL'


class Weathercache(models.Model):
    weather_condition = models.CharField(db_column='WEATHER_CONDITION', primary_key=True, max_length=20)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, db_column='REGION_CODE')
    forecast_date = models.DateField(db_column='FORECAST_DATE')
    temp_high = models.IntegerField(db_column='TEMP_HIGH', blank=True, null=True)
    precip_pct = models.IntegerField(db_column='PRECIP_PCT', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'WEATHERCACHE'
        unique_together = (('weather_condition', 'region'),)