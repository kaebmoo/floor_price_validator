from sqlalchemy import text
from database import engine, SessionLocal
import database as db

def migrate():
    """เพิ่ม column is_active ให้ user เดิม"""
    
    print("🔄 กำลัง migrate database...")
    
    try:
        # เพิ่ม column is_active (ถ้ายังไม่มี)
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
                conn.commit()
                print("✅ เพิ่ม column is_active สำเร็จ")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print("⚠️  Column is_active มีอยู่แล้ว")
                else:
                    raise
        
        # อัปเดต user เดิมให้ is_active = True
        session = SessionLocal()
        try:
            result = session.execute(text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL"))
            session.commit()
            print(f"✅ อัปเดต {result.rowcount} users ให้ active")
        finally:
            session.close()
        
        print("✅ Migration สำเร็จ!")
        
    except Exception as e:
        print(f"❌ Migration ล้มเหลว: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()