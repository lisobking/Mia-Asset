from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import os
from cryptography.fernet import Fernet

# 강력한 데이터 암호화 설정 (Fernet 대칭키)
_env_key = os.getenv("ENCRYPTION_KEY")
if not _env_key:
    # 환경변수 미설정 시 임시 폴백 키 (실사용 시 반드시 Render 환경변수에 ENCRYPTION_KEY 세팅 권장)
    _env_key = b'Z3V6Y21uZGtvamVocWxzY21ueGthaG9wcWtqZGZncG0='
else:
    _env_key = _env_key.encode()

cipher_suite = Fernet(_env_key)

def encrypt_data(data: str) -> str:
    if not data:
        return data
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(data: str) -> str:
    if not data:
        return data
    try:
        return cipher_suite.decrypt(data.encode()).decode()
    except Exception:
        # 복호화 실패 시 기존 평문으로 간주하여 호환성 유지
        return data

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_ag_bot_key_12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7일 유지

# 비밀번호 해싱 설정 (bcrypt 4.0 호환성 이슈로 pbkdf2_sha256 사용)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
