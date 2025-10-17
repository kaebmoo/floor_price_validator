from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
from config import Config

Base = declarative_base()
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class PricingConfig(Base):
    __tablename__ = 'pricing_configs'
    
    id = Column(Integer, primary_key=True)
    config_name = Column(String, unique=True, nullable=False)  # เช่น 'default', 'promotion_2025'
    is_active = Column(Boolean, default=False)
    
    # Speed Prices (JSON)
    speed_prices_residential = Column(JSON, nullable=False)
    speed_prices_business = Column(JSON, nullable=False)
    
    # Installation configuration (stored in legacy distance fields)
    distance_price_residential = Column(Float, nullable=False)  # base installation cost (residential)
    distance_price_business = Column(Float, nullable=False)     # base installation cost (business)
    max_distance_residential = Column(Float, nullable=False)   # base installation length in meters (residential)
    max_distance_business = Column(Float, nullable=False)      # base installation length in meters (business)
    extra_distance_multiplier = Column(Float, nullable=False)  # extra cost per additional meter

    # Fixed IP
    fixed_ip_residential = Column(Float, nullable=False)
    fixed_ip_business = Column(Float, nullable=False)
    
    # Equipment Prices (JSON)
    equipment_prices = Column(JSON, nullable=False)
    
    # Contract Discounts (JSON)
    contract_discounts_residential = Column(JSON, nullable=False)
    contract_discounts_business = Column(JSON, nullable=False)
    
    # Business Premium
    business_premium_percent = Column(Float, nullable=False)
    
    # Installation Fees
    installation_fee_residential = Column(Float, nullable=False)
    installation_fee_business = Column(Float, nullable=False)
    
    # Metadata
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text)

