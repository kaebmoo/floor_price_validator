# สร้างไฟล์ fix_json_keys.py
from config_manager import SessionLocal, PricingConfig
import json

def fix_json_keys():
    """แก้ไข JSON keys ใน database จาก int เป็น string"""
    db = SessionLocal()
    try:
        configs = db.query(PricingConfig).all()
        
        for config in configs:
            # แก้ speed prices
            if config.speed_prices_residential:
                config.speed_prices_residential = {
                    str(k): v for k, v in config.speed_prices_residential.items()
                }
            if config.speed_prices_business:
                config.speed_prices_business = {
                    str(k): v for k, v in config.speed_prices_business.items()
                }
            
            # แก้ contract discounts
            if config.contract_discounts_residential:
                config.contract_discounts_residential = {
                    str(k): v for k, v in config.contract_discounts_residential.items()
                }
            if config.contract_discounts_business:
                config.contract_discounts_business = {
                    str(k): v for k, v in config.contract_discounts_business.items()
                }
        
        db.commit()
        print(f"✅ Fixed {len(configs)} configs")
    finally:
        db.close()

if __name__ == "__main__":
    fix_json_keys()