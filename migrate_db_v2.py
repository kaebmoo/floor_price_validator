from sqlalchemy import text
from database import engine, SessionLocal

def migrate():
    """เพิ่ม columns customer_type และ has_fixed_ip"""
    
    print("🔄 กำลัง migrate database v2...")
    
    try:
        with engine.connect() as conn:
            # เพิ่ม customer_type
            try:
                conn.execute(text(
                    "ALTER TABLE price_checks ADD COLUMN customer_type VARCHAR DEFAULT 'residential'"
                ))
                conn.commit()
                print("✅ เพิ่ม column customer_type สำเร็จ")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("⚠️  Column customer_type มีอยู่แล้ว")
                else:
                    raise
            
            # เพิ่ม has_fixed_ip
            try:
                conn.execute(text(
                    "ALTER TABLE price_checks ADD COLUMN has_fixed_ip BOOLEAN DEFAULT FALSE"
                ))
                conn.commit()
                print("✅ เพิ่ม column has_fixed_ip สำเร็จ")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("⚠️  Column has_fixed_ip มีอยู่แล้ว")
                else:
                    raise
        
        # อัปเดตข้อมูลเดิม
        session = SessionLocal()
        try:
            result = session.execute(text(
                "UPDATE price_checks SET customer_type = 'residential' WHERE customer_type IS NULL"
            ))
            session.commit()
            print(f"✅ อัปเดต {result.rowcount} records")
        finally:
            session.close()
        
        print("✅ Migration v2 สำเร็จ!")
        
    except Exception as e:
        print(f"❌ Migration ล้มเหลว: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()