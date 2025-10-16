import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
from dotenv import load_dotenv
import os

load_dotenv()

def test_smtp():
    """ทดสอบการส่ง email"""
    
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    
    print(f"🔧 กำลังทดสอบการเชื่อมต่อ SMTP...")
    print(f"   Server: {SMTP_SERVER}")
    print(f"   Port: {SMTP_PORT}")
    print(f"   Username: {SMTP_USERNAME}")
    print(f"   Password: {'*' * len(SMTP_PASSWORD) if SMTP_PASSWORD else 'ไม่ได้ตั้งค่า'}")
    print()
    
    if not SMTP_PASSWORD:
        print("❌ กรุณาตั้งค่า SMTP_PASSWORD ในไฟล์ .env")
        return
    
    try:
        # สร้างข้อความทดสอบ
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = SMTP_USERNAME  # ส่งให้ตัวเอง
        msg['Subject'] = 'ทดสอบระบบ Floor Price Validator'
        
        body = """
        <html>
        <body>
            <h2>ทดสอบระบบส่ง Email สำเร็จ!</h2>
            <p>ระบบสามารถส่ง email ผ่าน SMTP ได้แล้ว</p>
            <p>รหัส OTP ตัวอย่าง: <strong>123456</strong></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        print("📧 กำลังเชื่อมต่อและส่ง email...")
        
        # เลือกใช้ SSL หรือ STARTTLS
        if SMTP_PORT == 465:
            print("   ใช้ SSL connection (port 465)")
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context)
        else:
            print("   ใช้ STARTTLS connection")
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
        
        print("🔐 กำลัง login...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        print("📤 กำลังส่ง email...")
        server.send_message(msg)
        server.quit()
        
        print()
        print("✅ ส่ง email สำเร็จ!")
        print(f"   กรุณาตรวจสอบ inbox ที่: {SMTP_USERNAME}")
        
    except smtplib.SMTPAuthenticationError:
        print("❌ ไม่สามารถ login ได้")
        print("   กรุณาตรวจสอบ:")
        print("   1. Username ถูกต้องหรือไม่")
        print("   2. Password ถูกต้องหรือไม่")
        print("   3. Email account อนุญาตให้ใช้ SMTP หรือไม่")
        
    except smtplib.SMTPConnectError as e:
        print(f"❌ ไม่สามารถเชื่อมต่อ SMTP server ได้: {e}")
        print("   กรุณาตรวจสอบ:")
        print("   1. SMTP server address ถูกต้องหรือไม่")
        print("   2. Port ถูกต้องหรือไม่")
        print("   3. Firewall block port นี้หรือไม่")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        import traceback
        print()
        print("📋 รายละเอียด error:")
        print(traceback.format_exc())

if __name__ == "__main__":
    test_smtp()