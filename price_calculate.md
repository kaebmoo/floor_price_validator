# Floor Price Calculation Guide

## 1. Input Parameters

| Parameter | Description |
| --- | --- |
| `customer_type` | `residential` หรือ `business` |
| `speed` | ความเร็ว Mbps ที่เสนอ |
| `distance` | ระยะทางติดตั้ง (กม.) ใช้คำนวณค่าติดตั้งเกินระยะพื้นฐาน |
| `equipment_list` | รายการอุปกรณ์ (ใช้ชื่อ SKU ตาม `Config.EQUIPMENT_PRICES`) |
| `contract_months` | ระยะสัญญา (12 / 24 / 36 เดือน) |
| `has_fixed_ip` | ต้องการ Fixed IP หรือไม่ |
| `discount_percent` | ส่วนลด (%) ที่ให้ลูกค้า |
| `existing_customer_ratio` | สัดส่วนลูกค้าเดิม (0-1) สำหรับคำนวณค่าเฉลี่ยแบบถัว |
| `proposed_price` | ราคาขายที่เสนอ (ต่อเดือน) |

## 2. Base Floor Calculation (Existing Customers)

1. **โหลดราคาแพ็กเกจ**
   - ดึงจาก active config ใน database (ถ้ามี) มิฉะนั้นใช้ค่าใน `config.py`
   - หากความเร็วไม่ตรงแพ็กเกจ → interpolate ตามช่วงที่มี (ดู `floor_price.py::calculate_floor_price`)

2. **บวกค่า Fixed IP (ถ้ามี)**
   - ใช้ค่าตามประเภทลูกค้า (`Config.FIXED_IP_PRICE` หรือค่า override)

3. **บวกต้นทุนอุปกรณ์**
   - รวมราคาตาม SKU ใน `equipment_list`

4. **Business Premium (เฉพาะ business)**
   - คิดเพิ่มตาม `business_premium_percent`

5. **หักส่วนลดตามระยะสัญญา**
   - ใช้ `CONTRACT_DISCOUNTS` ของประเภทลูกค้า

> ผลลัพธ์ = `floor_existing` (บาท/เดือน) — ไม่รวมค่าติดตั้ง

## 3. Installation Cost (New Customers)

1. **ดึง config ค่าติดตั้ง**
   - `base_cost` และ `base_length_m` ต่อประเภทลูกค้า
   - `extra_cost_per_meter` สำหรับระยะเกิน

2. **คำนวณระยะจริง**
   - `distance_km × 1000` → `distance_m`
   - `extra_distance = max(distance_m - base_length_m, 0)`

3. **คิดค่าติดตั้งทั้งหมด**
   - `total_install_cost = base_cost + extra_distance × extra_cost_per_meter`

4. **กระจายตามสัญญา**
   - `installation_monthly = total_install_cost / contract_months`

5. **รวมกับ `floor_existing`**
   - `floor_new = floor_existing + installation_monthly`

## 4. Weighted Floor

```
existing_ratio = existing_customer_ratio
new_ratio = 1 - existing_ratio
floor_weighted = floor_existing * existing_ratio + floor_new * new_ratio
```

## 5. Net Revenue After Discount & Regulator Fee

```
discount_amount = proposed_price * (discount_percent / 100)
price_after_discount = proposed_price - discount_amount
regulator_fee = price_after_discount * 0.04
net_revenue = price_after_discount - regulator_fee
```

ผลลัพธ์ถูกปัดเศษสองตำแหน่งก่อนแสดง (ดู `calculate_net_revenue_after_fees`).

## 6. Margin Metrics

สำหรับแต่ละ floor (existing, new, weighted):

```
margin_baht = net_revenue - floor_price
margin_percent = (margin_baht / net_revenue) * 100 if net_revenue > 0 else 0
is_valid = net_revenue >= floor_price
```

> หมายเหตุ: `margin_percent` ใช้ **net revenue** เป็นตัวหาร ตามข้อกำหนดธุรกิจล่าสุด

## 7. Validation Rules

- **ผ่าน (✅)** เมื่อ `net_revenue >= floor_weighted`
- ค่า `is_valid_existing` / `is_valid_new` ใช้เงื่อนไขเดียวกันกับ floor แต่ละประเภท
- ระบบบันทึกผลทั้งหมดในตาราง `price_checks` พร้อม `reference_id`

## 8. Comparison Table Generation

`generate_bandwidth_comparison_table` จะวนลูปทุกความเร็วใน config ปัจจุบันและคำนวณค่าต่าง ๆ แบบเดียวกับขั้นตอนด้านบน โดยมีการตั้งค่า margin เป็น 0 หากไม่มี `proposed_price` กำหนดสำหรับความเร็วนั้น

## 9. Example Walkthrough

ตัวอย่าง: Residential, 500 Mbps, ระยะ 0.315 กม., อุปกรณ์ `["ONU ZTE F612 (No WiFi + 1POTS)", "WiFi 6 Router (AX.1200)"]`, สัญญา 12 เดือน, ไม่มีส่วนลด, ไม่มี Fixed IP, สัดส่วนลูกค้าเดิม 70%

1. Base speed + equipment + premium → `floor_existing ≈ 640.00`
2. Installation: base cost ครอบคลุม 0.315 กม. → `installation_monthly ≈ 0`
3. Weighted floor: `floor_weighted = 640 * 0.7 + 640 * 0.3 = 640`
4. Net revenue ที่ราคาเสนอ 800 บาท: `net_revenue = (800 - 0) * 0.96 = 768`
5. Margin: `margin_baht = 128`, `margin_percent ≈ 16.67%`
6. เนื่องจาก `768 ≥ 640` → ผ่าน

## 10. Data Persistence

เมื่อกด “🔍 ตรวจสอบราคา” ระบบจะบันทึก:
- ราคาที่ใช้ (`floor_existing`, `floor_new`, `floor_weighted`)
- รายได้สุทธิและค่าธรรมเนียม
- Margin (บาท/%) สำหรับลูกค้าเดิม/ใหม่/ถัวเฉลี่ย
- `is_valid_*`, `reference_id`, ข้อมูลผู้ใช้, หมายเหตุ, export flags

## 11. References

- `floor_price.py` – source of all formulas
- `floor_price_plan.md` – อ้างอิงค่าราคาและอุปกรณ์ล่าสุด
- `app.py` – จุดเชื่อมกับ UI/Logging
