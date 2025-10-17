import streamlit as st
import pandas as pd
from datetime import datetime
import auth
import database as db
import floor_price as fp
import document_export as doc_export
from config import Config
import config_manager as cm
import json
import base64

# Page config
st.set_page_config(
    page_title="Floor Price Validator v2.0",
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
    .warning-box {
        padding: 20px;
        border-radius: 10px;
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        text-align: center;
    }
    .metric-card {
        padding: 15px;
        border-radius: 8px;
        background-color: #f8f9fa;
        border-left: 4px solid #007bff;
    }
    .floor-comparison {
        border: 2px solid #0066cc;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        background: #f0f8ff;
    }
    .reference-id {
        font-family: 'Courier New', monospace;
        font-size: 14px;
        background: #e6f2ff;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #0066cc;
    }
</style>
""", unsafe_allow_html=True)

def main_app():
    """Main application after login"""
    
    # Header with logout
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("💰 Floor Price Validator v2.0")
        st.caption("ระบบตรวจสอบราคาขั้นต่ำ (รองรับ Weighted Average & Document Export)")
    with col2:
        st.write(f"👤 {st.session_state.user_email}")
        if st.button("🚪 ออกจากระบบ", key="btn_logout_header"):
            auth.logout()
    
    # Tabs
    if st.session_state.is_admin:
        tabs = st.tabs([
            "✅ ตรวจสอบราคา",
            "📊 ประวัติของฉัน",
            "🔍 ตรวจสอบเอกสาร",
            "📈 ตารางเปรียบเทียบ",
            "👥 จัดการผู้ใช้",
            "⚙️ จัดการราคา",
            "🔧 Admin Dashboard"
        ])
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = tabs
    else:
        tabs = st.tabs([
            "✅ ตรวจสอบราคา",
            "📊 ประวัติของฉัน",
            "🔍 ตรวจสอบเอกสาร",
            "📈 ตารางเปรียบเทียบ"
        ])
        tab1, tab2, tab3, tab4 = tabs
    
    # Tab 1: Price Check (NEW VERSION)
    with tab1:
        price_check_interface_v2()
    
    # Tab 2: User History
    with tab2:
        user_history_interface()
    
    # Tab 3: Document Verification
    with tab3:
        document_verification_interface()
    
    # Tab 4: Comparison Table
    with tab4:
        comparison_table_interface()
    
    # Admin tabs
    if st.session_state.is_admin:
        with tab5:
            user_management_interface()
        
        with tab6:
            price_config_interface()
        
        with tab7:
            admin_dashboard()


def price_check_interface_v2():
    """Interface สำหรับตรวจสอบราคา (Version 2.0 - รองรับ Weighted Average)"""
    st.header("ตรวจสอบราคา Broadband (Version 2.0)")
    st.info("💡 **สิ่งที่เปลี่ยนแปลง:** รองรับการคำนวณแบบถัวเฉลี่ย (Weighted Average) ระหว่างลูกค้าเดิม/ใหม่ และระบบหักส่วนลด + ค่าธรรมเนียม กสทช. 4%")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 ข้อมูลแพ็คเกจ")

        customer_type = st.selectbox(
            "ประเภทลูกค้า",
            options=['residential', 'business'],
            format_func=lambda x: Config.CUSTOMER_TYPES.get(x, x)
        )

        speed_options = sorted(fp._load_pricing_config()['speed_prices'][customer_type].keys())
        speed = st.selectbox("ความเร็วอินเทอร์เน็ต (Mbps)", options=speed_options, index=speed_options.index(500) if 500 in speed_options else 0)

        distance = st.number_input(
            "ระยะทางการติดตั้ง (กม.)",
            min_value=0.0,
            max_value=5.0,
            value=0.315,
            step=0.01,
            help="ระยะทางสายมาตรฐาน 300 เมตร + 15 เมตร = 0.315 กม."
        )

        has_fixed_ip = st.checkbox("Fixed IP (+200 ฿/เดือน)")

        st.write("**อุปกรณ์ปลายทาง**")
        equipment_options = list(Config.EQUIPMENT_PRICES.keys())
        default_selection = [eq for eq in equipment_options if eq in (
            'ONU ZTE F612 (No WiFi + 1POTS)',
            'ONU Huawei HG8145X6 (AX3000 + 1POTS)',
            'WiFi 6 Router (AX.3000)',
            'WiFi 6 Router (AX.1200)'
        )]
        equipment_list = st.multiselect(
            "เลือกอุปกรณ์",
            options=equipment_options,
            default=default_selection,
            help="เลือกรายการจากแผน เช่น ONU, Router, ATA"
        )
        
        # Contract period
        contract_months = st.select_slider(
            "ระยะเวลาสัญญา (เดือน)",
            options=[12, 24, 36],
            value=12
        )
    
    with col2:
        st.subheader("💵 ราคาและส่วนลด")

        proposed_price = st.number_input(
            "ราคาที่ต้องการเสนอขาย (บาท/เดือน)",
            min_value=0.0,
            value=871.42,
            step=1.0
        )

        discount_percent = st.number_input(
            "ส่วนลด (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0
        )

        st.write("---")

        st.subheader("👥 สัดส่วนลูกค้า")
        existing_ratio = st.slider(
            "สัดส่วนลูกค้าเดิม (%)",
            min_value=0,
            max_value=100,
            value=70,
            step=1
        ) / 100
        new_ratio = 1 - existing_ratio

        col_ratio1, col_ratio2 = st.columns(2)
        col_ratio1.metric("ลูกค้าเดิม", f"{existing_ratio*100:.0f}%", help="ไม่คิดค่าติดตั้ง")
        col_ratio2.metric("ลูกค้าใหม่", f"{new_ratio*100:.0f}%", help="คิดค่าติดตั้ง")

        st.write("---")

        notes = st.text_area("หมายเหตุ (ถ้ามี)", height=80)

        if st.button("🔍 ตรวจสอบราคา", type="primary", width="stretch", key="btn_check_price"):
            perform_price_check_v2(
                customer_type, speed, distance, equipment_list,
                contract_months, has_fixed_ip, proposed_price,
                discount_percent, existing_ratio, new_ratio, notes
            )


def perform_price_check_v2(customer_type, speed, distance, equipment_list,
                           contract_months, has_fixed_ip, proposed_price,
                           discount_percent, existing_ratio, new_ratio, notes):
    """ทำการตรวจสอบราคาแบบใหม่ (Version 2.0)"""
    try:
        # 1. คำนวณ Weighted Floor
        weighted_result = fp.calculate_weighted_floor(
            customer_type, speed, distance, equipment_list,
            contract_months, has_fixed_ip, existing_ratio
        )
        
        floor_existing = weighted_result['floor_existing']
        floor_new = weighted_result['floor_new']
        floor_weighted = weighted_result['floor_weighted']
        
        # 2. คำนวณรายได้สุทธิหลังหักส่วนลดและค่าธรรมเนียม
        revenue_result = fp.calculate_net_revenue_after_fees(proposed_price, discount_percent)
        net_revenue = revenue_result['net_revenue']
        regulator_fee = revenue_result['regulator_fee']
        
        # 3. คำนวณ Margin แบบต่างๆ
        margin_existing = fp.calculate_comprehensive_margin(proposed_price, floor_existing, discount_percent)
        margin_new = fp.calculate_comprehensive_margin(proposed_price, floor_new, discount_percent)
        margin_weighted = fp.calculate_comprehensive_margin(proposed_price, floor_weighted, discount_percent)
        
        # 4. บันทึกลง database
        log = db.log_price_check_comprehensive(
            user_email=st.session_state.user_email,
            customer_type=customer_type,
            speed=speed,
            distance=distance,
            equipment=','.join(equipment_list),
            contract_months=contract_months,
            has_fixed_ip=has_fixed_ip,
            proposed_price=proposed_price,
            discount_percent=discount_percent,
            floor_existing=floor_existing,
            floor_new=floor_new,
            floor_weighted=floor_weighted,
            existing_customer_ratio=existing_ratio,
            new_customer_ratio=new_ratio,
            net_revenue=net_revenue,
            regulator_fee=regulator_fee,
            is_valid_existing=margin_existing['is_valid'],
            is_valid_new=margin_new['is_valid'],
            is_valid_weighted=margin_weighted['is_valid'],
            margin_existing_baht=margin_existing['margin_baht'],
            margin_existing_percent=margin_existing['margin_percent'],
            margin_new_baht=margin_new['margin_baht'],
            margin_new_percent=margin_new['margin_percent'],
            margin_weighted_baht=margin_weighted['margin_baht'],
            margin_weighted_percent=margin_weighted['margin_percent'],
            floor_price=floor_weighted,
            notes=notes
        )
        
        # 5. แสดงผลลัพธ์
        st.write("---")
        st.success("✅ คำนวณเสร็จสิ้น!")
        
        # แสดง Reference ID
        st.markdown(f"""
        <div class="reference-id">
            <strong>🔖 Reference ID:</strong> {log.reference_id}<br>
            <small>เก็บรหัสนี้ไว้สำหรับการตรวจสอบเอกสาร</small>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        # แสดงรายได้สุทธิ
        col_rev1, col_rev2, col_rev3, col_rev4 = st.columns(4)
        col_rev1.metric("ราคาเสนอ", f"{proposed_price:,.2f} ฿")
        col_rev2.metric("ส่วนลด", f"-{revenue_result['discount_amount']:,.2f} ฿")
        col_rev3.metric("ค่าธรรมเนียม 4%", f"-{regulator_fee:,.2f} ฿")
        col_rev4.metric("รายได้สุทธิ", f"{net_revenue:,.2f} ฿", delta=None)
        
        st.write("---")
        
        # แสดง Floor Price Comparison
        st.subheader("📊 เปรียบเทียบ Floor Price")
        
        comparison_cols = ['ประเภท', 'Floor Price', 'Margin (%)']
        comparison_data = [
            {
                'ประเภท': 'ลูกค้าเดิม',
                'Floor Price (บาท)': f"{floor_existing:,.2f}",
                'Net Revenue (บาท)': f"{margin_existing['revenue_details']['net_revenue']:,.2f}",
                'Margin (บาท)': f"{margin_existing['margin_baht']:,.2f}",
                'Margin (%)': f"{margin_existing['margin_percent']:.2f}%",
                'ผลการตรวจสอบ': '✅ ผ่าน' if margin_existing['is_valid'] else '❌ ไม่ผ่าน'
            },
            {
                'ประเภท': 'ลูกค้าใหม่',
                'Floor Price (บาท)': f"{floor_new:,.2f}",
                'Net Revenue (บาท)': f"{margin_new['revenue_details']['net_revenue']:,.2f}",
                'Margin (บาท)': f"{margin_new['margin_baht']:,.2f}",
                'Margin (%)': f"{margin_new['margin_percent']:.2f}%",
                'ผลการตรวจสอบ': '✅ ผ่าน' if margin_new['is_valid'] else '❌ ไม่ผ่าน'
            },
            {
                'ประเภท': 'ถัวเฉลี่ย',
                'Floor Price (บาท)': f"{floor_weighted:,.2f}",
                'Net Revenue (บาท)': f"{net_revenue:,.2f}",
                'Margin (บาท)': f"{margin_weighted['margin_baht']:,.2f}",
                'Margin (%)': f"{margin_weighted['margin_percent']:.2f}%",
                'ผลการตรวจสอบ': '✅ ผ่าน' if margin_weighted['is_valid'] else '❌ ไม่ผ่าน'
            }
        ]

        df_comparison = pd.DataFrame(comparison_data)

        st.dataframe(df_comparison, hide_index=True, width='stretch')
        
        # ผลการตรวจสอบขั้นสุดท้าย (ถัวเฉลี่ย)
        st.write("---")
        
        if margin_weighted['is_valid']:
            st.markdown(f"""
            <div class="success-box">
                <h2>✅ ราคาผ่านการตรวจสอบ!</h2>
                <p style="font-size: 18px;">ราคาที่เสนอสูงกว่า Floor Price ถัวเฉลี่ย</p>
                <p style="font-size: 20px; color: #28a745;"><strong>Margin: {margin_weighted['margin_percent']:.2f}% ({margin_weighted['margin_baht']:,.2f} บาท)</strong></p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="error-box">
                <h2>❌ ราคาไม่ผ่านการตรวจสอบ!</h2>
                <p style="font-size: 18px;">ราคาต่ำกว่า Floor Price ถัวเฉลี่ย</p>
                <p style="font-size: 20px; color: #dc3545;"><strong>ต่ำกว่า {abs(margin_weighted['margin_baht']):,.2f} บาท</strong></p>
            </div>
            """, unsafe_allow_html=True)
        
        # Export Document Button
        st.write("---")
        
        col_export1, col_export2, col_export3 = st.columns([1, 1, 1])
        
        with col_export1:
            # HTML Export
            html_content = doc_export.generate_verification_document_html(log)
            st.download_button(
                label="📄 ดาวน์โหลดเอกสาร HTML",
                data=html_content,
                file_name=f"floor_price_{log.reference_id[:8]}.html",
                mime="text/html",
                width='stretch'
            )
        
        with col_export2:
            # Text Summary
            text_summary = doc_export.generate_simple_summary_text(log)
            st.download_button(
                label="📝 ดาวน์โหลดสรุป TXT",
                data=text_summary,
                file_name=f"summary_{log.reference_id[:8]}.txt",
                mime="text/plain",
                width='stretch'
            )
        
        with col_export3:
            # Mark as exported
            if st.button("✅ บันทึกว่าได้ Export แล้ว", width="stretch", key=f"btn_mark_export_{log.reference_id}"):
                db.mark_as_exported(log.reference_id, st.session_state.user_email)
                st.success("บันทึกสำเร็จ!")
        
        if st.session_state.is_admin:
            with st.expander("🔐 รายละเอียดการคำนวณ (Admin Only)"):
                st.write("**Floor - ลูกค้าเดิม (ไม่รวมค่าติดตั้ง):**")
                st.json(weighted_result['breakdown_existing'])
                st.write("**Floor - ลูกค้าใหม่ (รวมค่าติดตั้ง):**")
                st.json(weighted_result['breakdown_new'])
                st.write("**รายละเอียดค่าติดตั้ง:**")
                st.json(weighted_result['installation_new'])
                st.write("**Revenue Calculation:**")
                st.json(revenue_result)
    
    except Exception as e:
        st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
        import traceback
        with st.expander("🐛 Error Details"):
            st.code(traceback.format_exc())


def user_history_interface():
    """แสดงประวัติการตรวจสอบของ user (Version 2.0 - รองรับ weighted floor)"""
    st.header("📊 ประวัติการตรวจสอบของคุณ")
    
    logs = db.get_user_logs(st.session_state.user_email)
    
    if not logs:
        st.info("ยังไม่มีประวัติการตรวจสอบ")
        return
    
    # Summary metrics
    total_checks = len(logs)
    valid_checks = sum(1 for log in logs if log.is_valid_weighted)
    invalid_checks = total_checks - valid_checks
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ตรวจสอบทั้งหมด", total_checks)
    col2.metric("ผ่าน ✅", valid_checks)
    col3.metric("ไม่ผ่าน ❌", invalid_checks)
    col4.metric("Pass Rate", f"{(valid_checks/total_checks*100):.1f}%")
    
    st.write("---")
    
    # Table
    df = pd.DataFrame([{
        'วันที่': log.checked_at.strftime('%Y-%m-%d %H:%M'),
        'Ref ID': log.reference_id[:8] + '...',
        'ประเภท': '🏠' if log.customer_type == 'residential' else '🏢',
        'ความเร็ว': f"{log.speed} Mbps",
        'ราคาเสนอ': f"{log.proposed_price:,.0f} ฿",
        'ส่วนลด': f"{log.discount_percent}%",
        'Floor ถัวเฉลี่ย': f"{log.floor_weighted:,.0f} ฿",
        'Margin': f"{log.margin_weighted_percent:.1f}%",
        'ผล': '✅ ผ่าน' if log.is_valid_weighted else '❌ ไม่ผ่าน',
        'Export': '📄' if log.exported_at else '-'
    } for log in logs])
    
    st.dataframe(df, width='stretch', hide_index=True)
    
    # Export
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 ดาวน์โหลดประวัติ CSV",
        data=csv,
        file_name=f"my_history_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )


def document_verification_interface():
    """หน้าสำหรับตรวจสอบเอกสารด้วย Reference ID"""
    st.header("🔍 ตรวจสอบเอกสาร")
    st.write("ตรวจสอบความถูกต้องของเอกสารที่ออกจากระบบ")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        reference_id = st.text_input(
            "Reference ID",
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            help="กรอก Reference ID ที่ได้จากเอกสาร"
        )
        
        if st.button("🔍 ตรวจสอบ", type="primary", key="btn_verify_document"):
            if not reference_id:
                st.error("❌ กรุณากรอก Reference ID")
            else:
                log = db.get_price_check_by_reference(reference_id)
                
                if not log:
                    st.error("❌ ไม่พบเอกสารนี้ในระบบ")
                else:
                    st.success("✅ พบเอกสารในระบบ - ข้อมูลถูกต้อง")
                    
                    st.write("---")
                    
                    # Display document details
                    customer_type_th = "🏠 Residential" if log.customer_type == 'residential' else "🏢 Business"
                    
                    col_detail1, col_detail2 = st.columns(2)
                    
                    with col_detail1:
                        st.write("**ข้อมูลเอกสาร:**")
                        st.write(f"• Reference ID: `{log.reference_id}`")
                        st.write(f"• ผู้ตรวจสอบ: {log.user_email}")
                        st.write(f"• วันที่: {log.checked_at.strftime('%d/%m/%Y %H:%M')}")
                        st.write(f"• ประเภท: {customer_type_th}")
                    
                    with col_detail2:
                        st.write("**รายละเอียดแพ็คเกจ:**")
                        st.write(f"• ความเร็ว: {log.speed} Mbps")
                        st.write(f"• สัญญา: {log.contract_months} เดือน")
                        st.write(f"• ราคาเสนอ: {log.proposed_price:,.2f} ฿")
                        st.write(f"• ส่วนลด: {log.discount_percent}%")
                    
                    st.write("---")
                    
                    # Verification results
                    col_result1, col_result2, col_result3 = st.columns(3)
                    
                    col_result1.metric(
                        "Floor - ลูกค้าเดิม",
                        f"{log.floor_existing:,.2f} ฿",
                        delta="✅" if log.is_valid_existing else "❌"
                    )
                    
                    col_result2.metric(
                        "Floor - ลูกค้าใหม่",
                        f"{log.floor_new:,.2f} ฿",
                        delta="✅" if log.is_valid_new else "❌"
                    )
                    
                    col_result3.metric(
                        "Floor - ถัวเฉลี่ย",
                        f"{log.floor_weighted:,.2f} ฿",
                        delta="✅" if log.is_valid_weighted else "❌"
                    )
                    
                    st.write("---")
                    
                    if log.is_valid_weighted:
                        st.markdown(f"""
                        <div class="success-box">
                            <h3>✅ เอกสารนี้ได้รับการอนุมัติ</h3>
                            <p>Margin: {log.margin_weighted_percent:.2f}%</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div class="error-box">
                            <h3>❌ เอกสารนี้ไม่ผ่านการตรวจสอบ</h3>
                            <p>Margin: {log.margin_weighted_percent:.2f}%</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Export info
                    if log.exported_at:
                        st.info(f"📄 เอกสารนี้ถูก export โดย {log.exported_by} เมื่อ {log.exported_at.strftime('%d/%m/%Y %H:%M')} (จำนวน {log.export_count} ครั้ง)")
                    
                    # Re-export
                    st.write("---")
                    col_reexport1, col_reexport2 = st.columns(2)
                    
                    with col_reexport1:
                        html_content = doc_export.generate_verification_document_html(log)
                        st.download_button(
                            label="📄 ดาวน์โหลดเอกสาร HTML อีกครั้ง",
                            data=html_content,
                            file_name=f"floor_price_{log.reference_id[:8]}.html",
                            mime="text/html",
                            width='stretch'
                        )
                    
                    with col_reexport2:
                        text_summary = doc_export.generate_simple_summary_text(log)
                        st.download_button(
                            label="📝 ดาวน์โหลดสรุป TXT อีกครั้ง",
                            data=text_summary,
                            file_name=f"summary_{log.reference_id[:8]}.txt",
                            mime="text/plain",
                            width='stretch'
                        )
    
    with col2:
        st.info("""
        **💡 วิธีใช้งาน:**
        
        1. ดูเอกสารที่ได้รับ
        2. คัดลอก Reference ID
        3. วางใน textbox
        4. กดตรวจสอบ
        
        **📌 หมายเหตุ:**
        - เอกสารทุกฉบับมี Reference ID เฉพาะ
        - สามารถตรวจสอบได้ตลอดเวลา
        - ข้อมูลจะตรงกับที่บันทึกในระบบ
        """)


def comparison_table_interface():
    """หน้าตารางเปรียบเทียบราคาตาม Bandwidth"""
    st.header("📈 ตารางเปรียบเทียบราคา")
    st.write("เปรียบเทียบ Floor Price ตามความเร็วอินเทอร์เน็ต")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Parameters
        customer_type = st.selectbox(
            "ประเภทลูกค้า",
            options=['residential', 'business'],
            format_func=lambda x: "🏠 Residential" if x == 'residential' else "🏢 Business"
        )
        
        contract_months = st.selectbox(
            "ระยะสัญญา",
            options=[12, 24, 36],
            index=1
        )
        
        distance = st.number_input(
            "ระยะทางติดตั้ง (กม.)",
            min_value=0.0,
            max_value=10.0,
            value=1.0,
            step=0.5
        )
    
    with col2:
        has_fixed_ip = st.checkbox("รวม Fixed IP")
        
        existing_ratio = st.slider(
            "สัดส่วนลูกค้าเดิม (%)",
            min_value=0,
            max_value=100,
            value=70,
            step=5
        ) / 100
        
        discount_percent = st.number_input(
            "ส่วนลด (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=5.0
        )
    
    # Equipment selection
    st.write("**เลือกอุปกรณ์:**")
    equipment_list = st.multiselect(
        "อุปกรณ์",
        options=list(Config.EQUIPMENT_PRICES.keys()),
        default=['ONU ZTE F612 (No WiFi + 1POTS)'],
        key="comparison_equipment"
    )
    
    if st.button("สร้างตารางเปรียบเทียบ", type="primary", key="btn_create_comparison_table"):
        with st.spinner("กำลังคำนวณ..."):
            try:
                # Generate comparison table
                table_data = fp.generate_bandwidth_comparison_table(
                    customer_type, equipment_list, contract_months,
                    has_fixed_ip, discount_percent, existing_ratio, distance
                )
                
                # Create DataFrame
                df = pd.DataFrame(table_data)
                
                # Add proposed price comparison columns
                st.write("---")
                st.subheader("ตารางเปรียบเทียบ Floor Price")

                formatters = {
                    'floor_existing': '{:,.2f}',
                    'floor_new': '{:,.2f}',
                    'floor_weighted': '{:,.2f}'
                }
                if 'margin_percent' in df.columns:
                    formatters['margin_percent'] = '{:,.2f}'
                if 'margin_baht' in df.columns:
                    formatters['margin_baht'] = '{:,.2f}'

                st.dataframe(df.style.format(formatters), width='stretch')
                
                # Plot
                st.write("---")
                st.subheader("📈 กราฟเปรียบเทียบ")
                
                import plotly.graph_objects as go
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df['speed'],
                    y=df['floor_existing'],
                    mode='lines+markers',
                    name='ลูกค้าเดิม',
                    line=dict(color='blue', width=2)
                ))
                
                fig.add_trace(go.Scatter(
                    x=df['speed'],
                    y=df['floor_new'],
                    mode='lines+markers',
                    name='ลูกค้าใหม่',
                    line=dict(color='red', width=2)
                ))
                
                fig.add_trace(go.Scatter(
                    x=df['speed'],
                    y=df['floor_weighted'],
                    mode='lines+markers',
                    name='ถัวเฉลี่ย',
                    line=dict(color='green', width=3, dash='dash')
                ))
                
                fig.update_layout(
                    title="Floor Price vs ความเร็ว",
                    xaxis_title="ความเร็ว (Mbps)",
                    yaxis_title="Floor Price (฿/เดือน)",
                    hovermode='x unified',
                    height=500
                )
                
                st.plotly_chart(fig, config={'responsive': True})
                
                # Export table
                st.write("---")
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 ดาวน์โหลดตาราง CSV",
                    data=csv,
                    file_name=f"floor_price_comparison_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาด: {str(e)}")
                import traceback
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
        
        if st.button("➕ เพิ่มผู้ใช้", type="primary", key="btn_add_user"):
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
        if st.button("🚀 สร้าง Default Config", key="btn_create_default_when_empty"):
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
                    st.metric("ค่าระยะทาง", f"{config.distance_price_residential} ฿/จุดติดตั้ง")
                with col_b:
                    st.metric("ระยะมาตรฐาน", f"{config.max_distance_residential} m")
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
                    st.metric("ค่าระยะทาง", f"{config.distance_price_business} ฿/จุดติดตั้ง")
                with col_b:
                    st.metric("ระยะมาตรฐาน", f"{config.max_distance_business} m")
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
        
        if st.button("📋 คัดลอก Config", type="primary", key="btn_duplicate_config"):
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
    if st.button("🚀 สร้าง Default Config", key="btn_create_default_from_config"):
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
            if st.button("📥 Export เป็น JSON", key=f"btn_export_config_{export_config}"):
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
    
    if st.button("📤 Import จาก JSON", type="primary", key="btn_import_config"):
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


def admin_dashboard():
    """Admin dashboard - แสดง floor price และ log ทั้งหมด"""
    st.header("🔧 Admin Dashboard")
    
    # Summary
    all_logs = db.get_all_logs(limit=500)
    
    if not all_logs:
        st.info("ยังไม่มีข้อมูล")
        return
    
    total = len(all_logs)
    valid = sum(1 for log in all_logs if log.is_valid_weighted)
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
        
        if st.button("🔍 คำนวณ", width='stretch', key="btn_admin_calculate"):
            try:
                result = fp.calculate_floor_price(
                    customer_type=calc_customer_type,
                    speed=calc_speed,
                    distance=calc_distance,
                    equipment_list=[],
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
                        if breakdown.get('interpolated', False) and 'speed_lower' in breakdown:
                            st.caption(f"  └ คำนวณจาก {breakdown['speed_lower']} → {breakdown.get('speed_upper', breakdown['speed_lower'])} Mbps")
                        if breakdown.get('fixed_ip_cost', 0) > 0:
                            st.write(f"- Fixed IP: {breakdown['fixed_ip_cost']:,.2f} ฿")
                        st.write(f"- อุปกรณ์: {breakdown['equipment_cost']:,.2f} ฿")
                        st.write(f"- ค่าติดตั้งเพิ่มต่อเดือน (กรณีระยะทางเกิน): {breakdown['installation_extra_cost']:,.2f} ฿")
                    
                    with col_b:
                        st.write("**ส่วนลดและเพิ่มเติม:**")
                        if breakdown.get('business_premium', 0) > 0:
                            st.write(f"- Business Premium (+10%): +{breakdown['business_premium']:,.2f} ฿")
                        st.write(f"- ส่วนลด {breakdown['contract_months']} เดือน ({breakdown['discount_rate']*100:.0f}%): -{breakdown['discount_amount']:,.2f} ฿")
                        st.write(f"**รวมสุทธิ: {floor:,.2f} ฿/เดือน**")
                    st.info(
                        f"ค่าติดตั้งรวม (กรณีลูกค้าใหม่): {result['installation_details']['total_cost']:,.2f} บาท "
                        f"(~{result['installation_details']['total_cost'] / calc_contract:,.2f} ฿/เดือน)"
                    )
                    
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
        'ประเภท': '🏠' if log.customer_type == 'residential' else '🏢',
        'ความเร็ว': log.speed,
        'ระยะทาง': log.distance,
        'Fixed IP': '✅' if log.has_fixed_ip else '❌',
        'อุปกรณ์': log.equipment,
        'สัญญา': log.contract_months,
        'ราคาเสนอ': log.proposed_price,
        'Floor (Weighted)': log.floor_weighted,
        'ผ่าน': '✅' if log.is_valid_weighted else '❌',
        'Margin%': round(log.margin_weighted_percent, 1) if log.margin_weighted_percent else 0,
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