from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import secrets
from config import Config

Base = declarative_base()
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class OTP(Base):
    __tablename__ = 'otps'
    
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    otp_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

class PriceCheck(Base):
    __tablename__ = 'price_checks'
    
    id = Column(Integer, primary_key=True)
    user_email = Column(String, nullable=False)
    customer_type = Column(String, nullable=False)  
    has_fixed_ip = Column(Boolean, default=False)   
    speed = Column(Integer, nullable=False)
    distance = Column(Float, nullable=False)
    equipment = Column(String, nullable=False)
    contract_months = Column(Integer, nullable=False)
    proposed_price = Column(Float, nullable=False)
    floor_price = Column(Float, nullable=False)
    is_valid = Column(Boolean, nullable=False)
    margin_percent = Column(Float)
    checked_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    notes = Column(Text)

# Create tables
Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

def create_user(email, is_admin=False):
    db = SessionLocal()
    try:
        user = User(email=email, is_admin=is_admin)
        db.add(user)
        db.commit()
        return user
    finally:
        db.close()

def get_user(email):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first()
    finally:
        db.close()

def create_otp(email):
    db = SessionLocal()
    try:
        # Generate 6-digit OTP
        otp_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        expires_at = datetime.utcnow() + timedelta(minutes=Config.OTP_EXPIRY_MINUTES)
        
        otp = OTP(email=email, otp_code=otp_code, expires_at=expires_at)
        db.add(otp)
        db.commit()
        return otp_code
    finally:
        db.close()

def verify_otp(email, otp_code):
    db = SessionLocal()
    try:
        otp = db.query(OTP).filter(
            OTP.email == email,
            OTP.otp_code == otp_code,
            OTP.used == False,
            OTP.expires_at > datetime.utcnow()
        ).first()
        
        if otp:
            otp.used = True
            db.commit()
            return True
        return False
    finally:
        db.close()

def log_price_check(user_email, customer_type, speed, distance, equipment, 
                   contract_months, proposed_price, floor_price, is_valid, 
                   margin_percent, has_fixed_ip=False, ip_address=None, notes=None):
    db = SessionLocal()
    try:
        log = PriceCheck(
            user_email=user_email,
            customer_type=customer_type,      # ⬅️ เพิ่ม
            has_fixed_ip=has_fixed_ip,         # ⬅️ เพิ่ม
            speed=speed,
            distance=distance,
            equipment=equipment,
            contract_months=contract_months,
            proposed_price=proposed_price,
            floor_price=floor_price,
            is_valid=is_valid,
            margin_percent=margin_percent,
            ip_address=ip_address,
            notes=notes
        )
        db.add(log)
        db.commit()
        return log
    finally:
        db.close()

def get_all_logs(limit=100):
    db = SessionLocal()
    try:
        return db.query(PriceCheck).order_by(PriceCheck.checked_at.desc()).limit(limit).all()
    finally:
        db.close()

def get_user_logs(email, limit=50):
    db = SessionLocal()
    try:
        return db.query(PriceCheck).filter(
            PriceCheck.user_email == email
        ).order_by(PriceCheck.checked_at.desc()).limit(limit).all()
    finally:
        db.close()

# เพิ่มลงท้ายไฟล์ database.py

def update_user(email, is_admin=None, is_active=None):
    """อัปเดตข้อมูล user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            if is_admin is not None:
                user.is_admin = is_admin
            if is_active is not None:
                user.is_active = is_active
            db.commit()
            return user
        return None
    finally:
        db.close()

def delete_user(email):
    """ลบ user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            db.delete(user)
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_all_users():
    """ดึงข้อมูล user ทั้งหมด"""
    db = SessionLocal()
    try:
        return db.query(User).order_by(User.created_at.desc()).all()
    finally:
        db.close()

def is_user_allowed(email):
    """ตรวจสอบว่า user มีสิทธิ์ใช้งานหรือไม่"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        # ถ้าไม่มี user ในระบบ = ไม่อนุญาต
        if not user:
            return False
        # ตรวจสอบว่า active หรือไม่
        return user.is_active
    finally:
        db.close()

def get_user_stats():
    """สถิติ users"""
    db = SessionLocal()
    try:
        total = db.query(User).count()
        active = db.query(User).filter(User.is_active == True).count()
        admins = db.query(User).filter(User.is_admin == True).count()
        return {
            'total': total,
            'active': active,
            'inactive': total - active,
            'admins': admins
        }
    finally:
        db.close()