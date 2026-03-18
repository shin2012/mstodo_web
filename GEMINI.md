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
  1. `/auth/login`에서 `offline_access` 권한을 포함하여 Microsoft 로그인 페이지로 리다이렉트.
  2. `/auth/callback`에서 인증 코드를 받아 토큰으로 교환 후 `config.ini`에 저장.
  3. **토큰 자동 갱신**: `get_refreshed_token()` 로직을 통해 토큰 만료 전 `refresh_token`을 사용하여 자동으로 `access_token`을 갱신하고 `config.ini`를 업데이트합니다. (매시간 재로그인 필요 없음)
- **리스트 그룹화 및 영속성**: 
  - 사용자가 정의한 리스트 그룹 정보를 `list_groups.json`에 저장하여 드래그 앤 드롭 위치와 폴딩 상태를 유지합니다.
  - 사이드바에서 그룹 생성, 이름 수정, 삭제가 가능하며 `SortableJS`를 이용해 리스트를 자유롭게 배치합니다.
- **기한 및 날짜 처리**:
  - 기한은 `YYYY-MM-DD (요일)` 형식으로 표시되며, 오늘/내일/어제의 경우 각각 **"오늘"**, **"내일"**, **"어제"**로 스마트하게 표시됩니다.
  - 자체 제작한 날짜 선택 팝업을 통해 기한 설정 및 삭제를 직관적으로 수행합니다.
- **API 연동**: `ToDoConnection` 클래스를 통해 Microsoft Graph API와 통신합니다. 서브태스크 제목 수정, 기한 변경 등 세부 API 엔드포인트가 추가되었습니다.
- **데이터 업데이트 방식**: 기존의 자동 리프레시(Timer) 기능을 제거하고, 사용자가 명시적으로 클릭할 수 있는 **수동 '업데이트' 버튼**으로 대체하여 불필요한 API 호출을 줄이고 사용자 제어권을 높였습니다.
- **Optimistic UI**: 중요도(별표) 토글, 서브태스크 완료 처리 시 서버 응답 전 UI를 먼저 변경하여 반응성을 극대화했습니다. 실패 시에만 원복합니다.
- **UI 강조 및 레이아웃**:
  - **폰트**: 전역적으로 `Pretendard`를 사용하여 가독성을 높였습니다.
  - **컴팩트 모드**: 태스크 목록의 높이를 줄여 한 화면에 더 많은 정보를 보여줍니다.
  - **애니메이션**: 배경의 동적인 블롭 효과를 강화하여 세련된 UI를 제공합니다.
- **성능 최적화**: `ThreadPoolExecutor`를 사용하여 여러 할 일 목록을 병렬로 가져옵니다.

## 4. 주요 파일 구조
- `app.py`: Flask 애플리케이션의 메인 로직 및 API 엔드포인트. (토큰 갱신 로직 포함)
- `templates/`: 사용자 인터페이스(HTML).
- `config.ini`: 애플리케이션 설정 및 인증 토큰 저장. (보안 주의)
- `Dockerfile` / `docker-compose.yml`: 컨테이너 빌드 및 실행 설정.

## 5. 개발 및 운영 지침
- **인증 오류 발생 시**: `config.ini`의 `client_token` 내 `expires_at`이 현재 시간보다 이전인지 확인하거나, `refresh_token`의 유효성을 점검하십시오. 필요한 경우 다시 로그인(`auth_login`)이 필요할 수 있습니다.
- **날짜 표시**: 백엔드에서 `kst_dt = dt + timedelta(hours=9)` 로직을 통해 보정된 날짜를 사용합니다.
- **Proxy 대응**: `werkzeug.middleware.proxy_fix.ProxyFix`를 적용하여 리버스 프록시 환경에서도 리다이렉트 URI가 올바르게 생성되도록 합니다.
- **보안**: `SECRET_KEY`는 가급적 환경 변수를 통해 설정하여 세션 보안을 강화하십시오.
