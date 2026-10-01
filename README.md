# 📋 Microsoft To-Do 웹 서비스 (MSTodo Web)

<div align="center">

[![Python Version](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-green?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)](.)

Microsoft To-Do와 연동하여 웹 브라우저에서 할 일을 확인하고 관리할 수 있는 서비스입니다.
Flask 기반으로 구축되었으며 Docker를 통해 간편하게 배포할 수 있습니다.

</div>

---

## 🚀 주요 개선 사항 (최신 업데이트)

### 스마트한 목록 관리
- **🎯 리스트 그룹화 및 드래그 앤 드롭**: 스마트 사이드바에서 그룹을 생성하고 리스트를 자유롭게 배치 가능
- **💾 영구 저장**: 그룹의 접기/펼치기 상태와 순서는 `list_groups.json`에 저장되어 영구적으로 유지

### 효율적인 기한 관리
- **📅 스마트 기한 관리**: 태스크 기한을 `YYYY-MM-DD (요일)` 형식으로 시각화
- **🎨 전용 팝업**: 달력 선택 및 기한 삭제를 직관적으로 수행

### 빠른 편집
- **⚡ 실시간 제목 편집**: 태스크와 서브태스크 제목을 목록에서 직접 클릭하여 실시간 수정 가능 (인라인 편집)

### 최적화된 UI/UX
- **🎪 컴팩트 레이아웃**: 태스크 카드 높이 조절로 한 화면에서 더 많은 할 일 확인
- **🔤 Pretendard 폰트**: 한국어 가독성에 최적화된 가변 폰트 전역 적용
- **🌈 다이내믹 배경**: Mesh Gradient 스타일의 블롭 애니메이션 효과
- **📱 파비콘 업데이트**: 서비스 로고와 통일감을 주는 새로운 파비콘

### 로그인 편의성
- **🔐 로그인 상태 유지**: `offline_access` 권한과 `refresh_token` 사용으로 자동 갱신 (매시간 재로그인 불필요!)

### 작업 이력 관리
- **✅ 완료된 할 일 관리**:
  - 완료된 할 일 목록의 폴딩(접기/펴기) 상태가 브라우저에 저장되어 재방문 시에도 유지
  - 완료된 항목은 **최근 완료 시간 순**으로 정렬되어 작업 내역 확인 용이

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 🌐 **웹 인터페이스** | 브라우저를 통해 실시간으로 Microsoft To-Do 할 일 목록 확인 및 관리 |
| 📱 **반응형 디자인** | PC와 모바일 모두에 최적화된 화면 구성 |
| ✔️ **서브태스크 관리** | 각 할 일에 포함된 체크리스트(서브태스크)를 조회하고 즉시 완료/해제 처리 |
| 🔄 **수동 업데이트** | '업데이트' 버튼을 통한 명시적인 데이터 동기화 기능 |
| 🐳 **Docker 기반** | Docker 및 Docker Compose를 사용하여 환경 격리 및 간편한 배포 |
| 🔒 **안정적인 서버** | Gunicorn을 사용한 웹 서버 환경 제공 |

---

## 🛠 기술 스택

<details>
<summary><b>백엔드 & 프론트엔드 스택 (클릭하여 펼치기)</b></summary>

### 백엔드
- **언어**: Python 3.11
- **프레임워크**: Flask
- **병렬 처리**: Concurrent Futures
- **API 래퍼**: `pymstodo` (Microsoft Graph API)

### 프론트엔드
- **마크업**: HTML5
- **스크립트**: Vanilla JavaScript
- **스타일**: TailwindCSS
- **아이콘**: FontAwesome 6
- **폰트**: Pretendard (한국어 최적화)

### 배포 & 인프라
- **WSGI 서버**: Gunicorn
- **컨테이너화**: Docker, Docker Compose
- **리버스 프록시**: Nginx Proxy Manager (선택사항)

</details>

---

## 🔑 Azure AD (Entra ID) 설정

