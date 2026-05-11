import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.database import SessionLocal
from api.models import User, APICredential
from api.auth import encrypt_data

db = SessionLocal()
user = db.query(User).first()
if not user:
    print("No user")
    sys.exit(0)

try:
    db_cred = APICredential(user_id=user.id)
    db.add(db_cred)
    db_cred.broker_name = "kis"
    db_cred.env_type = "paper"
    db_cred.api_key = encrypt_data("test_key")
    db_cred.secret_key = encrypt_data("test_secret")
    db_cred.account_number = encrypt_data("12345")
    db.commit()
    print("Success")
except Exception as e:
    print("Error:", e)
