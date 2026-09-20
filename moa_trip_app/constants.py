# ==============================================================================
# 대한민국 지역 코드 통합 매핑 (TourAPI 기준)
# ==============================================================================

REGION_MASTER = {
    "1": {
        "name": "서울",
        "region_code": "R01",
        "land": "11B00000", #중기육상
        "temp": "11B10101", #중기기온
        "grid": (60, 127),
        "tel": "02-120",
    },
    "2": {
        "name": "인천",
        "region_code": "R02",
        "land": "11B00000",
        "temp": "11B20201",
        "grid": (55, 124),
        "tel": "032-120",
    },
    "31": {
        "name": "경기",
        "region_code": "R03",
        "land": "11B00000",
        "temp": "11B20601",
        "grid": (60, 120),
        "tel": "031-120",
    },
    "32": {
        "name": "강원",
        "region_code": "R04",
        "land": "11D10000",
        "temp": "11D10301",
        "grid": (73, 134),
        "tel": "033-120",
    },
    "33": {
        "name": "충북",
        "region_code": "R05",
        "land": "11C10000",
        "temp": "11C10301",
        "grid": (69, 107),
        "tel": "043-120",
    },
    "34": {
        "name": "충남",
        "region_code": "R06",
        "land": "11C20000",
        "temp": "11C20101",
        "grid": (68, 100),
        "tel": "041-120",
    },
    "3": {
        "name": "대전",
        "region_code": "R07",
        "land": "11C20000",
        "temp": "11C20401",
        "grid": (67, 100),
        "tel": "042-120",
    },
    "8": {
        "name": "세종",
        "region_code": "R08",
        "land": "11C20000",
        "temp": "11C20404",
        "grid": (66, 103),
        "tel": "044-120",
    },
    "37": {
        "name": "전북",
        "region_code": "R09",
        "land": "11F10000",
        "temp": "11F10201",
        "grid": (63, 89),
        "tel": "063-120",
    },
    "5": {
        "name": "광주",
        "region_code": "R10",
        "land": "11F20000",
        "temp": "11F20401",
        "grid": (58, 74),
        "tel": "062-120",
    },
    "38": {
        "name": "전남",
        "region_code": "R11",
        "land": "11F20000",
        "temp": "11F20501",
        "grid": (51, 67),
        "tel": "061-120",
    },
    "35": {
        "name": "경북",
        "region_code": "R12",
        "land": "11H10000",
        "temp": "11H10701",
        "grid": (89, 91),
        "tel": "054-120",
    },
    "4": {
        "name": "대구",
        "region_code": "R13",
        "land": "11H10000",
        "temp": "11H10201",
        "grid": (89, 90),
        "tel": "053-120",
    },
    "7": {
        "name": "울산",
        "region_code": "R14",
        "land": "11H20000",
        "temp": "11H20101",
        "grid": (102, 84),
        "tel": "052-120",
    },
    "6": {
        "name": "부산",
        "region_code": "R15",
        "land": "11H20000",
        "temp": "11H20201",
        "grid": (98, 76),
        "tel": "051-120",
    },
    "36": {
        "name": "경남",
        "region_code": "R16",
        "land": "11H20000",
        "temp": "11H20301",
        "grid": (90, 77),
        "tel": "055-120",
    },
    "39": {
        "name": "제주",
        "region_code": "R17",
        "land": "11G00000",
        "temp": "11G00201",
        "grid": (52, 38),
        "tel": "064-120",
    },
}

# 행정안전부/기상청 코드 호환
AREA_ALIASES = {
    "11": "1",   # 서울
    "23": "2",   # 인천
    "25": "3",   # 대전
    "22": "4",   # 대구
    "24": "5",   # 광주
    "21": "6",   # 부산
    "26": "7",   # 울산
    "51": "32",  # 강원
}

# 탐색 페이지 지역 필터
REGION_FILTERS = [
    {"code": "all", "name": "전체"},
    {"code": "1", "name": "서울"},
    {"code": "2", "name": "인천"},
    {"code": "31", "name": "경기"},
    {"code": "32", "name": "강원"},
    {"code": "33", "name": "충북"},
    {"code": "34", "name": "충남"},
    {"code": "3", "name": "대전"},
    {"code": "8", "name": "세종"},
    {"code": "37", "name": "전북"},
    {"code": "5", "name": "광주"},
    {"code": "38", "name": "전남"},
    {"code": "35", "name": "경북"},
    {"code": "4", "name": "대구"},
    {"code": "7", "name": "울산"},
    {"code": "6", "name": "부산"},
    {"code": "36", "name": "경남"},
    {"code": "39", "name": "제주"},
]

# TourAPI와 DB Region 매핑
REGIONS_DB = {
    code: info["region_code"] for code, info in REGION_MASTER.items()
}
for alias, real_code in AREA_ALIASES.items():
    REGIONS_DB[alias] = REGION_MASTER[real_code]["region_code"]

# areacode가 비어 있으면 주소에서 지역명을 찾아 매칭
REGION_KEYWORDS = [
    ("서울", "R01"), ("인천", "R02"), ("경기", "R03"), ("강원", "R04"),
    ("충청북도", "R05"), ("충북", "R05"), ("충청남도", "R06"), ("충남", "R06"),
    ("대전", "R07"), ("세종", "R08"),
    ("전라북도", "R09"), ("전북", "R09"), ("광주", "R10"),
    ("전라남도", "R11"), ("전남", "R11"),
    ("경상북도", "R12"), ("경북", "R12"), ("대구", "R13"), ("울산", "R14"), ("부산", "R15"),
    ("경상남도", "R16"), ("경남", "R16"), ("제주", "R17"),
]

def get_region(area_code):
    #지역 코드 통합 딕셔너리
    key = str(area_code or "").strip()
    norm_key = AREA_ALIASES.get(key, key) #구형과 신형 코드
    return REGION_MASTER.get(norm_key)