import re
from django.db import models
from .utils import short_address, fetch_public_data, api_items
from .constants import REGIONS_DB, REGION_KEYWORDS


# ==============================================================================
# 1. 회원 (USERS)
# ==============================================================================
class Users(models.Model):
    user_id = models.CharField(db_column='USER_ID', primary_key=True, max_length=20, verbose_name='회원 ID')
    nickname = models.CharField(db_column='NICKNAME', max_length=20, verbose_name='닉네임')
    email = models.CharField(db_column='EMAIL', max_length=255, verbose_name='이메일')
    pw = models.CharField(db_column='PW', max_length=255, verbose_name='비밀번호')
    join_date = models.DateField(db_column='JOIN_DATE', blank=True, null=True, verbose_name='가입일자')
    status = models.CharField(db_column='STATUS', max_length=20, default='정상', verbose_name='회원 상태') # 상태 컬럼 추가

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
class TouristSpotManager(models.Manager):
    def _fetch_fee_and_pet(self, spot_code):
        # 1. detailPetTour2 (반려동물 정보 전용 API)
        pet_raw = fetch_public_data(
            "http://apis.data.go.kr/B551011/KorPetTourService2/detailPetTour2",
            extra_params={"contentId": str(spot_code)}
        )
        p_items = api_items(pet_raw)
        pet = p_items[0] if p_items else {}

        # 2. detailIntro2 (소개 정보)
        intro_raw = fetch_public_data(
            "http://apis.data.go.kr/B551011/KorService2/detailIntro2",
            extra_params={"contentId": str(spot_code), "contentTypeId": "12"}
        )
        i_items = api_items(intro_raw)
        intro = i_items[0] if i_items else {}

        # 3. detailInfo2 (usefee 없을 때 반복 정보 조회)
        raw_fee = intro.get('usefee') or intro.get('usefeeleports') or ''
        if not raw_fee:
            info_raw = fetch_public_data(
                "http://apis.data.go.kr/B551011/KorService2/detailInfo2",
                extra_params={"contentId": str(spot_code), "contentTypeId": "12"}
            )
            for r in api_items(info_raw):
                iname = (r.get('infoname') or '').replace(' ', '')
                itext = (r.get('infotext') or '').strip()
                if any(w in iname for w in ['입장료', '관람료', '이용요금', '이용료', '체험료', '요금']):
                    if itext:
                        raw_fee = itext
                        break

        # 반려동물 동반 가능 여부 (detailPetTour2 정보 우선 -> intro의 chkpet 판별)
        pet_need = (pet.get('acmpyNeedMtr') or '').strip()
        pet_etc = (pet.get('etcAcmpyInfo') or '').strip()
        pet_type = (pet.get('acmpyTypeCd') or '').strip()
        pet_cpam = (pet.get('acmpyPsblCpam') or '').strip()
        chk_pet = (intro.get('chkpet') or '').strip()
        is_pet = 1 if (pet_need or pet_etc or pet_type or pet_cpam or any(k in chk_pet for k in ['가능', '허용', '목줄', '케이지'])) else 0

        # 입장료 숫자 추출 (무료 또는 미등록 시 0)
        fee_num = 0
        if raw_fee:
            m = re.search(r'([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)\s*원', raw_fee)
            if m:
                try:
                    fee_num = int(m.group(1).replace(',', ''))
                except ValueError:
                    fee_num = 0

        return fee_num, is_pet

    def insert_from_api(self, spot_code):
        # API에서 관광지 정보를 가져와 DB에 없으면 등록
        # DB에 이미 존재
        spot = self.filter(spot_code=spot_code).select_related('region').first()
        if spot:
            updates = []
            # 기존 데이터에 이미지가 비어있는 경우 API에서 보충
            if not spot.image or not spot.image.name:
                raw = fetch_public_data(
                    "http://apis.data.go.kr/B551011/KorService2/detailCommon2",
                    extra_params={"contentId": str(spot_code)}
                )
                items = api_items(raw)
                if items and items[0].get('firstimage'):
                    spot.image = items[0]['firstimage']
                    updates.append('image')
            if updates:
                spot.save(update_fields=updates)
            return spot

        # 공공데이터 API 조회
        raw = fetch_public_data(
            "http://apis.data.go.kr/B551011/KorService2/detailCommon2",
            extra_params={"contentId": str(spot_code)}
        )
        items = api_items(raw)
        item = items[0] if items else None
        if not item or not item.get('title'):
            return None

        # 지역 코드 매핑
        region_code = REGIONS_DB.get(str(item.get('areacode')))
        if not region_code:
            addr1 = item.get('addr1') or ''
            for keyword, code in REGION_KEYWORDS:
                if keyword in addr1:
                    region_code = code
                    break

        region = Region.objects.filter(region_code=region_code).first()
        if not region:
            return None

        # 입장료 및 반려동물 상세 정보 조회
        entry_fee, pet_allowed = self._fetch_fee_and_pet(spot_code)

        # DB에 새로 등록
        return self.create(
            spot_code=spot_code,
            region=region,
            t_name=item.get('title'),
            address=item.get('addr1') or '주소 정보 없음',
            entry_fee=entry_fee,
            pet_allowed=pet_allowed,
            image=item.get('firstimage') or None,
        )


