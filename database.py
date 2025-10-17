from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import secrets
import uuid
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
    reference_id = Column(String, unique=True, nullable=False)  # UUID สำหรับอ้างอิง
    
    # User info
    user_email = Column(String, nullable=False)
    checked_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    
    # Package details
    customer_type = Column(String, nullable=False)
    speed = Column(Integer, nullable=False)
    distance = Column(Float, nullable=False)
    equipment = Column(String, nullable=False)
    contract_months = Column(Integer, nullable=False)
    has_fixed_ip = Column(Boolean, default=False)
    
    # Pricing
    proposed_price = Column(Float, nullable=False)
    discount_percent = Column(Float, default=0)  # ส่วนลด %
    
    # Floor prices
    floor_existing = Column(Float, nullable=False)  # Floor ลูกค้าเดิม
    floor_new = Column(Float, nullable=False)  # Floor ลูกค้าใหม่
    floor_weighted = Column(Float, nullable=False)  # Floor ถัวเฉลี่ย
    floor_price = Column(Float, nullable=False)  # Floor ที่จัดเก็บเพื่อเทียบกับรายได้สุทธิ
    
    # Customer mix
    existing_customer_ratio = Column(Float, default=0.7)  # สัดส่วนลูกค้าเดิม
    new_customer_ratio = Column(Float, default=0.3)  # สัดส่วนลูกค้าใหม่
    
    # Revenue after fees
    net_revenue = Column(Float, nullable=False)  # รายได้สุทธิหลังหักส่วนลดและค่าธรรมเนียม
    regulator_fee = Column(Float, nullable=False)  # ค่าธรรมเนียม กสทช. 4%
    
    # Validation results
    is_valid_existing = Column(Boolean, nullable=False)  # ผ่านหรือไม่ (vs ลูกค้าเดิม)
    is_valid_new = Column(Boolean, nullable=False)  # ผ่านหรือไม่ (vs ลูกค้าใหม่)
    is_valid_weighted = Column(Boolean, nullable=False)  # ผ่านหรือไม่ (vs ถัวเฉลี่ย)
    
    # Margins
    margin_existing_baht = Column(Float)  # Margin vs ลูกค้าเดิม (บาท)
    margin_existing_percent = Column(Float)  # Margin vs ลูกค้าเดิม (%)
    margin_new_baht = Column(Float)  # Margin vs ลูกค้าใหม่ (บาท)
    margin_new_percent = Column(Float)  # Margin vs ลูกค้าใหม่ (%)
    margin_weighted_baht = Column(Float)  # Margin vs ถัวเฉลี่ย (บาท)
    margin_weighted_percent = Column(Float)  # Margin vs ถัวเฉลี่ย (%)
    is_valid = Column(Boolean, default=False, nullable=False)
    
    # Export tracking
    exported_at = Column(DateTime)  # วันที่ export เอกสาร
    exported_by = Column(String)  # ผู้ export
    export_count = Column(Integer, default=0)  # จำนวนครั้งที่ export
    
    # Notes
    notes = Column(Text)

# Backward compatibility - เก็บ model เดิมไว้
class PriceCheckLegacy(Base):
    __tablename__ = 'price_checks_legacy'
    
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

# Create tables and ensure schema compatibility
Base.metadata.create_all(engine)


def ensure_price_checks_schema():
    """Ensure legacy databases include all required columns for price_checks."""
    inspector = inspect(engine)
    if 'price_checks' not in inspector.get_table_names():
        return

    existing_columns = {column['name'] for column in inspector.get_columns('price_checks')}

    # column_name -> (DDL snippet, default value)
    required_columns = {
        'reference_id': ('TEXT', None),
        'floor_price': ('FLOAT', 0.0),
        'equipment': ('TEXT', ''),
        'discount_percent': ('FLOAT', 0.0),
        'floor_existing': ('FLOAT', 0.0),
        'floor_new': ('FLOAT', 0.0),
        'floor_weighted': ('FLOAT', 0.0),
        'existing_customer_ratio': ('FLOAT', 0.7),
        'new_customer_ratio': ('FLOAT', 0.3),
        'net_revenue': ('FLOAT', 0.0),
        'regulator_fee': ('FLOAT', 0.0),
        'is_valid_existing': ('BOOLEAN', False),
        'is_valid_new': ('BOOLEAN', False),
        'is_valid_weighted': ('BOOLEAN', False),
        'margin_existing_baht': ('FLOAT', 0.0),
        'margin_existing_percent': ('FLOAT', 0.0),
        'margin_new_baht': ('FLOAT', 0.0),
        'margin_new_percent': ('FLOAT', 0.0),
        'margin_weighted_baht': ('FLOAT', 0.0),
        'margin_weighted_percent': ('FLOAT', 0.0),
        'is_valid': ('BOOLEAN', False),
        'exported_at': ('DATETIME', None),
        'exported_by': ('TEXT', ''),
        'export_count': ('INTEGER', 0),
        'notes': ('TEXT', '')
    }

    columns_added = []

    with engine.begin() as conn:
        for column_name, (ddl, _) in required_columns.items():
            if column_name not in existing_columns:
                conn.execute(text(f"ALTER TABLE price_checks ADD COLUMN {column_name} {ddl}"))
                columns_added.append(column_name)

        # Populate defaults for nullable columns (including freshly added ones)
        for column_name, (_, default_value) in required_columns.items():
            if default_value is None and column_name != 'reference_id':
                continue
            if column_name == 'reference_id':
                rows = conn.execute(text(
                    "SELECT id FROM price_checks WHERE reference_id IS NULL OR reference_id = ''"
                )).fetchall()
                for row in rows:
                    conn.execute(
                        text("UPDATE price_checks SET reference_id = :ref WHERE id = :id"),
                        {"ref": str(uuid.uuid4()), "id": row.id}
                    )
            else:
                conn.execute(
                    text(
                        f"UPDATE price_checks SET {column_name} = :default "
                        f"WHERE {column_name} IS NULL"
                    ),
                    {"default": default_value}
                )

        # Ensure unique index for reference IDs once column exists
        if 'reference_id' in existing_columns or 'reference_id' in columns_added:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_price_checks_reference_id "
                    "ON price_checks(reference_id)"
                )
            )