class ConfigHistory(Base):
    __tablename__ = 'config_history'
    
    id = Column(Integer, primary_key=True)
    config_name = Column(String, nullable=False)
    action = Column(String, nullable=False)  # 'created', 'updated', 'activated', 'deactivated'
    changed_by = Column(String, nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    old_values = Column(JSON)
    new_values = Column(JSON)

# Create tables
Base.metadata.create_all(engine)

# Cache
_config_cache = {'config': None, 'timestamp': None, 'ttl': 300}  # 5 minutes cache

def get_active_config():
    """ดึง config ที่ active อยู่ (with cache)"""
    from datetime import datetime
    
    # Check cache
    now = datetime.utcnow()
    if (_config_cache['config'] is not None and 
        _config_cache['timestamp'] is not None and
        (now - _config_cache['timestamp']).seconds < _config_cache['ttl']):
        return _config_cache['config']
    
    # Load from database
    db = SessionLocal()
    try:
        config = db.query(PricingConfig).filter(PricingConfig.is_active == True).first()
        
        if config:
            # Update cache
            _config_cache['config'] = config
            _config_cache['timestamp'] = now
            return config
        else:
            # Return default config from Config class
            return None
    finally:
        db.close()

def clear_config_cache():
    """ล้าง cache (เรียกหลังจาก update config)"""
    _config_cache['config'] = None
    _config_cache['timestamp'] = None

def create_default_config(created_by="system"):
    """สร้าง config ค่าเริ่มต้นจาก config.py"""
    db = SessionLocal()
    try:
        # Check if default exists
        existing = db.query(PricingConfig).filter(
            PricingConfig.config_name == 'default'
        ).first()
        
        if existing:
            print("Default config already exists")
            return existing
        
        # ⚠️ IMPORTANT: Ensure integer keys in JSON
        config = PricingConfig(
            config_name='default',
            is_active=True,
            
            # Convert dict keys to strings explicitly for JSON storage
            # They will be converted back to int when loaded
            speed_prices_residential={str(k): v for k, v in Config.SPEED_PRICES['residential'].items()},
            speed_prices_business={str(k): v for k, v in Config.SPEED_PRICES['business'].items()},
            
            distance_price_residential=Config.INSTALLATION_CONFIG['residential']['base_cost'],
            distance_price_business=Config.INSTALLATION_CONFIG['business']['base_cost'],
            max_distance_residential=Config.INSTALLATION_CONFIG['residential']['base_length_m'],
            max_distance_business=Config.INSTALLATION_CONFIG['business']['base_length_m'],
            extra_distance_multiplier=Config.INSTALLATION_CONFIG['extra_cost_per_meter'],
            fixed_ip_residential=Config.FIXED_IP_PRICE['residential'],
            fixed_ip_business=Config.FIXED_IP_PRICE['business'],
            equipment_prices=Config.EQUIPMENT_PRICES,
            
            # Contract discounts - convert keys to strings
            contract_discounts_residential={str(k): v for k, v in Config.CONTRACT_DISCOUNTS['residential'].items()},
            contract_discounts_business={str(k): v for k, v in Config.CONTRACT_DISCOUNTS['business'].items()},
            
            business_premium_percent=Config.BUSINESS_PREMIUM_PERCENT,
            installation_fee_residential=Config.INSTALLATION_FEE['residential'],
            installation_fee_business=Config.INSTALLATION_FEE['business'],
            created_by=created_by,
            notes='Default configuration imported from config.py'
        )
        
        db.add(config)
        db.commit()
        
        # Log history
        log_config_change(
            config_name='default',
            action='created',
            changed_by=created_by,
            new_values={'note': 'Initial default config created'}
        )
        
        clear_config_cache()
        return config
        
    finally:
        db.close()

def get_all_configs():
    """ดึง config ทั้งหมด"""
    db = SessionLocal()
    try:
        return db.query(PricingConfig).order_by(PricingConfig.created_at.desc()).all()
    finally:
        db.close()

def activate_config(config_name, activated_by):
    """เปิดใช้งาน config"""
    db = SessionLocal()
    try:
        # Deactivate all
        db.query(PricingConfig).update({'is_active': False})
        
        # Activate selected
        config = db.query(PricingConfig).filter(
            PricingConfig.config_name == config_name
        ).first()
        
        if config:
            config.is_active = True
            db.commit()
            
            log_config_change(
                config_name=config_name,
                action='activated',
                changed_by=activated_by,
                new_values={'is_active': True}
            )
            
            clear_config_cache()
            return True
        return False
    finally:
        db.close()

def duplicate_config(original_name, new_name, created_by):
    """คัดลอก config"""
    db = SessionLocal()
    try:
        original = db.query(PricingConfig).filter(
            PricingConfig.config_name == original_name
        ).first()
        
        if not original:
            return None
        
        new_config = PricingConfig(
            config_name=new_name,
            is_active=False,
            
            # Copy JSON data as-is (already in string key format)
            speed_prices_residential=original.speed_prices_residential,
            speed_prices_business=original.speed_prices_business,
            distance_price_residential=original.distance_price_residential,
            distance_price_business=original.distance_price_business,
            max_distance_residential=original.max_distance_residential,
            max_distance_business=original.max_distance_business,
            extra_distance_multiplier=original.extra_distance_multiplier,
            fixed_ip_residential=original.fixed_ip_residential,
            fixed_ip_business=original.fixed_ip_business,
            equipment_prices=original.equipment_prices,
            contract_discounts_residential=original.contract_discounts_residential,
            contract_discounts_business=original.contract_discounts_business,
            business_premium_percent=original.business_premium_percent,
            installation_fee_residential=original.installation_fee_residential,
            installation_fee_business=original.installation_fee_business,
            created_by=created_by,
            notes=f'Duplicated from {original_name}'
        )
        
        db.add(new_config)
        db.commit()
        
        log_config_change(
            config_name=new_name,
            action='created',
            changed_by=created_by,
            new_values={'note': f'Duplicated from {original_name}'}
        )
        
        return new_config
        
    finally:
        db.close()

def delete_config(config_name, deleted_by):
    """ลบ config (ห้ามลบ config ที่ active)"""
    db = SessionLocal()
    try:
        config = db.query(PricingConfig).filter(
            PricingConfig.config_name == config_name
        ).first()
        
        if not config:
            return False
        
        if config.is_active:
            return False  # Cannot delete active config
        
        db.delete(config)
        db.commit()
        
        log_config_change(
            config_name=config_name,
            action='deleted',
            changed_by=deleted_by,
            old_values={'config_name': config_name}
        )
        
        return True
        
    finally:
        db.close()

def log_config_change(config_name, action, changed_by, old_values=None, new_values=None):
    """บันทึกประวัติการเปลี่ยนแปลง"""
    db = SessionLocal()
    try:
        history = ConfigHistory(
            config_name=config_name,
            action=action,
            changed_by=changed_by,
            old_values=old_values,
            new_values=new_values
        )
        db.add(history)
        db.commit()
    finally:
        db.close()

def export_config_to_json(config_name):
    """Export config เป็น JSON"""
    db = SessionLocal()
    try:
        config = db.query(PricingConfig).filter(
            PricingConfig.config_name == config_name
        ).first()
        
        if not config:
            return None
        
        return {
            'config_name': config.config_name,
            'speed_prices': {
                'residential': config.speed_prices_residential,
                'business': config.speed_prices_business
            },
            'installation_pricing': {
                'residential': {
                    'base_cost': config.distance_price_residential,
                    'base_length_m': config.max_distance_residential
                },
                'business': {
                    'base_cost': config.distance_price_business,
                    'base_length_m': config.max_distance_business
                },
                'extra_cost_per_meter': config.extra_distance_multiplier
            },
            'fixed_ip': {
                'residential': config.fixed_ip_residential,
                'business': config.fixed_ip_business
            },
            'equipment_prices': config.equipment_prices,
            'contract_discounts': {
                'residential': config.contract_discounts_residential,
                'business': config.contract_discounts_business
            },
            'business_premium_percent': config.business_premium_percent,
            'installation_fee': {
                'residential': config.installation_fee_residential,
                'business': config.installation_fee_business
            },
            'notes': config.notes
        }
        
    finally:
        db.close()

def import_config_from_json(json_data, config_name, created_by):
    """Import config จาก JSON"""
    db = SessionLocal()
    try:
        config = PricingConfig(
            config_name=config_name,
            is_active=False,
            speed_prices_residential=json_data['speed_prices']['residential'],
            speed_prices_business=json_data['speed_prices']['business'],
            distance_price_residential=json_data['installation_pricing']['residential']['base_cost'],
            distance_price_business=json_data['installation_pricing']['business']['base_cost'],
            max_distance_residential=json_data['installation_pricing']['residential']['base_length_m'],
            max_distance_business=json_data['installation_pricing']['business']['base_length_m'],
            extra_distance_multiplier=json_data['installation_pricing']['extra_cost_per_meter'],
            fixed_ip_residential=json_data['fixed_ip']['residential'],
            fixed_ip_business=json_data['fixed_ip']['business'],
            equipment_prices=json_data['equipment_prices'],
            contract_discounts_residential=json_data['contract_discounts']['residential'],
            contract_discounts_business=json_data['contract_discounts']['business'],
            business_premium_percent=json_data['business_premium_percent'],
            installation_fee_residential=json_data['installation_fee']['residential'],
            installation_fee_business=json_data['installation_fee']['business'],
            created_by=created_by,
            notes=json_data.get('notes', 'Imported from JSON')
        )
        
        db.add(config)
        db.commit()
        
        log_config_change(
            config_name=config_name,
            action='created',
            changed_by=created_by,
            new_values={'note': 'Imported from JSON'}
        )
        
        clear_config_cache()
        return config
        
    finally:
        db.close()