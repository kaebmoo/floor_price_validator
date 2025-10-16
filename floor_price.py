from config import Config
import config_manager as cm

def calculate_floor_price(customer_type, speed, distance, equipment_list, 
                         contract_months, has_fixed_ip=False):
    """
    คำนวณ floor price โดยดึง config จาก database
    รองรับ interpolation สำหรับความเร็วที่ไม่ใช่แพ็คเกจมาตรฐาน
    """
    
    # Load config from database (with cache)
    db_config = cm.get_active_config()
    
    if db_config:
        # Use database config
        # ⚠️ IMPORTANT: Convert JSON keys from string to int
        speed_prices_residential = {int(k): v for k, v in db_config.speed_prices_residential.items()}
        speed_prices_business = {int(k): v for k, v in db_config.speed_prices_business.items()}
        
        speed_prices = {
            'residential': speed_prices_residential,
            'business': speed_prices_business
        }
        
        # Convert contract discount keys to int
        contract_discounts_residential = {int(k): v for k, v in db_config.contract_discounts_residential.items()}
        contract_discounts_business = {int(k): v for k, v in db_config.contract_discounts_business.items()}
        
        distance_price_per_km = {
            'residential': db_config.distance_price_residential,
            'business': db_config.distance_price_business
        }
        max_standard_distance = {
            'residential': db_config.max_distance_residential,
            'business': db_config.max_distance_business
        }
        extra_distance_multiplier = db_config.extra_distance_multiplier
        fixed_ip_price = {
            'residential': db_config.fixed_ip_residential,
            'business': db_config.fixed_ip_business
        }
        equipment_prices = db_config.equipment_prices
        contract_discounts = {
            'residential': contract_discounts_residential,
            'business': contract_discounts_business
        }
        business_premium_percent = db_config.business_premium_percent
    else:
        # Fallback to config.py
        speed_prices = Config.SPEED_PRICES
        distance_price_per_km = Config.DISTANCE_PRICE_PER_KM
        max_standard_distance = Config.MAX_STANDARD_DISTANCE
        extra_distance_multiplier = Config.EXTRA_DISTANCE_MULTIPLIER
        fixed_ip_price = Config.FIXED_IP_PRICE
        equipment_prices = Config.EQUIPMENT_PRICES
        contract_discounts = Config.CONTRACT_DISCOUNTS
        business_premium_percent = Config.BUSINESS_PREMIUM_PERCENT
    
    breakdown = {}
    
    # 1. Base price from speed (with improved interpolation)
    speeds = speed_prices.get(customer_type, speed_prices['residential'])
    base_price = speeds.get(speed)  # ลองดึงตรงๆ ก่อน
    
    if base_price is not None:
        # เป็นแพ็คเกจมาตรฐาน
        breakdown['interpolated'] = False
        breakdown['base_price'] = round(base_price, 2)
    else:
        # ต้องใช้ interpolation
        breakdown['interpolated'] = True
        
        speeds_sorted = sorted(speeds.keys())  # ตอนนี้ keys เป็น int แล้ว
        
        if not speeds_sorted:
            raise ValueError(f"ไม่มีข้อมูลราคาสำหรับประเภท {customer_type}")
        
        # กรณีที่ 1: ความเร็วอยู่ระหว่างแพ็คเกจ (Linear Interpolation)
        lower_speeds = [s for s in speeds_sorted if s < speed]
        upper_speeds = [s for s in speeds_sorted if s > speed]
        
        if lower_speeds and upper_speeds:
            # Interpolate between two packages
            speed_lower = max(lower_speeds)
            speed_upper = min(upper_speeds)
            price_lower = speeds[speed_lower]
            price_upper = speeds[speed_upper]
            
            # Linear interpolation
            ratio = (speed - speed_lower) / (speed_upper - speed_lower)
            base_price = price_lower + ratio * (price_upper - price_lower)
            
            breakdown['speed_lower'] = speed_lower
            breakdown['speed_upper'] = speed_upper
            breakdown['price_lower'] = price_lower
            breakdown['price_upper'] = price_upper
            breakdown['interpolation_ratio'] = round(ratio, 3)
            
        elif lower_speeds:
            # กรณีที่ 2: ความเร็วสูงกว่าแพ็คเกจสูงสุด - Extrapolate
            speed_lower = max(lower_speeds)
            
            if len(speeds_sorted) >= 2:
                # ใช้ slope จาก 2 แพ็คเกจสุดท้าย
                speed_second = speeds_sorted[-2]
                price_lower = speeds[speed_lower]
                price_second = speeds[speed_second]
                slope = (price_lower - price_second) / (speed_lower - speed_second)
                
                # Extrapolate (แต่ไม่ให้เกินไปเกินมา - cap at 1.5x)
                extra_speed = speed - speed_lower
                extra_price = slope * extra_speed
                base_price = price_lower + min(extra_price, price_lower * 0.5)  # Cap at 50% increase
            else:
                # มีแพ็คเกจเดียว - ใช้ราคานั้นคูณ ratio
                price_lower = speeds[speed_lower]
                ratio = speed / speed_lower
                base_price = price_lower * min(ratio, 1.5)  # Cap at 1.5x
            
            breakdown['speed_lower'] = speed_lower
            breakdown['extrapolation'] = 'upward'
            
        else:
            # กรณีที่ 3: ความเร็วต่ำกว่าแพ็คเกจต่ำสุด - ใช้ราคาต่ำสุด
            speed_upper = min(upper_speeds)
            base_price = speeds[speed_upper]
            
            breakdown['speed_upper'] = speed_upper
            breakdown['extrapolation'] = 'downward'
            breakdown['note'] = f"ใช้ราคาแพ็คเกจต่ำสุด ({speed_upper} Mbps)"
        
        breakdown['base_price'] = round(base_price, 2)
    
    
    # 2. Distance cost
    distance_rate = distance_price_per_km.get(customer_type, distance_price_per_km['residential'])
    max_dist = max_standard_distance.get(customer_type, max_standard_distance['residential'])
    
    if distance <= max_dist:
        distance_cost = distance * distance_rate
    else:
        standard_cost = max_dist * distance_rate
        extra_distance = distance - max_dist
        extra_cost = extra_distance * distance_rate * extra_distance_multiplier
        distance_cost = standard_cost + extra_cost
    
    breakdown['distance_cost'] = round(distance_cost, 2)
    breakdown['distance_rate'] = distance_rate
    breakdown['distance_km'] = distance
    
    # 3. Fixed IP cost
    fixed_ip_cost = 0
    if has_fixed_ip:
        fixed_ip_cost = fixed_ip_price.get(customer_type, fixed_ip_price['residential'])
    
    breakdown['fixed_ip_cost'] = fixed_ip_cost
    
    # 4. Equipment cost
    equipment_cost = sum([equipment_prices.get(eq, 0) for eq in equipment_list])
    breakdown['equipment_cost'] = round(equipment_cost, 2)
    breakdown['equipment_list'] = equipment_list
    
    # 5. Subtotal
    subtotal = base_price + distance_cost + fixed_ip_cost + equipment_cost
    breakdown['subtotal_before_adjustments'] = round(subtotal, 2)
    
    # 6. Business Premium
    business_premium = 0
    if customer_type == 'business':
        business_premium = subtotal * business_premium_percent
        breakdown['business_premium'] = round(business_premium, 2)
    
    subtotal_with_premium = subtotal + business_premium
    breakdown['subtotal_with_premium'] = round(subtotal_with_premium, 2)
    
    # 7. Contract discount
    discounts = contract_discounts.get(customer_type, contract_discounts['residential'])
    discount_rate = discounts.get(contract_months, 0)
    discount_amount = subtotal_with_premium * discount_rate
    
    breakdown['contract_months'] = contract_months
    breakdown['discount_rate'] = discount_rate
    breakdown['discount_amount'] = round(discount_amount, 2)
    
    # 8. Final floor price
    floor_price = subtotal_with_premium - discount_amount
    breakdown['floor_price'] = round(floor_price, 2)
    breakdown['customer_type'] = customer_type
    
    return {
        'floor_price': round(floor_price, 2),
        'breakdown': breakdown
    }

def calculate_margin(proposed_price, floor_price):
    """คำนวณ margin เปอร์เซ็นต์"""
    if floor_price == 0:
        return 0
    margin = ((proposed_price - floor_price) / floor_price) * 100
    return round(margin, 2)

def get_installation_fee(customer_type):
    """ดึงค่าติดตั้งตามประเภทลูกค้า"""
    db_config = cm.get_active_config()
    
    if db_config:
        return db_config.installation_fee_residential if customer_type == 'residential' else db_config.installation_fee_business
    else:
        return Config.INSTALLATION_FEE.get(customer_type, 0)