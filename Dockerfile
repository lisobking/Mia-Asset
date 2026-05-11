# Python 3.9 슬림 이미지 기반
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (필요시)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# FastAPI 구동을 위한 uvicorn 추가 설치
RUN pip install --no-cache-dir fastapi uvicorn

# 소스 코드 전체 복사
COPY . .

# 외부로 노출할 포트
EXPOSE 8000

# 컨테이너 실행 시 FastAPI 서버 구동 (Render의 $PORT 환경 변수 대응)
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
