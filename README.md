# Microsoft To-Do 웹 서비스 (MSTodo Web)

Microsoft To-Do와 연동하여 웹 브라우저에서 할 일을 확인하고 관리할 수 있는 서비스입니다. Flask 기반으로 구축되었으며 Docker를 통해 간편하게 배포할 수 있습니다.

## 주요 기능
- **웹 인터페이스**: 브라우저를 통해 실시간으로 Microsoft To-Do 할 일 목록 확인 및 관리.
- **Docker 기반**: Docker 및 Docker Compose를 사용하여 환경 격리 및 간편한 배포.
- **안정적인 서버**: Gunicorn을 사용하여 프로덕션급 웹 서버 환경 제공.
- **자동 실행**: 시스템 재부팅 시에도 Docker restart 정책에 의해 자동으로 서비스 재개.

## 기술 스택
- **언어**: Python 3.11
- **프레임워크**: Flask
- **WSGI 서버**: Gunicorn
- **API 연동**: `pymstodo`
- **컨테이너화**: Docker, Docker Compose

## 파일 구조
- `app.py`: Flask 메인 애플리케이션 로직.
- `Dockerfile`: Python 3.11 환경 및 라이브러리 설치 정의.
- `docker-compose.yml`: 서비스 포트(5001), 볼륨, 재시작 정책 정의.
- `requirements.txt`: 필요한 Python 패키지 목록.
- `config.ini` / `token.json`: Microsoft To-Do API 인증 정보 (보안을 위해 Git 관리 대상에서 제외).

## 설치 및 실행 방법

### 사전 준비
- Docker 및 Docker Compose가 설치되어 있어야 합니다.
- Microsoft To-Do API 연동을 위한 `config.ini`와 `token.json` 파일이 필요합니다.

### 서비스 시작
1. 저장소를 클론합니다.
2. 프로젝트 루트 디렉토리에 `config.ini`와 `token.json` 파일을 배치합니다.
3. 다음 명령어를 실행하여 서비스를 빌드하고 시작합니다:
   ```bash
   docker-compose up -d --build
   ```
4. 브라우저에서 `http://localhost:5001`으로 접속합니다.

## 운영 명령어
- **서비스 상태 확인**: `docker-compose ps`
- **로그 확인**: `docker logs -f mstodo_web`
- **서비스 중지**: `docker-compose down`

## Nginx Proxy Manager (NPM) 설정
외부 접속이 필요한 경우 NPM에서 다음과 같이 설정하십시오:
- **Scheme**: `http`
- **Forward HostName / IP**: 호스트 서버의 IP (예: `10.0.0.99`)
- **Forward Port**: `5001`
