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

# Render Free 티어 기본 포트 10000
EXPOSE 10000

# shell form 사용: $PORT 환경변수가 런타임에 치환됨 (exec form은 치환 불가)
CMD ["sh", "-c", "python run.py"]