class TouristSpot(models.Model):
    spot_code = models.CharField(db_column='SPOT_CODE', primary_key=True, max_length=20, verbose_name='관광지 코드')
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column='REGION_CODE', verbose_name='지역')
    t_name = models.CharField(db_column='T_NAME', max_length=255, verbose_name='관광지명')
    address = models.CharField(db_column='ADDRESS', max_length=255, verbose_name='주소')
    entry_fee = models.IntegerField(db_column='ENTRY_FEE', verbose_name='입장료')
    pet_allowed = models.IntegerField(db_column='PET_ALLOWED', verbose_name='반려동물 동반 가능 여부')
    image = models.ImageField(db_column='IMAGE', upload_to='tourist_spots/', blank=True, null=True, verbose_name='이미지') # 이미지 컬럼 추가

    objects = TouristSpotManager()

    class Meta:
        managed = False
        db_table = 'TOURISTSPOT'
        verbose_name = '관광지'
        verbose_name_plural = '관광지 목록'

    def __str__(self):
        return self.t_name

    @property #함수를 변수처럼 사용
    def short_address(self):
        return short_address(self.address, default='주소 정보 준비 중')


# ==============================================================================
# 5. 날씨 캐시 (WEATHERCACHE)
# * 실제 DB 복합 PK (WEATHER_CONDITION, REGION_CODE) -> Django 단일 PK + unique_together 처리
# ==============================================================================
class WeatherCache(models.Model):
    weather_condition = models.CharField(db_column='WEATHER_CONDITION', max_length=20, verbose_name='기상 상태')
    region = models.ForeignKey(Region, on_delete=models.DO_NOTHING, db_column='REGION_CODE', verbose_name='지역')
    forecast_date = models.DateField(db_column='FORECAST_DATE', verbose_name='예보 날짜')
    temp_high = models.IntegerField(db_column='TEMP_HIGH', blank=True, null=True, verbose_name='최고 기온')
    precip_pct = models.IntegerField(db_column='PRECIP_PCT', blank=True, null=True, verbose_name='강수 확률(%)')

    class Meta:
        managed = False
        db_table = 'WEATHERCACHE'
        unique_together = (('region', 'forecast_date'),)
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
    itinerary_title = models.CharField(db_column='ITINERARY_TITLE', max_length=255, blank=True, null=True, verbose_name='일정 제목')
    itinerary_date = models.DateField(db_column='ITINERARY_DATE', verbose_name='일정 일자')
    companion = models.CharField(db_column='COMPANION', max_length=20, blank=True, null=True, verbose_name='동행') # 동행 컬럼 추가
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
# 9. 일정 방문 시간 (ITINERARY_TIME) - ITINERARY의 자식 테이블
# ==============================================================================
class ItineraryTime(models.Model):
    itinerary_time_id = models.AutoField(db_column='ITINERARY_TIME_ID', primary_key=True, verbose_name='방문 시간 ID')
    itinerary = models.ForeignKey(Itinerary, on_delete=models.DO_NOTHING, db_column='ITINERARY_CODE', verbose_name='일정')
    spot = models.ForeignKey(TouristSpot, on_delete=models.DO_NOTHING, db_column='SPOT_CODE', verbose_name='관광지')
    visit_time = models.CharField(db_column='VISIT_TIME', max_length=5, blank=True, null=True, verbose_name='방문 시간')

    class Meta:
        managed = False
        db_table = 'ITINERARY_TIME'
        verbose_name = '방문 시간'
        verbose_name_plural = '방문 시간 목록'

    def __str__(self):
        return f"{self.itinerary.itinerary_code} - {self.visit_time}"