ensure_price_checks_schema()

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

def log_price_check_comprehensive(
    user_email, customer_type, speed, distance, equipment, 
    contract_months, has_fixed_ip, proposed_price, discount_percent,
    floor_existing, floor_new, floor_weighted,
    existing_customer_ratio, new_customer_ratio,
    net_revenue, regulator_fee,
    is_valid_existing, is_valid_new, is_valid_weighted,
    margin_existing_baht, margin_existing_percent,
    margin_new_baht, margin_new_percent,
    margin_weighted_baht, margin_weighted_percent,
    floor_price=None,
    ip_address=None, notes=None
):
    """
    บันทึกการตรวจสอบราคาแบบครบถ้วน (รองรับระบบใหม่)
    """
    db = SessionLocal()
    try:
        # Generate unique reference ID
        reference_id = str(uuid.uuid4())
        
        log = PriceCheck(
            reference_id=reference_id,
            user_email=user_email,
            customer_type=customer_type,
            speed=speed,
            distance=distance,
            equipment=equipment,
            contract_months=contract_months,
            has_fixed_ip=has_fixed_ip,
            proposed_price=proposed_price,
            discount_percent=discount_percent,
            floor_existing=floor_existing,
            floor_new=floor_new,
            floor_weighted=floor_weighted,
            existing_customer_ratio=existing_customer_ratio,
            new_customer_ratio=new_customer_ratio,
            net_revenue=net_revenue,
            regulator_fee=regulator_fee,
            is_valid_existing=is_valid_existing,
            is_valid_new=is_valid_new,
            is_valid_weighted=is_valid_weighted,
            margin_existing_baht=margin_existing_baht,
            margin_existing_percent=margin_existing_percent,
            margin_new_baht=margin_new_baht,
            margin_new_percent=margin_new_percent,
            margin_weighted_baht=margin_weighted_baht,
            margin_weighted_percent=margin_weighted_percent,
            is_valid=is_valid_weighted,
            floor_price=floor_price if floor_price is not None else floor_weighted,
            ip_address=ip_address,
            notes=notes
        )
        
        db.add(log)
        db.commit()
        db.refresh(log)  # เพื่อดึง ID กลับมา
        
        return log
    finally:
        db.close()

def log_price_check(user_email, customer_type, speed, distance, equipment, 
                   contract_months, proposed_price, floor_price, is_valid, 
                   margin_percent, has_fixed_ip=False, ip_address=None, notes=None):
    """
    บันทึกการตรวจสอบราคาแบบเดิม (backward compatibility)
    """
    db = SessionLocal()
    try:
        log = PriceCheckLegacy(
            user_email=user_email,
            customer_type=customer_type,
            has_fixed_ip=has_fixed_ip,
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

def get_price_check_by_reference(reference_id):
    """ดึงข้อมูลการตรวจสอบจาก reference ID"""
    db = SessionLocal()
    try:
        return db.query(PriceCheck).filter(PriceCheck.reference_id == reference_id).first()
    finally:
        db.close()

def mark_as_exported(reference_id, exported_by):
    """บันทึกว่ามีการ export เอกสารแล้ว"""
    db = SessionLocal()
    try:
        log = db.query(PriceCheck).filter(PriceCheck.reference_id == reference_id).first()
        if log:
            log.exported_at = datetime.utcnow()
            log.exported_by = exported_by
            log.export_count = (log.export_count or 0) + 1
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_all_logs(limit=100):
    """ดึง log ทั้งหมด (แบบใหม่)"""
    db = SessionLocal()
    try:
        return db.query(PriceCheck).order_by(PriceCheck.checked_at.desc()).limit(limit).all()
    finally:
        db.close()

def get_all_logs_legacy(limit=100):
    """ดึง log ทั้งหมด (แบบเดิม)"""
    db = SessionLocal()
    try:
        return db.query(PriceCheckLegacy).order_by(PriceCheckLegacy.checked_at.desc()).limit(limit).all()
    finally:
        db.close()

def get_user_logs(email, limit=50):
    """แสดงประวัติการตรวจสอบของ user (แบบใหม่)"""
    db = SessionLocal()
    try:
        return db.query(PriceCheck).filter(
            PriceCheck.user_email == email
        ).order_by(PriceCheck.checked_at.desc()).limit(limit).all()
    finally:
        db.close()

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
        if not user:
            return False
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