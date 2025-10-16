import streamlit as st
import pandas as pd
from datetime import datetime
import auth
import database as db
import floor_price as fp
from config import Config
import config_manager as cm
import json

# Page config
st.set_page_config(
    page_title="Floor Price Validator",
    page_icon="💰",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .success-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #d4edda;
        border: 2px solid #28a745;
        text-align: center;
    }
    .error-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #f8d7da;
        border: 2px solid #dc3545;
        text-align: center;
    }
    .metric-card {
        padding: 15px;
        border-radius: 8px;
        background-color: #f8f9fa;
        border-left: 4px solid #007bff;
    }
</style>
""", unsafe_allow_html=True)

def main_app():
    """Main application after login"""
    
    # Header with logout
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("💰 Floor Price Validator")
    with col2:
        st.write(f"👤 {st.session_state.user_email}")
        if st.button("🚪 ออกจากระบบ"):
            auth.logout()
    
    # Tabs
    if st.session_state.is_admin:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([  # ⬅️ เพิ่ม tab5
            "✅ ตรวจสอบราคา", 
            "📊 ประวัติของฉัน", 
            "👥 จัดการผู้ใช้",
            "⚙️ จัดการราคา",  # ⬅️ เพิ่ม tab นี้
            "🔧 Admin Dashboard"
        ])
    else:
        tab1, tab2 = st.tabs(["✅ ตรวจสอบราคา", "📊 ประวัติของฉัน"])
    
    # Tab 1: Price Check
    with tab1:
        price_check_interface()
    
    # Tab 2: User History
    with tab2:
        user_history_interface()
    
    # Tab 3: User Management (only for admins)
    if st.session_state.is_admin:
        with tab3:
            user_management_interface()
    
    # Tab 4: Price Config Management (only for admins)  # ⬅️ เพิ่ม
    if st.session_state.is_admin:
        with tab4:
            price_config_interface()
    
    # Tab 5: Admin Dashboard (only for admins)
    if st.session_state.is_admin:
        with tab5:
            admin_dashboard()

def price_check_interface():
    """Interface สำหรับตรวจสอบราคา"""
    st.header("ตรวจสอบราคา Broadband")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 ข้อมูลแพ็คเกจ")
        
        # Customer type
        customer_type = st.selectbox(
            "ประเภทลูกค้า",
            options=['residential', 'business'],
            format_func=lambda x: Config.CUSTOMER_TYPES.get(x, x),
            help="Residential = บ้าน, Business = ธุรกิจ"
        )
        
        # Speed selection mode - เพิ่มส่วนนี้
        speed_mode = st.radio(
            "วิธีเลือกความเร็ว",
            options=['standard', 'custom'],
            format_func=lambda x: "📦 แพ็คเกจมาตรฐาน" if x == 'standard' else "✏️ กรอกเองแบบ Custom",
            horizontal=True,
            help="แพ็คเกจมาตรฐาน = เลือกจากรายการ, Custom = กรอกความเร็วเอง"
        )
        
        # Get speed options from config
        db_config = cm.get_active_config()
        if db_config:
            if customer_type == 'residential':
                speed_dict = {int(k): v for k, v in db_config.speed_prices_residential.items()}
            else:
                speed_dict = {int(k): v for k, v in db_config.speed_prices_business.items()}
            speed_options = sorted(speed_dict.keys())
        else:
            speed_options = sorted(Config.SPEED_PRICES[customer_type].keys())
        
        # Speed input based on mode
        if speed_mode == 'standard':
            # แพ็คเกจมาตรฐาน - ใช้ selectbox
            speed = st.selectbox(
                "ความเร็วอินเทอร์เน็ต (Mbps)",
                options=speed_options,
                index=1 if len(speed_options) > 1 else 0
            )
            st.info(f"💡 ราคาตามแพ็คเกจมาตรฐาน")
            
        else:
            # Custom speed - ใช้ number input
            col_speed1, col_speed2 = st.columns([2, 1])
            
            with col_speed1:
                speed = st.number_input(
                    "ความเร็วอินเทอร์เน็ต (Mbps)",
                    min_value=10,
                    max_value=10000,
                    value=speed_options[1] if len(speed_options) > 1 else speed_options[0],
                    step=10,
                    help="กรอกความเร็วที่ต้องการ"
                )
            
            with col_speed2:
                st.write("**แพ็คเกจมาตรฐาน:**")
                for s in speed_options:
                    st.caption(f"• {s} Mbps")
            
            # แสดง warning และ interpolation details
            if speed not in speed_options:
                st.warning(f"⚠️ **{speed} Mbps** ไม่ใช่แพ็คเกจมาตรฐาน")
                
                # คำนวณช่วงที่จะใช้ interpolate
                lower_speeds = [s for s in speed_options if s < speed]
                upper_speeds = [s for s in speed_options if s > speed]
                
                if lower_speeds and upper_speeds:
                    lower = max(lower_speeds)
                    upper = min(upper_speeds)
                    st.caption(f"📊 ระบบจะคำนวณราคาจากช่วง **{lower} Mbps** → **{upper} Mbps**")
                elif lower_speeds:
                    lower = max(lower_speeds)
                    st.caption(f"📊 ความเร็วเกินแพ็คเกจสูงสุด - ใช้ราคา **{lower} Mbps** เป็นฐาน")
                else:
                    upper = min(upper_speeds)
                    st.caption(f"📊 ความเร็วต่ำกว่าแพ็คเกจต่ำสุด - ใช้ราคา **{upper} Mbps** เป็นฐาน")
            else:
                st.success(f"✅ **{speed} Mbps** เป็นแพ็คเกจมาตรฐาน")
        
        # Distance
        max_distance = Config.MAX_STANDARD_DISTANCE[customer_type]
        distance = st.number_input(
            f"ระยะทางการติดตั้ง (กม.) - มาตรฐาน ≤{max_distance} กม.",
            min_value=0.0,
            max_value=100.0,
            value=1.0,
            step=0.5,
            help=f"เกิน {max_distance} กม. จะคิดเพิ่ม {Config.EXTRA_DISTANCE_MULTIPLIER}x"
        )
        
        # Fixed IP
        has_fixed_ip = st.checkbox(
            f"Fixed IP (+{Config.FIXED_IP_PRICE[customer_type]} ฿/เดือน)",
            help="IP Address คงที่สำหรับ Remote Access, CCTV, Server"
        )
        
        # Equipment
        st.write("**อุปกรณ์ปลายทาง**")
        equipment_list = []
        
        col_eq1, col_eq2 = st.columns(2)
        
        with col_eq1:
            if st.checkbox("Standard Router", value=True):
                equipment_list.append('standard_router')
            if st.checkbox("WiFi 6 Router (+500฿)"):
                equipment_list.append('wifi6_router')
            if st.checkbox("Mesh System (+1500฿)"):
                equipment_list.append('mesh_system')
        
        with col_eq2:
            if st.checkbox("ONT (+300฿)"):
                equipment_list.append('ont')
            if customer_type == 'business':
                if st.checkbox("Managed Switch (+800฿)"):
                    equipment_list.append('managed_switch')
                if st.checkbox("Enterprise Router (+2000฿)"):
                    equipment_list.append('enterprise_router')
        
        # Contract period
        contract_months = st.select_slider(
            "ระยะเวลาสัญญา (เดือน)",
            options=[12, 24, 36],
            value=24
        )
        
        # Show discount
        discount_rate = Config.CONTRACT_DISCOUNTS[customer_type].get(contract_months, 0)
        if discount_rate > 0:
            st.info(f"💰 ส่วนลด {contract_months} เดือน: {discount_rate*100:.0f}%")
    
    with col2:
        st.subheader("💵 ราคาที่เสนอ")
        
        proposed_price = st.number_input(
            "ราคาที่ต้องการเสนอขาย (บาท/เดือน)",
            min_value=0.0,
            value=1000.0,
            step=50.0
        )
        
        notes = st.text_area("หมายเหตุ (ถ้ามี)", height=100)
        
        st.write("")
        
        # Check button
        if st.button("🔍 ตรวจสอบราคา", type="primary", width='stretch'):
            try:
                # Calculate floor price
                result = fp.calculate_floor_price(
                    customer_type=customer_type,
                    speed=speed,
                    distance=distance,
                    equipment_list=equipment_list,
                    contract_months=contract_months,
                    has_fixed_ip=has_fixed_ip
                )
                
                floor_price = result['floor_price']
                breakdown = result['breakdown']
                
                is_valid = proposed_price >= floor_price
                margin = fp.calculate_margin(proposed_price, floor_price)
                
                # Log the check
                db.log_price_check(
                    user_email=st.session_state.user_email,
                    customer_type=customer_type,
                    speed=speed,
                    distance=distance,
                    equipment=','.join(equipment_list),
                    contract_months=contract_months,
                    proposed_price=proposed_price,
                    floor_price=floor_price,
                    is_valid=is_valid,
                    margin_percent=margin,
                    has_fixed_ip=has_fixed_ip,
                    notes=notes
                )
                
                # Display result
                st.write("---")
                
                if is_valid:
                    st.markdown(f"""
                    <div class="success-box">
                        <h2>✅ ราคาผ่าน!</h2>
                        <p style="font-size: 20px;">ราคาที่เสนอสูงกว่า floor price</p>
                        <p style="font-size: 18px; color: #28a745;"><strong>Margin: {margin:.2f}%</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    difference = floor_price - proposed_price
                    st.markdown(f"""
                    <div class="error-box">
                        <h2>❌ ราคาไม่ผ่าน!</h2>
                        <p style="font-size: 20px;">ราคาต่ำกว่า floor price</p>
                        <p style="font-size: 18px; color: #dc3545;"><strong>ต่ำกว่า {difference:.2f} บาท</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Show breakdown for admins
                if st.session_state.is_admin:
                    st.write("---")
                    st.info(f"🔐 **Admin Only - Floor Price: {floor_price:.2f} ฿/เดือน**")
                    
                    # แสดงว่าใช้ interpolation หรือไม่
                    if breakdown.get('interpolated', False):
                        st.warning(f"⚠️ **ใช้ Interpolation:** ความเร็ว {speed} Mbps ไม่ใช่แพ็คเกจมาตรฐาน")
                    
                    with st.expander("📊 รายละเอียดการคำนวณ"):
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.write("**ค่าพื้นฐาน:**")
                            st.write(f"- ราคาตามความเร็ว: {breakdown['base_price']:,.2f} ฿")
                            if breakdown.get('interpolated', False):
                                if 'speed_lower' in breakdown and 'speed_upper' in breakdown:
                                    st.caption(f"  └ คำนวณจาก {breakdown['speed_lower']} → {breakdown['speed_upper']} Mbps")
                            st.write(f"- ค่าระยะทาง ({breakdown['distance_km']} km): {breakdown['distance_cost']:,.2f} ฿")
                            if breakdown.get('fixed_ip_cost', 0) > 0:
                                st.write(f"- Fixed IP: {breakdown['fixed_ip_cost']:,.2f} ฿")
                            st.write(f"- อุปกรณ์: {breakdown['equipment_cost']:,.2f} ฿")
                        
                        with col_b:
                            st.write("**ส่วนลดและเพิ่มเติม:**")
                            if breakdown.get('business_premium', 0) > 0:
                                st.write(f"- Business Premium (+10%): +{breakdown['business_premium']:,.2f} ฿")
                            st.write(f"- ส่วนลด {breakdown['contract_months']} เดือน ({breakdown['discount_rate']*100:.0f}%): -{breakdown['discount_amount']:,.2f} ฿")
                            st.write(f"**รวมสุทธิ: {floor_price:,.2f} ฿/เดือน**")
                        
                        # Full JSON
                        with st.expander("🔍 Complete Breakdown (JSON)"):
                            st.json(breakdown)
                    
                    # Installation fee
                    installation_fee = fp.get_installation_fee(customer_type)
                    st.caption(f"💡 ค่าติดตั้งครั้งแรก: {installation_fee:,.0f} บาท (ไม่นับใน monthly)")
            
            except ValueError as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดในการคำนวณ: {str(e)}")
                import traceback
                with st.expander("🐛 Error Details (Admin)"):
                    st.code(traceback.format_exc())

def user_management_interface():
    """หน้าจัดการ users (Admin only)"""
    st.header("👥 จัดการผู้ใช้งาน")
    
    # User stats
    stats = db.get_user_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 ทั้งหมด", stats['total'])
    col2.metric("✅ ใช้งานได้", stats['active'])
    col3.metric("❌ ปิดการใช้งาน", stats['inactive'])
    col4.metric("🔐 Admin", stats['admins'])
    
    st.write("---")
    
    # Add new user
    with st.expander("➕ เพิ่มผู้ใช้ใหม่", expanded=False):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            new_email = st.text_input(
                "Email", 
                placeholder=f"user@{Config.ALLOWED_EMAIL_DOMAIN}",
                key="new_user_email"
            )
        
        with col2:
            new_is_admin = st.checkbox("Admin", key="new_user_admin")
        
        if st.button("➕ เพิ่มผู้ใช้", type="primary"):
            if not new_email:
                st.error("❌ กรุณากรอก email")
            elif '@' not in new_email:
                st.error("❌ รูปแบบ email ไม่ถูกต้อง")
            elif not auth.is_valid_email_domain(new_email):
                st.error(f"❌ กรุณาใช้ email ของ {Config.ALLOWED_EMAIL_DOMAIN} เท่านั้น")
            else:
                existing_user = db.get_user(new_email)
                if existing_user:
                    st.error("❌ มี email นี้ในระบบแล้ว")
                else:
                    db.create_user(new_email, new_is_admin)
                    st.success(f"✅ เพิ่ม {new_email} สำเร็จ!")
                    st.rerun()
    
    st.write("---")
    
    # User list
    st.subheader("📋 รายชื่อผู้ใช้ทั้งหมด")
    
    users = db.get_all_users()
    
    if not users:
        st.info("ยังไม่มีผู้ใช้ในระบบ")
        return
    
    # Create DataFrame for display
    for user in users:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 2])
            
            with col1:
                status_icon = "✅" if user.is_active else "❌"
                admin_badge = "🔐 Admin" if user.is_admin else "👤 User"
                st.write(f"{status_icon} **{user.email}** ({admin_badge})")
                if user.last_login:
                    st.caption(f"Login ล่าสุด: {user.last_login.strftime('%Y-%m-%d %H:%M')}")
                else:
                    st.caption("ยังไม่เคย login")
            
            with col2:
                # Toggle active status
                current_status = "เปิด" if user.is_active else "ปิด"
                if st.button(f"🔄 {current_status}", key=f"toggle_{user.id}"):
                    db.update_user(user.email, is_active=not user.is_active)
                    st.rerun()
            
            with col3:
                # Toggle admin status
                if user.email != st.session_state.user_email:  # ป้องกันไม่ให้ลบสิทธิ์ตัวเอง
                    admin_text = "ลด" if user.is_admin else "เลื่อน"
                    if st.button(f"⚡ {admin_text}", key=f"admin_{user.id}"):
                        db.update_user(user.email, is_admin=not user.is_admin)
                        st.rerun()
            
            with col4:
                # Delete user
                if user.email != st.session_state.user_email:  # ป้องกันไม่ให้ลบตัวเอง
                    if st.button("🗑️ ลบ", key=f"delete_{user.id}"):
                        st.session_state[f'confirm_delete_{user.id}'] = True
            
            with col5:
                # Confirm delete
                if st.session_state.get(f'confirm_delete_{user.id}', False):
                    if st.button(f"⚠️ ยืนยันลบ {user.email}", key=f"confirm_{user.id}", type="secondary"):
                        db.delete_user(user.email)
                        st.success(f"✅ ลบ {user.email} สำเร็จ")
                        if f'confirm_delete_{user.id}' in st.session_state:
                            del st.session_state[f'confirm_delete_{user.id}']
                        st.rerun()
            
            st.divider()
    
    # Export user list
    st.write("---")
    df = pd.DataFrame([{
        'Email': user.email,
        'สถานะ': 'ใช้งานได้' if user.is_active else 'ปิดการใช้งาน',
        'Role': 'Admin' if user.is_admin else 'User',
        'สร้างเมื่อ': user.created_at.strftime('%Y-%m-%d %H:%M'),
        'Login ล่าสุด': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'ยังไม่เคย login'
    } for user in users])
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 ดาวน์โหลดรายชื่อผู้ใช้ (CSV)",
        data=csv,
        file_name=f'users_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv'
    )

def user_history_interface():
    """แสดงประวัติการตรวจสอบของ user"""
    st.header("📊 ประวัติการตรวจสอบของคุณ")
    
    logs = db.get_user_logs(st.session_state.user_email)
    
    if not logs:
        st.info("ยังไม่มีประวัติการตรวจสอบ")
        return
    
    # Summary metrics
    total_checks = len(logs)
    valid_checks = sum(1 for log in logs if log.is_valid)
    invalid_checks = total_checks - valid_checks
    
    col1, col2, col3 = st.columns(3)
    col1.metric("ตรวจสอบทั้งหมด", total_checks)
    col2.metric("ผ่าน ✅", valid_checks)
    col3.metric("ไม่ผ่าน ❌", invalid_checks)
    
    st.write("---")
    
    # Table
    df = pd.DataFrame([{
        'วันที่': log.checked_at.strftime('%Y-%m-%d %H:%M'),
        'ประเภท': '🏠' if log.customer_type == 'residential' else '🏢',
        'ความเร็ว': f"{log.speed} Mbps",
        'ระยะทาง': f"{log.distance} km",
        'Fixed IP': '✅' if log.has_fixed_ip else '❌',
        'สัญญา': f"{log.contract_months} เดือน",
        'ราคาเสนอ': f"{log.proposed_price:,.0f} ฿",
        'ผลการตรวจสอบ': '✅ ผ่าน' if log.is_valid else '❌ ไม่ผ่าน',
        'Margin': f"{log.margin_percent:.1f}%" if log.margin_percent else '-',
        'หมายเหตุ': log.notes or '-'
    } for log in logs])
    
    st.dataframe(df, width='stretch', hide_index=True)

def admin_dashboard():
    """Admin dashboard - แสดง floor price และ log ทั้งหมด"""
    st.header("🔧 Admin Dashboard")
    
    # Summary
    all_logs = db.get_all_logs(limit=500)
    
    if not all_logs:
        st.info("ยังไม่มีข้อมูล")
        return
    
    total = len(all_logs)
    valid = sum(1 for log in all_logs if log.is_valid)
    invalid = total - valid
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ตรวจสอบทั้งหมด", total)
    col2.metric("ผ่าน ✅", valid)
    col3.metric("ไม่ผ่าน ❌", invalid)
    col4.metric("Pass Rate", f"{(valid/total*100):.1f}%")
    
    st.write("---")
    
    # Floor Price Calculator
    with st.expander("🔐 คำนวณ Floor Price (Admin Only)"):
        # เพิ่ม speed mode selection
        calc_speed_mode = st.radio(
            "วิธีเลือกความเร็ว",
            options=['standard', 'custom'],
            format_func=lambda x: "📦 แพ็คเกจมาตรฐาน" if x == 'standard' else "✏️ Custom",
            horizontal=True,
            key='admin_speed_mode'
        )
        
        col1, col2, col3, col4, col5 = st.columns(5)
    
        with col1:
            calc_customer_type = st.selectbox(
                "ประเภท", 
                ['residential', 'business'],
                format_func=lambda x: '🏠 บ้าน' if x == 'residential' else '🏢 ธุรกิจ',
                key='admin_customer_type'
            )
        
        with col2:
            # Get speed options from config
            db_config = cm.get_active_config()
            if db_config:
                if calc_customer_type == 'residential':
                    speed_dict = {int(k): v for k, v in db_config.speed_prices_residential.items()}
                else:
                    speed_dict = {int(k): v for k, v in db_config.speed_prices_business.items()}
                speed_options = sorted(speed_dict.keys())
            else:
                speed_options = sorted(Config.SPEED_PRICES[calc_customer_type].keys())
            
            if calc_speed_mode == 'standard':
                calc_speed = st.selectbox(
                    "ความเร็ว", 
                    speed_options,
                    key='admin_speed'
                )
            else:
                calc_speed = st.number_input(
                    "ความเร็ว (Mbps)",
                    min_value=10,
                    max_value=10000,
                    value=speed_options[1] if len(speed_options) > 1 else speed_options[0],
                    step=10,
                    key='admin_speed_custom'
                )
                if calc_speed not in speed_options:
                    st.caption(f"⚠️ Custom: {calc_speed} Mbps")
        
        with col3:
            calc_distance = st.number_input(
                "ระยะทาง (km)", 
                0.0, 100.0, 1.0, 
                key='admin_distance'
            )
        
        with col4:
            calc_has_fixed_ip = st.checkbox(
                "Fixed IP",
                key='admin_fixed_ip'
            )
        
        with col5:
            calc_contract = st.selectbox(
                "สัญญา (เดือน)", 
                [12, 24, 36],
                key='admin_contract'
            )
        
        if st.button("🔍 คำนวณ", width='stretch'):
            try:
                result = fp.calculate_floor_price(
                    customer_type=calc_customer_type,
                    speed=calc_speed,
                    distance=calc_distance,
                    equipment_list=['standard_router'],
                    contract_months=calc_contract,
                    has_fixed_ip=calc_has_fixed_ip
                )
                
                floor = result['floor_price']
                breakdown = result['breakdown']
                
                st.success(f"💰 Floor Price: **{floor:,.2f} ฿/เดือน**")
                
                # แสดง interpolation warning
                if breakdown.get('interpolated', False):
                    st.warning(f"⚠️ ใช้ Interpolation สำหรับ {calc_speed} Mbps")
                
                # Show breakdown
                with st.expander("📊 รายละเอียดการคำนวณ"):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.write("**ค่าพื้นฐาน:**")
                        st.write(f"- ราคาตามความเร็ว: {breakdown['base_price']:,.2f} ฿")
                        if breakdown.get('interpolated', False):
                            if 'speed_lower' in breakdown and 'speed_upper' in breakdown:
                                st.caption(f"  └ คำนวณจาก {breakdown['speed_lower']} → {breakdown['speed_upper']} Mbps")
                        st.write(f"- ค่าระยะทาง ({breakdown['distance_km']} km): {breakdown['distance_cost']:,.2f} ฿")
                        if breakdown.get('fixed_ip_cost', 0) > 0:
                            st.write(f"- Fixed IP: {breakdown['fixed_ip_cost']:,.2f} ฿")
                        st.write(f"- อุปกรณ์: {breakdown['equipment_cost']:,.2f} ฿")
                    
                    with col_b:
                        st.write("**ส่วนลดและเพิ่มเติม:**")
                        if breakdown.get('business_premium', 0) > 0:
                            st.write(f"- Business Premium (+10%): +{breakdown['business_premium']:,.2f} ฿")
                        st.write(f"- ส่วนลด {breakdown['contract_months']} เดือน ({breakdown['discount_rate']*100:.0f}%): -{breakdown['discount_amount']:,.2f} ฿")
                        st.write(f"**รวมสุทธิ: {floor:,.2f} ฿/เดือน**")
                    
                    # Installation fee
                    installation_fee = fp.get_installation_fee(calc_customer_type)
                    st.info(f"💡 ค่าติดตั้งครั้งแรก: {installation_fee:,.0f} บาท (ไม่นับใน monthly)")
                    
                    # Full JSON
                    with st.expander("🔍 Complete Breakdown (JSON)"):
                        st.json(breakdown)
            
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
    
    st.write("---")
    
    # All logs
    st.subheader("📋 Log ทั้งหมด")
    
    df = pd.DataFrame([{
        'วันที่': log.checked_at.strftime('%Y-%m-%d %H:%M'),
        'User': log.user_email.split('@')[0],
        'ประเภท': '🏠' if log.customer_type == 'residential' else '🏢',  # ⬅️ เพิ่ม
        'ความเร็ว': log.speed,
        'ระยะทาง': log.distance,
        'Fixed IP': '✅' if log.has_fixed_ip else '❌',  # ⬅️ เพิ่ม
        'อุปกรณ์': log.equipment,
        'สัญญา': log.contract_months,
        'ราคาเสนอ': log.proposed_price,
        'Floor Price': log.floor_price,
        'ผ่าน': '✅' if log.is_valid else '❌',
        'Margin%': round(log.margin_percent, 1) if log.margin_percent else 0,
        'หมายเหตุ': log.notes or '-'
    } for log in all_logs])
    
    st.dataframe(df, width='stretch', hide_index=True)
    
    # Export
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 ดาวน์โหลด CSV",
        data=csv,
        file_name=f'floor_price_logs_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv'
    )

def price_config_interface():
    """หน้าจัดการ Pricing Configuration (Admin only)"""
    st.header("⚙️ จัดการ Pricing Configuration")
    
    # Get all configs
    configs = cm.get_all_configs()
    
    # Summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📋 Config ทั้งหมด", len(configs))
    with col2:
        active_config = [c for c in configs if c.is_active]
        if active_config:
            st.success(f"✅ Config ที่ใช้งาน: **{active_config[0].config_name}**")
        else:
            st.warning("⚠️ ยังไม่มี config ที่ active")
    
    st.write("---")
    
    # Tabs for different actions
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["📋 รายการ Config", "➕ สร้าง/คัดลอก", "📥 Import/Export"])
    
    with sub_tab1:
        config_list_ui(configs)
    
    with sub_tab2:
        config_create_ui(configs)
    
    with sub_tab3:
        config_import_export_ui(configs)

def config_list_ui(configs):
    """แสดงรายการ config"""
    st.subheader("📋 รายการ Pricing Configuration")
    
    if not configs:
        st.info("ยังไม่มี config ในระบบ กรุณาสร้าง config ใหม่")
        if st.button("🚀 สร้าง Default Config"):
            cm.create_default_config(created_by=st.session_state.user_email)
            st.success("✅ สร้าง default config สำเร็จ!")
            st.rerun()
        return
    
    for config in configs:
        with st.expander(
            f"{'✅ ' if config.is_active else '⚪ '}{config.config_name}" + 
            (f" (Active)" if config.is_active else ""),
            expanded=config.is_active
        ):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**สร้างโดย:** {config.created_by}")
                st.write(f"**สร้างเมื่อ:** {config.created_at.strftime('%Y-%m-%d %H:%M')}")
                st.write(f"**อัปเดตล่าสุด:** {config.updated_at.strftime('%Y-%m-%d %H:%M')}")
                if config.notes:
                    st.caption(f"📝 {config.notes}")
            
            with col2:
                if not config.is_active:
                    if st.button(f"✅ เปิดใช้งาน", key=f"activate_{config.id}"):
                        cm.activate_config(config.config_name, st.session_state.user_email)
                        st.success(f"✅ เปิดใช้งาน {config.config_name}")
                        st.rerun()
                
                if not config.is_active:
                    if st.button(f"🗑️ ลบ", key=f"delete_{config.id}"):
                        if cm.delete_config(config.config_name, st.session_state.user_email):
                            st.success(f"✅ ลบ {config.config_name} สำเร็จ")
                            st.rerun()
                        else:
                            st.error("❌ ไม่สามารถลบได้ (config กำลังใช้งานอยู่)")
            
            # Show pricing details
            st.write("---")
            
            tab_res, tab_bus = st.tabs(["🏠 Residential", "🏢 Business"])
            
            with tab_res:
                st.write("**ราคาตามความเร็ว:**")
                st.json(config.speed_prices_residential)
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("ค่าระยะทาง", f"{config.distance_price_residential} ฿/km")
                with col_b:
                    st.metric("ระยะมาตรฐาน", f"{config.max_distance_residential} km")
                with col_c:
                    st.metric("Fixed IP", f"{config.fixed_ip_residential} ฿")
                
                st.write("**ส่วนลดตามสัญญา:**")
                discounts_res = {f"{k} เดือน": f"{v*100:.0f}%" 
                                for k, v in config.contract_discounts_residential.items()}
                st.json(discounts_res)
            
            with tab_bus:
                st.write("**ราคาตามความเร็ว:**")
                st.json(config.speed_prices_business)
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("ค่าระยะทาง", f"{config.distance_price_business} ฿/km")
                with col_b:
                    st.metric("ระยะมาตรฐาน", f"{config.max_distance_business} km")
                with col_c:
                    st.metric("Fixed IP", f"{config.fixed_ip_business} ฿")
                
                st.write("**ส่วนลดตามสัญญา:**")
                discounts_bus = {f"{k} เดือน": f"{v*100:.0f}%" 
                                for k, v in config.contract_discounts_business.items()}
                st.json(discounts_bus)
                
                st.metric("Business Premium", f"{config.business_premium_percent*100:.0f}%")

def config_create_ui(configs):
    """UI สำหรับสร้าง/คัดลอก config"""
    st.subheader("➕ สร้างหรือคัดลอก Config")
    
    # Duplicate existing config
    if configs:
        st.write("**คัดลอกจาก Config ที่มี:**")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            source_config = st.selectbox(
                "เลือก config ต้นฉบับ",
                options=[c.config_name for c in configs],
                key="duplicate_source"
            )
        
        with col2:
            new_name = st.text_input(
                "ชื่อ config ใหม่",
                placeholder="promotion_2025",
                key="duplicate_name"
            )
        
        if st.button("📋 คัดลอก Config", type="primary"):
            if not new_name:
                st.error("❌ กรุณากรอกชื่อ config ใหม่")
            elif new_name in [c.config_name for c in configs]:
                st.error("❌ ชื่อ config นี้มีอยู่แล้ว")
            else:
                new_config = cm.duplicate_config(
                    source_config, 
                    new_name, 
                    st.session_state.user_email
                )
                if new_config:
                    st.success(f"✅ คัดลอก config สำเร็จ: {new_name}")
                    st.rerun()
                else:
                    st.error("❌ ไม่สามารถคัดลอกได้")
    
    st.write("---")
    
    # Create from default
    st.write("**สร้างจาก config.py:**")
    if st.button("🚀 สร้าง Default Config"):
        cm.create_default_config(created_by=st.session_state.user_email)
        st.success("✅ สร้าง default config สำเร็จ!")
        st.rerun()

def config_import_export_ui(configs):
    """UI สำหรับ Import/Export"""
    st.subheader("📥 Import/Export Configuration")
    
    # Export
    st.write("**Export Config:**")
    if configs:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            export_config = st.selectbox(
                "เลือก config ที่จะ export",
                options=[c.config_name for c in configs],
                key="export_config"
            )
        
        with col2:
            st.write("")
            st.write("")
            if st.button("📥 Export เป็น JSON"):
                json_data = cm.export_config_to_json(export_config)
                if json_data:
                    json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="💾 ดาวน์โหลด JSON",
                        data=json_str,
                        file_name=f"pricing_config_{export_config}_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
    
    st.write("---")
    
    # Import
    st.write("**Import Config:**")
    uploaded_file = st.file_uploader(
        "อัปโหลดไฟล์ JSON",
        type=['json'],
        key="import_file"
    )
    
    import_name = st.text_input(
        "ชื่อ config ที่จะสร้าง",
        placeholder="imported_config",
        key="import_name"
    )
    
    if st.button("📤 Import จาก JSON", type="primary"):
        if not uploaded_file:
            st.error("❌ กรุณาอัปโหลดไฟล์ JSON")
        elif not import_name:
            st.error("❌ กรุณากรอกชื่อ config")
        elif import_name in [c.config_name for c in configs]:
            st.error("❌ ชื่อ config นี้มีอยู่แล้ว")
        else:
            try:
                json_data = json.load(uploaded_file)
                new_config = cm.import_config_from_json(
                    json_data,
                    import_name,
                    st.session_state.user_email
                )
                if new_config:
                    st.success(f"✅ Import config สำเร็จ: {import_name}")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ ไม่สามารถ import ได้: {str(e)}")

# Main entry point
if __name__ == "__main__":
    # Check authentication
    auth.require_auth()
    
    # Run main app if authenticated
    main_app()