import streamlit as st
import pandas as pd
from datetime import datetime
import auth
import database as db
import floor_price as fp
from config import Config

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
        st.title("Floor Price Validator")
    with col2:
        st.write(f"👤 {st.session_state.user_email}")
        if st.button("🚪 ออกจากระบบ"):
            auth.logout()
    
    # Tabs
    if st.session_state.is_admin:
        tab1, tab2, tab3, tab4 = st.tabs([
            "✅ ตรวจสอบราคา", 
            "📊 ประวัติของฉัน", 
            "👥 จัดการผู้ใช้",  # ⬅️ เพิ่ม tab นี้
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
    
    # Tab 4: Admin Dashboard (only for admins)
    if st.session_state.is_admin:
        with tab4:
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
        
        # Speed selection
        speed_options = sorted(Config.SPEED_PRICES[customer_type].keys())
        speed = st.selectbox(
            "ความเร็วอินเทอร์เน็ต (Mbps)",
            options=speed_options,
            index=1 if len(speed_options) > 1 else 0
        )
        
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
                
                with st.expander("📊 รายละเอียดการคำนวณ"):
                    st.json(breakdown)
                
                # Installation fee
                installation_fee = fp.get_installation_fee(customer_type)
                st.caption(f"💡 ค่าติดตั้งครั้งแรก: {installation_fee:,.0f} บาท (ไม่นับใน monthly)")

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
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            calc_customer_type = st.selectbox(
                "ประเภท", 
                ['residential', 'business'],
                format_func=lambda x: '🏠 บ้าน' if x == 'residential' else '🏢 ธุรกิจ',
                key='admin_customer_type'
            )
        
        with col2:
            speed_options = sorted(Config.SPEED_PRICES[calc_customer_type].keys())
            calc_speed = st.selectbox(
                "ความเร็ว", 
                speed_options,
                key='admin_speed'
            )
        
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
            
            # Show breakdown
            with st.expander("📊 รายละเอียดการคำนวณ"):
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.write("**ค่าพื้นฐาน:**")
                    st.write(f"- ราคาตามความเร็ว: {breakdown['base_price']:,.2f} ฿")
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

# Main entry point
if __name__ == "__main__":
    # Check authentication
    auth.require_auth()
    
    # Run main app if authenticated
    main_app()