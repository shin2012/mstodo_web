# Microsoft To-Do 웹 서비스 (MSTodo Web)

Microsoft To-Do와 연동하여 웹 브라우저에서 할 일을 확인하고 관리할 수 있는 서비스입니다. Flask 기반으로 구축되었으며 Docker를 통해 간편하게 배포할 수 있습니다.

## 🚀 주요 개선 사항 (최근 업데이트)
- **리스트 그룹화 및 드래그 앤 드롭**: 스마트 사이드바에서 그룹을 생성하고 리스트를 자유롭게 배치할 수 있는 기능을 추가했습니다. 그룹의 접기/펼치기 상태와 순서는 `list_groups.json`에 저장되어 영구적으로 유지됩니다.
- **스마트 기한 관리 및 전용 팝업**: 태스크 기한을 `YYYY-MM-DD (요일)` 형식으로 시각화하고, 전용 팝업을 통해 달력 선택 및 기한 삭제를 직관적으로 수행할 수 있도록 개선했습니다.
- **실시간 제목 편집**: 태스크와 서브태스크 제목을 별도의 창 이동 없이 목록에서 직접 클릭하여 실시간으로 수정할 수 있는 인라인 편집 기능을 도입했습니다.
- **컴팩트 레이아웃 최적화**: 태스크 카드의 높이를 조절하고 불필요한 정보를 제거하여, 한 화면에서 더 많은 할 일을 명확하게 확인할 수 있도록 레이아웃을 최적화했습니다.
- **로그인 상태 유지 (Persistent Login)**: `offline_access` 권한을 요청하고 `refresh_token`을 사용하여 토큰 만료 시 자동으로 갱신하도록 개선했습니다. 이제 매시간 다시 로그인할 필요가 없습니다.
- **완료된 할 일 관리 및 정렬**: 
  - 완료된 할 일 목록의 폴딩(접기/펴기) 상태가 브라우저에 저장되어 재방문 시에도 유지됩니다.
  - 완료된 항목은 **최근 완료 시간 순**으로 정렬되어 작업 내역 확인이 용이합니다.
- **모던 UI/UX 디자인**: 
  - **Pretendard 폰트**: 한국어 가독성에 최적화된 Pretendard 가변 폰트 전역 적용.
  - **다이내믹 배경**: Mesh Gradient 스타일의 블롭 애니메이션 효과를 강화하여 세련된 디자인 제공.
  - **파비콘 업데이트**: 서비스 로고와 통일감을 주는 새로운 파비콘 적용.
  - **사용자 편의성**: 직관적인 아이콘과 Glassmorphism 효과를 적절히 배합하여 시각적 완성도를 높였습니다.

## ✨ 주요 기능
- **웹 인터페이스**: 브라우저를 통해 실시간으로 Microsoft To-Do 할 일 목록 확인 및 관리.
- **반응형 디자인**: PC와 모바일 모두에 최적화된 화면 구성.
- **서브태스크 관리**: 각 할 일에 포함된 체크리스트(서브태스크)를 조회하고 즉시 완료/해제 처리 가능.
- **수동 업데이트**: '업데이트' 버튼을 통한 명시적인 데이터 동기화 기능.
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
