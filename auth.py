import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime
import streamlit as st
from config import Config
import database as db

def is_valid_email_domain(email):
    """ตรวจสอบว่า email เป็นของ domain องค์กรหรือไม่"""
    domain = email.split('@')[-1]
    return domain.lower() == Config.ALLOWED_EMAIL_DOMAIN.lower()

def send_otp_email(email, otp_code):
    """ส่ง OTP ผ่าน email"""
    
    # Development Mode - ไม่ส่ง email จริง
    if Config.DEV_MODE:
        st.session_state.dev_otp_code = otp_code  # เก็บไว้แสดงบนหน้าจอ
        return True
    
    # Production Mode - ส่ง email จริง
    try:
        msg = MIMEMultipart()
        msg['From'] = formataddr((Config.SENDER_NAME, Config.FROM_EMAIL))
        msg['To'] = email
        msg['Subject'] = 'รหัส OTP สำหรับเข้าสู่ระบบ Floor Price Validator'
        
        body = f"""
        <html>
        <body>
            <h2>รหัส OTP ของคุณ</h2>
            <p>รหัส OTP สำหรับเข้าสู่ระบบ: <strong style="font-size: 24px; color: #0066cc;">{otp_code}</strong></p>
            <p>รหัสนี้จะหมดอายุใน {Config.OTP_EXPIRY_MINUTES} นาที</p>
            <p><em>หากคุณไม่ได้ร้องขอรหัสนี้ กรุณาเพิกเฉยต่ออีเมลนี้</em></p>
            <br>
            <p>ฝ่ายบัญชีบริหารและกรอบอัตราค่าบริการ</p>
            <p>บริษัท โทรคมนาคมแห่งชาติ จำกัด (มหาชน)</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # เลือกใช้ SSL หรือ STARTTLS ตาม port
        if Config.SMTP_PORT == 465:
            # SSL connection (port 465)
            import ssl
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(Config.SMTP_SERVER, Config.SMTP_PORT, context=context)
        else:
            # STARTTLS connection (port 587 หรืออื่นๆ)
            server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
            server.starttls()
        
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except smtplib.SMTPAuthenticationError:
        st.error("❌ ไม่สามารถเข้าสู่ระบบ email ได้ กรุณาตรวจสอบ username/password")
        return False
    except smtplib.SMTPException as e:
        st.error(f"❌ เกิดข้อผิดพลาด SMTP: {str(e)}")
        return False
    except Exception as e:
        st.error(f"❌ ไม่สามารถส่ง OTP ได้: {str(e)}")
        return False

def login_page():
    """หน้า Login"""
    st.title("🔐 เข้าสู่ระบบ Floor Price Validator")
    
    # Show dev mode indicator
    if Config.DEV_MODE:
        st.warning("🔧 **Development Mode** - OTP จะแสดงบนหน้าจอ (ไม่ส่ง email จริง)")
    
    # Initialize session state
    if 'otp_sent' not in st.session_state:
        st.session_state.otp_sent = False
    if 'email_for_otp' not in st.session_state:
        st.session_state.email_for_otp = None
    if 'dev_otp_code' not in st.session_state:
        st.session_state.dev_otp_code = None
    
    if not st.session_state.otp_sent:
        # Step 1: Request OTP
        st.markdown("### ขั้นตอนที่ 1: กรอก Email")
        
        if Config.DEV_MODE:
            email = st.text_input(
                "Email", 
                placeholder="test@example.com (ใน dev mode ใช้ email อะไรก็ได้)"
            )
        else:
            email = st.text_input(
                "Email ขององค์กร", 
                placeholder=f"yourname@{Config.ALLOWED_EMAIL_DOMAIN}"
            )
        
        if st.button("ส่งรหัส OTP", type="primary"):
            if not email:
                st.error("❌ กรุณากรอก email")
                return
            
            email = email.strip()
            if '@' not in email:
                # ถ้าไม่มี @ ให้เติม domain ขององค์กรเข้าไป
                email = f"{email}@ntplc.co.th"

                # st.error("❌ รูปแบบ email ไม่ถูกต้อง")
            
            if not is_valid_email_domain(email):
                st.error(f"❌ กรุณาใช้ email ของ {Config.ALLOWED_EMAIL_DOMAIN} เท่านั้น")
            else:
                with st.spinner('กำลังตรวจสอบสิทธิ์...'):
                    try:
                        # ตรวจสอบว่า user มีสิทธิ์หรือไม่
                        user = db.get_user(email)
                        
                        if not user:
                            st.error("❌ ไม่พบ email นี้ในระบบ กรุณาติดต่อ Admin เพื่อขอสิทธิ์การใช้งาน")
                            st.info("📧 Admin Email: " + ", ".join(Config.ADMIN_EMAILS))
                            return
                        
                        if not user.is_active:
                            st.error("❌ บัญชีของคุณถูกปิดการใช้งาน กรุณาติดต่อ Admin")
                            st.info("📧 Admin Email: " + ", ".join(Config.ADMIN_EMAILS))
                            return
                        
                        # Generate and send OTP
                        otp_code = db.create_otp(email)
                        
                        if send_otp_email(email, otp_code):
                            st.session_state.otp_sent = True
                            st.session_state.email_for_otp = email
                            st.success("✅ ส่ง OTP สำเร็จ!")
                            st.rerun()
                        else:
                            st.error("❌ ไม่สามารถส่ง OTP ได้ กรุณาลองใหม่อีกครั้ง")
                    
                    except Exception as e:
                        st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
    
    else:
        # Step 2: Verify OTP
        st.markdown("### ขั้นตอนที่ 2: ยืนยัน OTP")
        st.info(f"📧 รหัส OTP ถูกส่งไปที่ {st.session_state.email_for_otp}")
        
        # Show OTP in dev mode
        if Config.DEV_MODE and st.session_state.dev_otp_code:
            st.success(f"🔧 **DEV MODE - รหัส OTP ของคุณคือ:** `{st.session_state.dev_otp_code}`")
        
        otp_input = st.text_input(
            "กรอกรหัส OTP (6 หลัก)", 
            max_chars=6,
            key="otp_input_field"
        )
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("ยืนยัน OTP", type="primary"):
                if not otp_input:
                    st.error("❌ กรุณากรอกรหัส OTP")
                elif len(otp_input) != 6:
                    st.error("❌ รหัส OTP ต้องมี 6 หลัก")
                else:
                    with st.spinner('กำลังตรวจสอบ OTP...'):
                        try:
                            if db.verify_otp(st.session_state.email_for_otp, otp_input):
                                user = db.get_user(st.session_state.email_for_otp)
                                
                                # ตรวจสอบอีกครั้งว่า user ยัง active อยู่
                                if not user.is_active:
                                    st.error("❌ บัญชีของคุณถูกปิดการใช้งาน")
                                    st.session_state.otp_sent = False
                                    st.session_state.email_for_otp = None
                                    return
                                
                                # Update last login
                                user.last_login = datetime.utcnow()
                                
                                st.session_state.logged_in = True
                                st.session_state.user_email = st.session_state.email_for_otp
                                st.session_state.is_admin = user.is_admin
                                st.session_state.otp_sent = False
                                st.session_state.dev_otp_code = None
                                st.success("✅ เข้าสู่ระบบสำเร็จ!")
                                st.rerun()
                            else:
                                st.error("❌ รหัส OTP ไม่ถูกต้องหรือหมดอายุ")
                        except Exception as e:
                            st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
        
        with col2:
            if st.button("ส่งรหัสใหม่"):
                st.session_state.otp_sent = False
                st.session_state.email_for_otp = None
                st.session_state.dev_otp_code = None
                st.rerun()

def logout():
    """Logout function"""
    for key in ['logged_in', 'user_email', 'is_admin', 'otp_sent', 'email_for_otp']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

def require_auth():
    """ตรวจสอบว่า user login แล้วหรือยัง"""
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        login_page()
        st.stop()