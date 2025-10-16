# Floor Price Calculation Documentation
# คู่มือการคำนวณ Floor Price

## สารบัญ
1. [ภาพรวมระบบ](#ภาพรวมระบบ)
2. [ส่วนประกอบของการคำนวณ](#ส่วนประกอบของการคำนวณ)
3. [สูตรคำนวณ Floor Price](#สูตรคำนวณ-floor-price)
4. [Interpolation Algorithm](#interpolation-algorithm)
5. [ตัวอย่างการคำนวณ](#ตัวอย่างการคำนวณ)
6. [Configuration Management](#configuration-management)

---

## ภาพรวมระบบ

Floor Price Validator เป็นระบบตรวจสอบราคาขั้นต่ำสำหรับบริการ Broadband โดยคำนวณจาก:
- ประเภทลูกค้า (Residential/Business)
- ความเร็วอินเทอร์เน็ต (Mbps)
- ระยะทางการติดตั้ง (km)
- อุปกรณ์เสริม
- ระยะเวลาสัญญา
- Fixed IP (ถ้ามี)

---

## ส่วนประกอบของการคำนวณ

### 1. ราคาพื้นฐานตามความเร็ว (Base Price)

#### แพ็คเกจมาตรฐาน
```python
# Residential
100 Mbps  = 500 บาท/เดือน
200 Mbps  = 800 บาท/เดือน
500 Mbps  = 1,500 บาท/เดือน
1000 Mbps = 2,500 บาท/เดือน

# Business (แพงกว่า ~60%)
100 Mbps  = 800 บาท/เดือน
200 Mbps  = 1,200 บาท/เดือน
500 Mbps  = 2,200 บาท/เดือน
1000 Mbps = 3,500 บาท/เดือน
```

#### Custom Speed (Interpolation)
สำหรับความเร็วที่ไม่ใช่แพ็คเกจมาตรฐาน ระบบจะคำนวณด้วยวิธี:

**กรณี 1: ความเร็วอยู่ระหว่างแพ็คเกจ (Linear Interpolation)**
```python
ratio = (speed - speed_lower) / (speed_upper - speed_lower)
base_price = price_lower + ratio * (price_upper - price_lower)

# ตัวอย่าง: 300 Mbps (Residential)
# ระหว่าง 200 Mbps (800฿) และ 500 Mbps (1500฿)
ratio = (300 - 200) / (500 - 200) = 0.333
base_price = 800 + 0.333 * (1500 - 800) = 1,033 บาท
```

**กรณี 2: ความเร็วสูงกว่าแพ็คเกจสูงสุด (Extrapolation)**
```python
# คำนวณ slope จาก 2 แพ็คเกจสุดท้าย
slope = (price_last - price_second) / (speed_last - speed_second)
extra_price = slope * (speed - speed_last)
base_price = price_last + min(extra_price, price_last * 0.5)  # Cap at 50%

# ตัวอย่าง: 1500 Mbps (Residential)
# สูงกว่า 1000 Mbps (2500฿), slope จาก 500->1000 Mbps
slope = (2500 - 1500) / (1000 - 500) = 2 บาท/Mbps
extra_price = 2 * (1500 - 1000) = 1000 บาท
base_price = 2500 + min(1000, 1250) = 3,500 บาท
```

**กรณี 3: ความเร็วต่ำกว่าแพ็คเกจต่ำสุด**
```python
# ใช้ราคาแพ็คเกจต่ำสุด
base_price = price_of_minimum_package

# ตัวอย่าง: 50 Mbps -> ใช้ราคา 100 Mbps
```

---

### 2. ค่าระยะทางติดตั้ง (Distance Cost)
```python
# อัตราค่าระยะทาง
residential: 50 บาท/กม.
business: 100 บาท/กม.

# ระยะมาตรฐาน
residential: ไม่เกิน 5 กม.
business: ไม่เกิน 10 กม.

# การคำนวณ
if distance <= max_standard_distance:
    distance_cost = distance * rate_per_km
else:
    standard_cost = max_distance * rate_per_km
    extra_distance = distance - max_distance
    extra_cost = extra_distance * rate_per_km * 1.5  # คูณ 1.5 เท่า
    distance_cost = standard_cost + extra_cost

# ตัวอย่าง: Residential, 7 กม.
standard_cost = 5 * 50 = 250 บาท
extra_cost = (7 - 5) * 50 * 1.5 = 150 บาท
total_distance_cost = 400 บาท
```

---

### 3. Fixed IP (ถ้ามี)
```python
residential: 300 บาท/เดือน
business: 500 บาท/เดือน (มี SLA ดีกว่า)
```

---

### 4. ค่าอุปกรณ์ (Equipment Cost)
```python
standard_router    = 0 บาท (ฟรี)
wifi6_router      = 500 บาท
mesh_system       = 1,500 บาท
ont               = 300 บาท
managed_switch    = 800 บาท (Business only)
enterprise_router = 2,000 บาท (Business only)

# รวมค่าอุปกรณ์ทั้งหมดที่เลือก
equipment_cost = sum(selected_equipment_prices)
```

---

### 5. Business Premium (เฉพาะธุรกิจ)
```python
# เพิ่ม 10% สำหรับ SLA และ Support 24/7
if customer_type == 'business':
    business_premium = subtotal * 0.10
```

---

### 6. ส่วนลดตามระยะสัญญา (Contract Discount)
```python
# Residential
12 เดือน: ลด 5%
24 เดือน: ลด 10%
36 เดือน: ลด 15%

# Business (ส่วนลดน้อยกว่า)
12 เดือน: ลด 3%
24 เดือน: ลด 7%
36 เดือน: ลด 12%

discount_amount = subtotal_with_premium * discount_rate
```

---

## สูตรคำนวณ Floor Price
```python
def calculate_floor_price():
    # Step 1: คำนวณราคาพื้นฐาน (อาจใช้ interpolation)
    base_price = get_speed_price(customer_type, speed)
    
    # Step 2: คำนวณค่าระยะทาง
    distance_cost = calculate_distance_cost(distance, customer_type)
    
    # Step 3: เพิ่ม Fixed IP (ถ้ามี)
    fixed_ip_cost = get_fixed_ip_price(customer_type) if has_fixed_ip else 0
    
    # Step 4: รวมค่าอุปกรณ์
    equipment_cost = sum(equipment_prices)
    
    # Step 5: คำนวณ Subtotal
    subtotal = base_price + distance_cost + fixed_ip_cost + equipment_cost
    
    # Step 6: เพิ่ม Business Premium (ถ้าเป็น Business)
    business_premium = subtotal * 0.10 if customer_type == 'business' else 0
    subtotal_with_premium = subtotal + business_premium
    
    # Step 7: หักส่วนลดตามสัญญา
    discount_amount = subtotal_with_premium * contract_discount_rate
    
    # Step 8: Floor Price สุดท้าย
    floor_price = subtotal_with_premium - discount_amount
    
    return floor_price
```

---

## ตัวอย่างการคำนวณ

### ตัวอย่าง 1: Residential Standard Package
```
ประเภท: Residential
ความเร็ว: 200 Mbps (แพ็คเกจมาตรฐาน)
ระยะทาง: 3 กม.
Fixed IP: ไม่มี
อุปกรณ์: Standard Router
สัญญา: 24 เดือน

คำนวณ:
1. Base Price: 800 บาท (200 Mbps residential)
2. Distance: 3 * 50 = 150 บาท
3. Fixed IP: 0 บาท
4. Equipment: 0 บาท
5. Subtotal: 800 + 150 = 950 บาท
6. Business Premium: 0 บาท (ไม่ใช่ business)
7. ส่วนลด 24 เดือน (10%): 950 * 0.10 = 95 บาท
8. Floor Price: 950 - 95 = 855 บาท/เดือน
```

### ตัวอย่าง 2: Business Custom Speed
```
ประเภท: Business
ความเร็ว: 750 Mbps (Custom - ต้อง interpolate)
ระยะทาง: 12 กม. (เกินมาตรฐาน)
Fixed IP: มี
อุปกรณ์: WiFi6 Router + Managed Switch
สัญญา: 36 เดือน

คำนวณ:
1. Base Price (Interpolation):
   - อยู่ระหว่าง 500 Mbps (2,200฿) และ 1000 Mbps (3,500฿)
   - ratio = (750-500)/(1000-500) = 0.5
   - base_price = 2,200 + 0.5*(3,500-2,200) = 2,850 บาท

2. Distance:
   - Standard (10 km): 10 * 100 = 1,000 บาท
   - Extra (2 km): 2 * 100 * 1.5 = 300 บาท
   - Total: 1,300 บาท

3. Fixed IP: 500 บาท

4. Equipment: 500 + 800 = 1,300 บาท

5. Subtotal: 2,850 + 1,300 + 500 + 1,300 = 5,950 บาท

6. Business Premium (10%): 5,950 * 0.10 = 595 บาท
   Subtotal with premium: 6,545 บาท

7. ส่วนลด 36 เดือน (12%): 6,545 * 0.12 = 785.40 บาท

8. Floor Price: 6,545 - 785.40 = 5,759.60 บาท/เดือน
```

---

## Configuration Management

### Database Configuration
ระบบสามารถจัดการ configuration หลายชุดผ่าน database:
```python
PricingConfig Table:
- config_name: ชื่อ config (เช่น 'default', 'promotion_2025')
- is_active: สถานะการใช้งาน
- speed_prices_residential/business: ราคาตามความเร็ว (JSON)
- distance/fixed_ip/equipment prices: ค่าต่างๆ
- contract_discounts: ส่วนลดตามสัญญา (JSON)
- created_by, created_at: ข้อมูลผู้สร้างและเวลา
```

### การใช้งาน Config
1. **Default Config**: ดึงจาก config.py
2. **Active Config**: ดึงจาก database (มี cache 5 นาที)
3. **Fallback**: ถ้าไม่มี active config ใช้ค่าจาก config.py

### Features
- ✅ สร้าง/ลบ/แก้ไข config
- ✅ Duplicate config เพื่อสร้างโปรโมชั่น
- ✅ Import/Export JSON
- ✅ Config History tracking
- ✅ Cache mechanism เพื่อประสิทธิภาพ

---

## การตรวจสอบราคา (Price Validation)
```python
def validate_price(proposed_price, floor_price):
    is_valid = proposed_price >= floor_price
    margin = ((proposed_price - floor_price) / floor_price) * 100
    
    if is_valid:
        return f"✅ ผ่าน - Margin: {margin:.2f}%"
    else:
        difference = floor_price - proposed_price
        return f"❌ ไม่ผ่าน - ต่ำกว่า {difference:.2f} บาท"
```

---

## หมายเหตุเพิ่มเติม

1. **ค่าติดตั้ง (Installation Fee)** - คิดแยกต่างหาก ไม่รวมใน monthly floor price
   - Residential: 500 บาท
   - Business: 1,500 บาท

2. **Interpolation Warning** - ระบบจะแจ้งเตือนเมื่อใช้ interpolation

3. **Admin Features** - Admin สามารถดู breakdown ละเอียดของการคำนวณ

4. **Logging** - ทุกการตรวจสอบจะถูกบันทึกใน database

---

## สรุป

Floor Price = (Base Price + Distance + Fixed IP + Equipment + Business Premium) - Contract Discount

โดยที่:
- Base Price อาจใช้ interpolation สำหรับ custom speed
- Distance มีการคิดเพิ่มถ้าเกินระยะมาตรฐาน
- Business มี premium 10% และส่วนลดน้อยกว่า residential
- ระบบรองรับ configuration หลายชุดผ่าน database