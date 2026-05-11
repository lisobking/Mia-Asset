from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
import os

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./sql_app.db"
)

# Render postgres:// → postgresql:// 자동 변환
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

is_sqlite = "sqlite" in SQLALCHEMY_DATABASE_URL

# SQLite: check_same_thread=False + busy_timeout 10초 (잠금 대기 허용)
connect_args = {"check_same_thread": False, "timeout": 10} if is_sqlite else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    # SQLite는 동시 접속이 제한적 → pool_size 최소화
    **({} if not is_sqlite else {"pool_pre_ping": True})
)

# SQLite WAL 모드 활성화:
# - WAL(Write-Ahead Logging): 읽기/쓰기 동시 허용, 구 인스턴스와 신 인스턴스 공존 가능
# - busy_timeout: 잠금 대기 시간을 5초로 제한 (무한 대기 방지)
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")   # 5초 대기 후 포기
        cursor.execute("PRAGMA synchronous=NORMAL")  # 성능 향상
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
