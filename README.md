# Microsoft To-Do 웹 서비스 (MSTodo Web)

Microsoft To-Do와 연동하여 웹 브라우저에서 할 일을 확인하고 관리할 수 있는 서비스입니다. Flask 기반으로 구축되었으며 Docker를 통해 간편하게 배포할 수 있습니다.

## 🚀 주요 개선 사항 (최근 업데이트)
- **UI/UX 강조 세분화**: 중요 작업(노란색 별표), 기한 지남(빨간색), 오늘(초록색), 내일(파란색), 이번 주(하늘색)로 테두리와 배경색을 세분화하여 시각적 인지도를 높였습니다.
- **완료 시간(KST) 보정**: Microsoft API의 UTC 시간을 한국 표준시(+9시간)로 정확히 변환하여 마감일 표시 오류를 해결했습니다.
- **모던 UI/UX 디자인**: 
  - **Pretendard 폰트**: 한국어 가독성에 최적화된 Pretendard 가변 폰트 적용.
  - **반응형 레이아웃**: 데스크탑 사이드바와 모바일 가로 스크롤 칩 메뉴 제공.
  - **감각적인 배경**: Mesh Gradient 스타일의 부드러운 애니메이션 배경과 Glassmorphism 효과 적용.
  - **사용자 편의성**: 초기 디자인의 여유로운 공간감(Spacious Layout)을 복원하여 쾌적한 사용 환경 제공.

## ✨ 주요 기능
- **웹 인터페이스**: 브라우저를 통해 실시간으로 Microsoft To-Do 할 일 목록 확인 및 관리.
- **반응형 디자인**: PC와 모바일 모두에 최적화된 화면 구성.
- **실시간 동기화**: 주기적인 자동 리프레시 기능(Refresh Timer)으로 최신 상태 유지.
- **Docker 기반**: Docker 및 Docker Compose를 사용하여 환경 격리 및 간편한 배포.
- **안정적인 서버**: Gunicorn을 사용하여 프로덕션급 웹 서버 환경 제공.

## 🛠 기술 스택
- **Backend**: Python 3.11, Flask, Concurrent Futures (병렬 처리)
- **Frontend**: HTML5, Vanilla JS, TailwindCSS, FontAwesome 6, Pretendard Font
- **WSGI 서버**: Gunicorn
- **API 연동**: `pymstodo` (Microsoft Graph API Wrapper)
- **컨테이너화**: Docker, Docker Compose

## Azure AD (Entra ID) 설정 및 Redirect URI 등록

이 앱을 사용하려면 [Microsoft Entra 관리 센터](https://portal.azure.com/)에서 앱을 등록해야 합니다.

1. **앱 등록**: '앱 등록(App registrations)' 메뉴에서 새 등록을 진행합니다.
2. **인증(Authentication) 설정**:
   - '플랫폼 추가' -> '웹'을 선택합니다.
   - **Redirect URI**에 다음 주소를 추가합니다:
     - `https://domain.com/auth/callback` (도메인 사용 시)
     - `http://localhost:5001/auth/callback` (로컬 테스트 시)
   - **중요**: 이 주소는 브라우저에서 접속하는 실제 주소와 정확히 일치해야 합니다.
3. **API 권한(API permissions)**:
   - `Tasks.ReadWrite`, `offline_access`, `openid` 권한을 추가하고 관리자 동의를 부여합니다.
4. **인증서 및 암호**:
   - 새로운 클라이언트 암호(Client Secret)를 생성하고 값을 복사해둡니다.

## 설치 및 실행 방법

### 사전 준비
- Docker 및 Docker Compose가 설치되어 있어야 합니다.

### 서비스 시작
1. 저장소를 클론합니다.
2. `docker-compose.yml`의 환경 변수나 `config.ini` 파일에 `MS_CLIENT_ID`와 `MS_CLIENT_SECRET`을 설정합니다.
3. 서비스를 빌드하고 시작합니다:
   ```bash
   docker-compose up -d --build
   ```
4. 브라우저에서 등록한 도메인(예: `https://domain.com`)으로 접속하여 로그인을 진행합니다.

## 운영 명령어
- **서비스 상태 확인**: `docker-compose ps`
- **로그 확인**: `docker-compose logs -f`
- **서비스 재시작**: `docker-compose restart mstodo_web`
- **서비스 중지**: `docker-compose down`

## Nginx Proxy Manager (NPM) 설정 (HTTPS 사용 시)
외부에서 HTTPS로 접속하는 경우 NPM에서 다음과 같이 설정하십시오:
- **Scheme**: `http`
- **Forward HostName / IP**: 호스트 서버의 IP (예: `10.0.0.2`)
- **Forward Port**: `5001`
- **Block Common Exploits**: On
- **Websockets Support**: On
- **Custom Nginx Configuration**:
  (필요한 경우 `X-Forwarded-Proto` 헤더가 올바르게 전달되는지 확인하십시오.)
