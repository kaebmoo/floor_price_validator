import streamlit as st
import streamlit.components.v1 as components
import database as db
import document_export as doc_export


st.set_page_config(page_title="Floor Price Verification", page_icon="🔍", layout="wide")

try:
    MAIN_APP_URL = st.secrets["MAIN_APP_URL"]
except (KeyError, FileNotFoundError):
    import os

    MAIN_APP_URL = os.environ.get("MAIN_APP_URL")


def _ensure_query_redirect():
    """Force /verify/<reference_id> paths to /verify?reference_id=<reference_id> for Streamlit."""
    components.html(
        """
        <script>
        (function() {
            const searchParams = new URLSearchParams(window.location.search);
            if (searchParams.has("reference_id")) {
                return;
            }
            const segments = window.location.pathname.split("/").filter(Boolean);
            if (segments.length >= 2 && segments[segments.length - 2] === "verify") {
                const refId = segments[segments.length - 1];
                if (refId) {
                    const origin = window.location.origin;
                    const hash = window.location.hash || "";
                    const newUrl = `${origin}/verify?reference_id=${encodeURIComponent(refId)}${hash}`;
                    window.location.replace(newUrl);
                }
            }
        })();
        </script>
        """,
        height=0,
        width=0
    )


def _extract_reference_id():
    params = st.experimental_get_query_params()
    ref_list = params.get("reference_id")
    ref = ref_list[0] if ref_list else ""
    return ref.strip()


def _load_price_check(reference_id: str):
    if not reference_id:
        return None
    return db.get_price_check_by_reference(reference_id)


def _render_verification_result(log):
    st.subheader("ผลการตรวจสอบเอกสาร")
    status_box = st.container()
    with status_box:
        if log.is_valid_weighted:
            st.success("✅ เอกสารนี้ได้รับการอนุมัติ")
        else:
            st.error("❌ เอกสารนี้ไม่ผ่านการตรวจสอบ")

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        st.write(f"**Reference ID:** `{log.reference_id}`")
        st.write(f"**ผู้ออกเอกสาร:** {log.user_email}")
        st.write(f"**วันที่ตรวจสอบ:** {log.checked_at.strftime('%d/%m/%Y %H:%M')} น.")
        if log.exported_at:
            st.info(
                f"📄 เอกสารถูกส่งออกโดย {log.exported_by} เมื่อ {log.exported_at.strftime('%d/%m/%Y %H:%M')} น."
            )

    with col_meta2:
        st.write("**รายละเอียดแพ็กเกจ:**")
        st.write(f"• ประเภทลูกค้า: {'🏠 Residential' if log.customer_type == 'residential' else '🏢 Business'}")
        st.write(f"• ความเร็ว: {log.speed} Mbps")
        st.write(f"• ระยะทาง: {log.distance} กม.")
        st.write(f"• สัญญา: {log.contract_months} เดือน")
        st.write(f"• ราคาเสนอ: {log.proposed_price:,.2f} ฿")
        st.write(f"• ส่วนลด: {log.discount_percent:.2f}%")

    st.write("---")

    col_floor1, col_floor2, col_floor3 = st.columns(3)
    col_floor1.metric("Floor - ลูกค้าเดิม", f"{log.floor_existing:,.2f} ฿", "ผ่าน" if log.is_valid_existing else "ไม่ผ่าน")
    col_floor2.metric("Floor - ลูกค้าใหม่", f"{log.floor_new:,.2f} ฿", "ผ่าน" if log.is_valid_new else "ไม่ผ่าน")
    col_floor3.metric(
        "Floor - ถัวเฉลี่ย",
        f"{log.floor_weighted:,.2f} ฿",
        "ผ่าน" if log.is_valid_weighted else "ไม่ผ่าน"
    )

    st.write("---")

    col_margin1, col_margin2, col_margin3 = st.columns(3)

    def format_metric(val, fallback="-"):
        return fallback if val is None else f"{val:.2f}"

    def format_currency(val):
        return "-" if val is None else f"{val:,.2f}"

    col_margin1.metric(
        "Margin ลูกค้าเดิม",
        f"{format_metric(log.margin_existing_percent)}%",
        f"{format_currency(log.margin_existing_baht)} ฿"
    )
    col_margin2.metric(
        "Margin ลูกค้าใหม่",
        f"{format_metric(log.margin_new_percent)}%",
        f"{format_currency(log.margin_new_baht)} ฿"
    )
    col_margin3.metric(
        "Margin ถัวเฉลี่ย",
        f"{format_metric(log.margin_weighted_percent)}%",
        f"{format_currency(log.margin_weighted_baht)} ฿"
    )

    st.write("---")
    col_download1, col_download2 = st.columns(2)
    with col_download1:
        html_content = doc_export.generate_verification_document_html(log)
        st.download_button(
            label="📄 ดาวน์โหลดเอกสาร HTML",
            data=html_content,
            file_name=f"floor_price_{log.reference_id[:8]}.html",
            mime="text/html",
            use_container_width=True
        )

    with col_download2:
        text_summary = doc_export.generate_simple_summary_text(log)
        st.download_button(
            label="📝 ดาวน์โหลดสรุป TXT",
            data=text_summary,
            file_name=f"summary_{log.reference_id[:8]}.txt",
            mime="text/plain",
            use_container_width=True
        )

    if log.notes:
        st.write("---")
        st.caption(f"หมายเหตุ: {log.notes}")

    st.write("---")
    if st.button("🔄 ตรวจสอบ Reference ID อื่น", key="btn_check_another"):
        st.experimental_set_query_params()
        st.rerun()


def main():
    st.title("🔍 Floor Price Verification Portal")
    st.caption("สำหรับผู้ตรวจสอบเอกสารยืนยันการตรวจสอบราคา")

    if MAIN_APP_URL:
        st.markdown(f"[⬅️ กลับสู่ระบบตรวจสอบราคา]({MAIN_APP_URL})")

    _ensure_query_redirect()
    reference_id = _extract_reference_id()
    log = _load_price_check(reference_id)

    if log:
        _render_verification_result(log)
        return

    st.info("กรุณาระบุ Reference ID เพื่อตรวจสอบเอกสาร")
    manual_ref = st.text_input(
        "Reference ID",
        value=reference_id,
        placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        key="reference_input"
    )
    submit = st.button("ตรวจสอบ", type="primary")

    if submit:
        ref_to_check = manual_ref.strip()
        if not ref_to_check:
            st.error("❌ กรุณากรอก Reference ID")
            return

        result = _load_price_check(ref_to_check)
        if result:
            st.experimental_set_query_params(reference_id=result.reference_id)
            st.rerun()
        else:
            st.error("❌ ไม่พบข้อมูลสำหรับ Reference ID นี้")


if __name__ == "__main__":
    main()
