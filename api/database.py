from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# MariaDB 연결 URL (로컬 혹은 Docker 환경 변수 처리)
# 환경 변수에 없으면 기본적으로 SQLite를 사용하여 테스트가 쉽게 만듭니다.
DB_USER = os.getenv("DB_USER", "agbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "agbot_password")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_NAME = os.getenv("DB_NAME", "trading_db")

# 로컬 개발 시에는 sqlite를 폴백으로 사용
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./sql_app.db" # 기본값 SQLite
)

# SQLite의 경우 check_same_thread=False 필요
connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# DB 세션 의존성 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
