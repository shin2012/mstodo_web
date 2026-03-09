# Python 3.11 이미지 사용 (pymstodo 최신 버전 호환)
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 및 설정 파일 복사
COPY . .

# Gunicorn으로 Flask 앱 실행 (포트 5001)
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:app"]
