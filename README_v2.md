# Floor Price Validator v2.0 – Product Manual

## 1. System Overview

- คำนวณ Floor Price แยกตามประเภทลูกค้า (เดิม/ใหม่) และถัวเฉลี่ยตามสัดส่วน
- รองรับส่วนลด (%) และค่าธรรมเนียม กสทช. 4% เพื่อให้ได้รายได้สุทธิจริง
- Margin (บาท/%) ใช้รายได้สุทธิเป็นฐานตาม requirement ล่าสุด
- ทุกการตรวจสอบสร้าง Reference ID พร้อมเอกสาร HTML/TXT และบันทึกสถานะการ export
- มีเครื่องมือวิเคราะห์ราคา (comparison table + plotly chart + CSV export)
- มี Document Verification สำหรับตรวจสอบผลย้อนหลังด้วย Reference ID
- Admin Dashboard ให้จัดการผู้ใช้, ปรับ config, ตรวจสอบ log และสถิติ

## 2. Architecture Snapshot

| Layer | Description |
| --- | --- |
| Config | `config.py` (default) + `pricing_configs` ใน DB (override) |
| Business Logic | `floor_price.py` ประกอบด้วยฟังก์ชันคำนวณทั้งหมด |
| Persistence | `database.py` (SQLAlchemy + SQLite), `ensure_price_checks_schema()` สำหรับ migrate in-place |
| Presentation | Streamlit app (`app.py`) แบ่งแท็บตามการใช้งาน |
| Documents | `document_export.py` สร้าง HTML/TXT ใช้ข้อมูลจากตาราง `price_checks` |

## 3. Calculation Flow (ย่อ)

1. โหลด config (จาก DB ถ้ามี active entry)
2. คำนวณ `floor_existing` → base price + อุปกรณ์ + premium (ธุรกิจ) - contract discount
3. คำนวณค่าติดตั้งและกระจายต่อเดือน → `floor_new`
4. ถัวเฉลี่ยตามสัดส่วนลูกค้า → `floor_weighted`
5. หักส่วนลดและค่าธรรมเนียม 4% → `net_revenue`
6. Margin = `net_revenue - floor_price`; Margin% = `(margin / net_revenue) × 100`
7. เปรียบเทียบเพื่อให้ผลผ่าน/ไม่ผ่าน และบันทึกลง DB

## 4. Streamlit Tabs

### 4.1 ✅ ตรวจสอบราคา
- กรอกข้อมูลแพ็กเกจ, ส่วนลด, สัดส่วนลูกค้า
- กดตรวจสอบ → ดู Floor/Margin และผลผ่าน/ไม่ผ่าน
- ดาวน์โหลด HTML/TXT, เก็บ Reference ID, บันทึก export flag

### 4.2 🔍 ตรวจสอบเอกสาร
- ใส่ Reference ID → ดูผลการตรวจสอบครั้งก่อน, re-export เอกสาร

### 4.3 📈 ตารางเปรียบเทียบ
- เลือกเงื่อนไขมาตรฐาน → ตาราง floor ทุกความเร็ว + กราฟ Plotly + CSV export
- Plotly ใช้ `config={'responsive': True}` ตาม API ล่าสุด

### 4.4 📊 ประวัติของฉัน
- แสดงรายการที่ผู้ใช้คนปัจจุบันตรวจสอบ พร้อม margin และสถานะ export

### 4.5 🔧 Admin Dashboard (เฉพาะ admin)
- จัดการผู้ใช้ (เพิ่ม/ปิดการใช้งาน/ให้สิทธิ์ admin)
- ดูสถิติภาพรวมและ log การส่งออก
- ปรับ pricing config ที่ใช้คำนวณในระบบ

## 5. Database Schema Highlights

### price_checks
- เก็บ input + output ทุกอย่าง (floor, margin, net revenue, regulator fee, validity flags)
- บันทึกข้อมูลเอกสาร (`reference_id`, `exported_at`, `exported_by`, `export_count`)
- ใช้ `ensure_price_checks_schema()` เพื่อเพิ่มคอลัมน์ใหม่โดยไม่ทำลายข้อมูลเก่า

### pricing_configs
- สามารถเก็บหลายชุด (active/inactive)
- ค่าติดตั้งถูกบันทึกเป็น base cost, base length (เมตร), extra cost per meter

## 6. Setup Instructions

1. สร้าง virtualenv → `pip install -r requirements.txt`
2. `python -c "import database; print('schema ensured')"` เพื่อ migrate schema
3. (ออปชัน) `python migrate_to_v2.py` สำหรับตรวจสอบไฟล์/แพ็กเกจ/คำนวณตัวอย่าง
4. รัน `streamlit run app.py`
5. รัน `pytest` เพื่อตรวจสอบ unit test ที่มี และเพิ่ม test ตามต้องการ

## 7. Maintenance & Tips

- เมื่ออัปเดต config ผ่าน UI → ตาราง `pricing_configs` จะถูกเปลี่ยนและนำไปใช้ทันทีในการคำนวณครั้งถัดไป
- Margin (%) ใช้ net revenue เป็นฐาน ตรวจสอบแล้วว่าตรงกับข้อกำหนดผู้ใช้
- ปุ่มใน UI มี key เฉพาะแก้ปัญหา duplicate-element
- ค่าเริ่มต้นของระยะติดตั้งใน UI = 0.315 กม. (315 ม.) ตามแผนงานติดตั้งมาตรฐาน

## 8. Known Enhancements (Roadmap)

- PDF export พร้อมฟอนต์ไทย
- อีเมลเอกสาร + ลายเซ็นดิจิทัล
- QR code verification สำหรับเอกสาร
- Analytics dashboard ขยายผล (margin trends, approval rate)

## 9. Reference Documents

- `QUICKSTART.md` – คู่มือเร็วสำหรับผู้ใช้งานธุรกิจ
- `price_calculate.md` – อธิบายสูตรแบบละเอียดพร้อมตัวอย่าง
- `floor_price_plan.md` – แผนราคา (truth source)

_ปรับปรุงล่าสุด: สอดคล้องกับโค้ดบนสาขา `main` หลังการ refactor v2.0_
