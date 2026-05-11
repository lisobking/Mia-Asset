from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    api_keys = relationship("APICredential", back_populates="owner")
    settings = relationship("TradingSetting", back_populates="owner")

class APICredential(Base):
    __tablename__ = "api_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    broker_name = Column(String(50)) # alpaca, kis, kiwoom
    env_type = Column(String(20)) # paper, live
    api_key = Column(String(512))
    secret_key = Column(String(512)) # 주의: 실제 상용에선 암호화(AES)되어야 함
    account_number = Column(String(512), nullable=True)

    owner = relationship("User", back_populates="api_keys")

class TradingSetting(Base):
    __tablename__ = "trading_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    target_symbol = Column(String(20), default="SOXL") # 유저가 선택한 종목
    trade_amount = Column(Float, default=50000.0) # 1회 매수 금액
    is_active = Column(Boolean, default=False) # 봇 가동 여부

    owner = relationship("User", back_populates="settings")
