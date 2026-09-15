# 모아트립 (moa_trip)

여행 일정 및 관광 정보 공유 플랫폼 Django 웹 프로젝트입니다.

---

## 🛠 로컬 개발 환경 세팅 가이드

### 1. 가상환경 생성 및 활성화

프로젝트 루트 디렉토리에서 가상환경(`menv`)을 생성하고 활성화합니다.

#### Windows (PowerShell)
```powershell
# 가상환경 생성
python -m venv menv

# 가상환경 활성화
.\menv\Scripts\Activate.ps1
```

> **참고 (스크립트 실행 권한 오류 발생 시)**:
> PowerShell 관리자 권한으로 `Set-ExecutionPolicy RemoteSigned`를 실행하거나, 명령 프롬프트(CMD)에서 `.\menv\Scripts\activate.bat`을 사용하세요.

#### macOS / Linux
```bash
# 가상환경 생성
python3 -m venv menv

# 가상환경 활성화
source menv/bin/activate
```

---

### 2. 패키지 설치

팀 DB 서버(MariaDB) 버전 호환을 위해 Django는 **5.0 미만 버전**을 사용합니다.

```bash
# pip 업그레이드
python -m pip install --upgrade pip

# Django 4.x 설치
pip install "django<5"

# MySQL/MariaDB 드라이버 설치
pip install mysqlclient
```

> **드라이버 설치 실패 시 대처 (Windows 빌드 에러 등)**:
> `mysqlclient` 설치가 실패할 경우 `pymysql`로 대체할 수 있습니다.
> ```bash
> pip install pymysql
> ```
> `pymysql`을 사용할 경우, `moa_trip/__init__.py` 파일에 다음 코드를 추가합니다:
> ```python
> import pymysql
> pymysql.install_as_MySQLdb()
> ```

---

### 3. 데이터베이스 및 환경 설정 확인

`moa_trip/settings.py`의 설정값이 아래와 같이 구성되어 있는지 확인합니다:

```python
# Database 설정
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'moa_trip',
        'USER': 'SSO2026',
        'PASSWORD': 'SSO2026',
        'HOST': 'ubuntu-server.iptime.org',
        'PORT': '13306',
    }
}

# 언어 및 시간대
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
```

---

### 4. 마이그레이션 실행

데이터베이스 변경사항을 확인하고 마이그레이션을 적용합니다.

```bash
# 앱 마이그레이션 파일 생성
python manage.py makemigrations moa_trip_app

# DB에 마이그레이션 적용
python manage.py migrate
```

---

### 5. 개발 서버 실행

```bash
python manage.py runserver
```

브라우저에서 [http://127.0.0.1:8000/](http://127.0.0.1:8000/)으로 접속하여 메인 페이지를 확인합니다.

---

## 📂 프로젝트 구조

```text
moa_trip/
├── manage.py            # Django 실행 및 관리 스크립트
├── moa_trip/            # 프로젝트 전역 설정
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py      # 앱 및 DB 설정
│   ├── urls.py          # 루트 URL 라우팅
│   └── wsgi.py
├── moa_trip_app/        # 모아트립 메인 애플리케이션
│   ├── admin.py
│   ├── apps.py
│   ├── models.py        # DB 모델 정의
│   ├── templates/       # HTML 템플릿
│   │   └── main.html
│   ├── urls.py          # 앱 단위 라우팅
│   └── views.py         # 뷰 로직
└── .gitignore
```

---

## 🔍 문제 해결 (Troubleshooting)

1. **드라이버 에러**: `mysqlclient` 설치 시 C++ 컴파일러 오류가 나면 `pymysql` 대체 사용
2. **버전 호환성 문제**: MariaDB 버전과의 호환을 위해 반드시 `django<5` 유지
3. **DB 접속 타임아웃/연결 실패**: 원격 서버(`ubuntu-server.iptime.org:13306`) 접근 가능 여부 및 방화벽/네트워크 확인
