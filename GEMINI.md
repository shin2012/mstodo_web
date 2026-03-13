# GEMINI.md - MSTodo Web Project Context

이 파일은 MSTodo Web 프로젝트의 핵심 정보와 아키텍처를 정리하여, Gemini가 프로젝트의 컨텍스트를 지속적으로 유지할 수 있도록 돕습니다.

## 1. 프로젝트 개요
- **목적**: Microsoft To-Do API와 연동하여 웹 브라우저에서 할 일을 확인하고 관리하는 서비스.
- **주요 기능**:
  - Microsoft Entra ID(Azure AD)를 통한 OAuth2 인증.
  - 할 일 목록(Lists) 및 개별 할 일(Tasks) 조회.
  - 새 할 일 추가 및 완료 처리.
  - Docker 및 Gunicorn을 이용한 배포 지원.

## 2. 기술 스택
- **Backend**: Python 3.11, Flask
- **Frontend**: HTML/JS (Vanilla), CSS
- **Library**: `pymstodo` (Microsoft Graph API 래퍼)
- **Deployment**: Docker, Docker Compose, Gunicorn
- **Proxy**: Nginx Proxy Manager (NPM) 대응 (`ProxyFix` 사용)

## 3. 핵심 아키텍처 및 로직
- **인증 흐름**: 
  1. `/auth/login`에서 Microsoft 로그인 페이지로 리다이렉트.
  2. `/auth/callback`에서 인증 코드를 받아 토큰으로 교환 후 `config.ini`에 저장.
- **API 연동**: `ToDoConnection` 클래스를 통해 Microsoft Graph API와 통신합니다.
- **데이터 업데이트 방식**: 기존의 자동 리프레시(Timer) 기능을 제거하고, 사용자가 명시적으로 클릭할 수 있는 **수동 '업데이트' 버튼**으로 대체하여 불필요한 API 호출을 줄이고 사용자 제어권을 높였습니다.
- **서브태스크 지원**: Microsoft To-Do의 체크리스트(checklistItems)를 할 일 카드 내에 표시합니다. Batch API 호출 시 `$expand=checklistItems`를 사용하여 한 번에 데이터를 가져옵니다.
- **Optimistic UI**: 서브태스크 완료 처리 시, 서버 응답 전 UI를 먼저 변경(취소선 적용 등)하여 즉각적인 피드백을 제공하고, 실패 시에만 원복하는 방식을 취합니다.
- **전체 할 일 그룹화**: '전체 할 일' 조회 시, 백엔드에서 리스트 이름(`list_name`)으로 1차 정렬하고 프론트엔드에서 리스트가 바뀔 때마다 헤더를 삽입하여 목록별로 그룹화해서 보여줍니다.
- **날짜 및 시간 처리**: Microsoft API에서 제공하는 UTC 시간을 백엔드(`app.py`)에서 한국 표준시(KST, UTC+9)로 변환하여 프론트엔드에 전달합니다. 프론트엔드에서는 시차 오해 없이 `YYYY-MM-DD` 형식으로 데이터를 처리합니다.
- **UI 강조 규칙**:
  - **중요(별표)**: 노란색(`amber-400`) 배경 및 굵은 테두리 (최우선)
  - **기한 지남**: 빨간색(`rose-400`) 배경 및 2px 테두리
  - **오늘**: 초록색(`emerald-400`) 배경 및 2px 테두리
  - **내일**: 파란색(`blue-400`) 배경 및 2px 테두리
  - **이번 주**: 옅은 파란색(`sky-300`) 테두리
- **성능 최적화**: `ThreadPoolExecutor`를 사용하여 여러 할 일 목록을 병렬로 가져옵니다.

## 4. 주요 파일 구조
- `app.py`: Flask 애플리케이션의 메인 로직 및 API 엔드포인트.
- `templates/`: 사용자 인터페이스(HTML).
- `config.ini`: 애플리케이션 설정 및 인증 토큰 저장.
- `Dockerfile` / `docker-compose.yml`: 컨테이너 빌드 및 실행 설정.

## 5. 개발 및 운영 지침
- **인증 오류 발생 시**: `config.ini`의 `client_token`이 유효한지 확인하거나, `/settings` 페이지에서 ID/Secret 설정을 점검하십시오.
- **날짜 표시**: 백엔드에서 `kst_dt = dt + timedelta(hours=9)` 로직을 통해 보정된 날짜를 사용합니다.
- **Proxy 대응**: `werkzeug.middleware.proxy_fix.ProxyFix`를 적용하여 리버스 프록시 환경에서도 리다이렉트 URI가 올바르게 생성되도록 합니다.