이 앱을 사용하려면 [Microsoft Entra 관리 센터](https://portal.azure.com/)에서 앱을 등록해야 합니다.

<details>
<summary><b>단계별 설정 가이드 (클릭하여 펼치기)</b></summary>

### 1단계: 앱 등록
- **Microsoft Entra 관리 센터** > **앱 등록(App registrations)** 메뉴에서 새 등록 진행

### 2단계: 인증(Authentication) 설정
- **플랫폼 추가** → **웹** 선택
- **Redirect URI**에 다음 주소를 추가:
  - **도메인 사용 시**: `https://domain.com/auth/callback`
  - **로컬 테스트 시**: `http://localhost:5001/auth/callback`
  
  > ⚠️ **중요**: 이 주소는 브라우저에서 접속하는 실제 주소와 정확히 일치해야 합니다.

### 3단계: API 권한(API permissions) 설정
필요한 권한 추가 후 관리자 동의 부여:
- `Tasks.ReadWrite` — 할 일 읽기 및 쓰기
- `offline_access` — 오프라인 액세스 (토큰 자동 갱신)
- `openid` — OpenID Connect

### 4단계: 인증서 및 암호 생성
- **인증서 및 암호** 메뉴에서 새로운 클라이언트 암호(Client Secret) 생성
- 생성된 값을 복사해두기 (이후 접속 불가능하므로 꼭 저장!)

</details>

---

## ⚙️ 설치 및 실행

### 사전 준비
- ✅ Docker가 설치되어 있어야 합니다
- ✅ Docker Compose가 설치되어 있어야 합니다
- ✅ Azure AD에서 앱이 등록되어 있어야 합니다

### 빠른 시작

<details>
<summary><b>Docker Compose를 사용한 배포 (권장) (클릭하여 펼치기)</b></summary>

#### 1단계: 저장소 클론
```bash
git clone https://github.com/shin2012/mstodo_web.git
cd mstodo_web
```

#### 2단계: 환경 변수 설정
다음 중 **하나**를 선택하여 설정하세요:

**방법 A: `docker-compose.yml` 직접 수정 (권장)**
```yaml
environment:
  - TZ=Asia/Seoul
  - MS_CLIENT_ID=your_client_id_here
  - MS_CLIENT_SECRET=your_client_secret_here
```

**방법 B: `config.ini` 파일 사용**
```ini
[connect]
client_id = your_client_id_here
client_secret = your_client_secret_here
```

#### 3단계: 서비스 시작
```bash
docker-compose up -d --build
```

#### 4단계: 접속
브라우저에서 다음 주소로 접속:
- **로컬 테스트**: `http://localhost:5001`
- **도메인 사용**: `https://domain.com` (Nginx Proxy Manager 설정 후)

</details>

---

## 🎮 운영 명령어

<details>
<summary><b>Docker 관리 명령어 (클릭하여 펼치기)</b></summary>

```bash
# 서비스 상태 확인
docker-compose ps

# 실시간 로그 확인
docker-compose logs -f

# 컨테이너만 재시작
docker-compose restart mstodo_web

# 전체 서비스 중지 및 제거
docker-compose down

# 서비스 중지만 하기 (컨테이너 유지)
docker-compose stop

# 서비스 재개
docker-compose start
```

</details>

---

## 🔌 Nginx Proxy Manager (NPM) 설정

HTTPS를 사용하여 외부에서 접속하는 경우, Nginx Proxy Manager에서 다음과 같이 설정하세요:

<details>
<summary><b>NPM 설정 상세 (클릭하여 펼치기)</b></summary>

| 설정 항목 | 값 |
|----------|-----|
| **Scheme** | `http` |
| **Forward HostName / IP** | 호스트 서버의 IP (예: `10.0.0.2`) |
| **Forward Port** | `5001` |
| **Block Common Exploits** | ✅ 활성화 |
| **Websockets Support** | ✅ 활성화 |
| **Custom Nginx Configuration** | (아래 참고) |

#### 선택사항: Custom Nginx Configuration
특정 헤더 처리가 필요한 경우:
```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

</details>

---

## 📂 프로젝트 구조

```
mstodo_web/
├── app.py                 # Flask 메인 애플리케이션
├── sync_worker.py         # 백그라운드 동기화 워커
├── database.py            # 데이터베이스 관리
├── requirements.txt       # Python 의존성
├── Dockerfile             # Docker 이미지 정의
├── docker-compose.yml     # Docker Compose 설정
├── config.ini             # 설정 파일 (환경변수로도 가능)
├── templates/             # HTML 템플릿
│   └── index.html         # 메인 UI
├── static/                # CSS, JavaScript, 이미지
│   ├── css/               # 스타일 파일
│   ├── js/                # 스크립트 파일
│   └── img/               # 이미지 및 파비콘
└── README.md              # 이 파일
```

---

## 🐛 문제 해결

<details>
<summary><b>자주 묻는 질문 & 해결방법 (클릭하여 펼치기)</b></summary>

### Q1: "Redirect URI mismatch" 오류가 발생합니다
**A:** Azure AD의 Redirect URI 설정을 확인하세요. 브라우저에서 실제로 접속하는 주소와 정확히 일치해야 합니다.
- 로컬: `http://localhost:5001/auth/callback`
- HTTPS 도메인: `https://domain.com/auth/callback`

### Q2: "로그인 후에도 할 일 목록이 표시되지 않습니다"
**A:** 다음을 확인하세요:
1. Azure AD에서 `Tasks.ReadWrite` 권한이 부여되었는지 확인
2. 관리자 동의(Admin consent)가 완료되었는지 확인
3. 도커 로그를 확인: `docker-compose logs -f`

### Q3: "Container이 자꾸만 재시작됩니다"
**A:** 로그를 확인하세요: `docker-compose logs -f`
- 환경 변수 설정 누락 확인
- Python 의존성 설치 실패 확인

### Q4: "모바일 앱에서도 작업이 동기화되나요?"
**A:** 네! 이 웹 서비스는 Microsoft Graph API를 통해 동기화하므로, Microsoft To-Do 공식 앱과 자동으로 동기화됩니다.

</details>

---

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포할 수 있습니다.

---

## 🤝 기여 방법

버그 리포트나 기능 제안은 GitHub Issues를 통해 제출해주세요!

```bash
# 로컬에서 개발하고 싶다면:
git clone https://github.com/shin2012/mstodo_web.git
cd mstodo_web

# 가상 환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 로컬 개발 서버 실행 (자동 재로드)
flask run --debug
```

---

<div align="center">

Made with ❤️ by the MSTodo Web Team

**[GitHub](https://github.com/shin2012/mstodo_web)** · **[Issues](https://github.com/shin2012/mstodo_web/issues)**

</div>
