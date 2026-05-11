"""
KIS 계좌 잔고 직접 조회 진단 스크립트
실행: python check_balance.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# DB에서 자격증명 읽기
from api.database import SessionLocal
from api.models import APICredential, User
from api.auth import decrypt_data

db = SessionLocal()
try:
    # 첫 번째 유저의 KIS 자격증명 조회
    cred = db.query(APICredential).filter(APICredential.broker_name == "kis").first()
    if not cred:
        cred = db.query(APICredential).first()
    
    if not cred:
        print("❌ 저장된 자격증명이 없습니다. 설정 페이지에서 먼저 연동해주세요.")
        sys.exit(1)
    
    user = db.query(User).filter(User.id == cred.user_id).first()
    print(f"✅ 계좌 정보 조회 중: {user.email if user else 'unknown'}")
    print(f"   브로커: {cred.broker_name}, 환경: {cred.env_type}")
    
    api_key = decrypt_data(cred.api_key)
    secret_key = decrypt_data(cred.secret_key)
    account_number = decrypt_data(cred.account_number) if cred.account_number else ""
    print(f"   계좌번호: {account_number}")
    print()
    
    from skills.api_clients.kis_client import KisClient
    is_paper = (cred.env_type == "paper")
    broker = KisClient(
        is_paper=is_paper,
        api_key=api_key,
        secret_key=secret_key,
        account_number=account_number
    )
    
    print("📡 KIS API 잔고 조회 중...")
    detail = broker.get_balance_detail()
    
    print()
    print("=" * 40)
    print(f"🇰🇷 원화 잔고:  ₩{detail['krw']:,.0f}")
    print(f"🇺🇸 달러 잔고:  ${detail['usd']:,.4f}")
    if detail['krw'] > 0 or detail['usd'] > 0:
        print("✅ 계좌 연결 정상")
    else:
        print("⚠️  잔고가 0이거나 조회 실패 — Render 로그 확인 필요")
    print("=" * 40)

finally:
    db.close()
