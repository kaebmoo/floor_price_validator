from config import Config

def calculate_floor_price(customer_type, speed, distance, equipment_list, 
                         contract_months, has_fixed_ip=False):
    """
    คำนวณ floor price แบบละเอียด
    
    Parameters:
    - customer_type: 'residential' หรือ 'business'
    - speed: ความเร็วอินเทอร์เน็ต (Mbps)
    - distance: ระยะทางการติดตั้ง (กม.)
    - equipment_list: รายการอุปกรณ์ (list)
    - contract_months: ระยะเวลาสัญญา (เดือน)
    - has_fixed_ip: มี Fixed IP หรือไม่ (boolean)
    
    Returns:
    - dict: {
        'floor_price': ราคาพื้นฐานต่ำสุด (monthly),
        'breakdown': รายละเอียดการคำนวณ
      }
    """
    
    breakdown = {}
    
    # 1. Base price from speed
    speed_prices = Config.SPEED_PRICES.get(customer_type, Config.SPEED_PRICES['residential'])
    base_price = speed_prices.get(speed, 0)
    
    if base_price == 0:
        # Interpolate if speed not in list
        speeds = sorted(speed_prices.keys())
        for i in range(len(speeds) - 1):
            if speeds[i] < speed < speeds[i + 1]:
                ratio = (speed - speeds[i]) / (speeds[i + 1] - speeds[i])
                base_price = speed_prices[speeds[i]] + ratio * (
                    speed_prices[speeds[i + 1]] - speed_prices[speeds[i]]
                )
                break
        if base_price == 0:
            base_price = speed_prices[max(speeds)]
    
    breakdown['base_price'] = round(base_price, 2)
    
    # 2. Distance cost (แยกตามประเภทลูกค้า)
    distance_rate = Config.DISTANCE_PRICE_PER_KM.get(
        customer_type, 
        Config.DISTANCE_PRICE_PER_KM['residential']
    )
    
    max_standard_distance = Config.MAX_STANDARD_DISTANCE.get(
        customer_type, 
        Config.MAX_STANDARD_DISTANCE['residential']
    )
    
    if distance <= max_standard_distance:
        # ระยะปกติ
        distance_cost = distance * distance_rate
    else:
        # เกินระยะปกติ - คิดแพงขึ้น
        standard_cost = max_standard_distance * distance_rate
        extra_distance = distance - max_standard_distance
        extra_cost = extra_distance * distance_rate * Config.EXTRA_DISTANCE_MULTIPLIER
        distance_cost = standard_cost + extra_cost
    
    breakdown['distance_cost'] = round(distance_cost, 2)
    breakdown['distance_rate'] = distance_rate
    breakdown['distance_km'] = distance
    
    # 3. Fixed IP cost
    fixed_ip_cost = 0
    if has_fixed_ip:
        fixed_ip_cost = Config.FIXED_IP_PRICE.get(
            customer_type, 
            Config.FIXED_IP_PRICE['residential']
        )
    
    breakdown['fixed_ip_cost'] = fixed_ip_cost
    
    # 4. Equipment cost
    equipment_cost = sum([
        Config.EQUIPMENT_PRICES.get(eq, 0) 
        for eq in equipment_list
    ])
    breakdown['equipment_cost'] = round(equipment_cost, 2)
    breakdown['equipment_list'] = equipment_list
    
    # 5. Subtotal before discount and premium
    subtotal = base_price + distance_cost + fixed_ip_cost + equipment_cost
    breakdown['subtotal_before_adjustments'] = round(subtotal, 2)
    
    # 6. Business Premium (SLA + Support)
    business_premium = 0
    if customer_type == 'business':
        business_premium = subtotal * Config.BUSINESS_PREMIUM_PERCENT
        breakdown['business_premium'] = round(business_premium, 2)
    
    subtotal_with_premium = subtotal + business_premium
    breakdown['subtotal_with_premium'] = round(subtotal_with_premium, 2)
    
    # 7. Contract discount
    discounts = Config.CONTRACT_DISCOUNTS.get(
        customer_type, 
        Config.CONTRACT_DISCOUNTS['residential']
    )
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
    return Config.INSTALLATION_FEE.get(customer_type, 0)