from config import Config
import config_manager as cm

def _load_pricing_config():
    """ดึง configuration สำหรับการคำนวณ (รองรับ database override)"""
    db_config = cm.get_active_config()
    if db_config:
        speed_prices = {
            'residential': {int(k): v for k, v in db_config.speed_prices_residential.items()},
            'business': {int(k): v for k, v in db_config.speed_prices_business.items()}
        }

        contract_discounts = {
            'residential': {int(k): v for k, v in db_config.contract_discounts_residential.items()},
            'business': {int(k): v for k, v in db_config.contract_discounts_business.items()}
        }

        installation_config = {
            'residential': {
                'base_cost': db_config.distance_price_residential,
                'base_length_m': db_config.max_distance_residential
            },
            'business': {
                'base_cost': db_config.distance_price_business,
                'base_length_m': db_config.max_distance_business
            },
            'extra_cost_per_meter': db_config.extra_distance_multiplier
        }

        fixed_ip_price = {
            'residential': db_config.fixed_ip_residential,
            'business': db_config.fixed_ip_business
        }

        equipment_prices = db_config.equipment_prices
        business_premium_percent = db_config.business_premium_percent
    else:
        speed_prices = Config.SPEED_PRICES
        contract_discounts = Config.CONTRACT_DISCOUNTS
        installation_config = Config.INSTALLATION_CONFIG
        fixed_ip_price = Config.FIXED_IP_PRICE
        equipment_prices = Config.EQUIPMENT_PRICES
        business_premium_percent = Config.BUSINESS_PREMIUM_PERCENT

    return {
        'speed_prices': speed_prices,
        'contract_discounts': contract_discounts,
        'installation_config': installation_config,
        'fixed_ip_price': fixed_ip_price,
        'equipment_prices': equipment_prices,
        'business_premium_percent': business_premium_percent,
        'source': 'database' if db_config else 'config.py'
    }


def _compute_installation_details(pricing_config, customer_type, distance_km):
    install_cfg = pricing_config['installation_config']
    customer_cfg = install_cfg['residential' if customer_type == 'residential' else 'business']

    distance_meters = max(distance_km, 0) * 1000
    base_cost = customer_cfg['base_cost']
    base_length = customer_cfg['base_length_m']
    extra_cost_per_meter = install_cfg['extra_cost_per_meter']

    extra_distance_m = max(distance_meters - base_length, 0)
    extra_cost = extra_distance_m * extra_cost_per_meter

    total_install_cost = base_cost + extra_cost

    return {
        'base_cost': base_cost,
        'base_length_m': base_length,
        'distance_m': distance_meters,
        'extra_distance_m': extra_distance_m,
        'extra_cost': extra_cost,
        'total_cost': total_install_cost
    }


def calculate_floor_price(customer_type, speed, distance, equipment_list, 
                         contract_months, has_fixed_ip=False):
    """
    คำนวณ floor price โดยดึง config จาก database
    รองรับ interpolation สำหรับความเร็วที่ไม่ใช่แพ็คเกจมาตรฐาน
    ** ไม่รวมค่าติดตั้ง - สำหรับลูกค้าเดิม **
    """
    
    pricing_config = _load_pricing_config()
    speed_prices = pricing_config['speed_prices']
    contract_discounts = pricing_config['contract_discounts']
    fixed_ip_price = pricing_config['fixed_ip_price']
    equipment_prices = pricing_config['equipment_prices']
    business_premium_percent = pricing_config['business_premium_percent']
    
    breakdown = {}
    
    # 1. Base price from speed (with improved interpolation)
    speeds = speed_prices.get(customer_type, speed_prices['residential'])
    base_price = speeds.get(speed)
    
    if base_price is not None:
        breakdown['interpolated'] = False
        breakdown['base_price'] = round(base_price, 2)
    else:
        breakdown['interpolated'] = True
        
        speeds_sorted = sorted(speeds.keys())
        
        if not speeds_sorted:
            raise ValueError(f"ไม่มีข้อมูลราคาสำหรับประเภท {customer_type}")
        
        lower_speeds = [s for s in speeds_sorted if s < speed]
        upper_speeds = [s for s in speeds_sorted if s > speed]
        
        if lower_speeds and upper_speeds:
            speed_lower = max(lower_speeds)
            speed_upper = min(upper_speeds)
            price_lower = speeds[speed_lower]
            price_upper = speeds[speed_upper]
            
            ratio = (speed - speed_lower) / (speed_upper - speed_lower)
            base_price = price_lower + ratio * (price_upper - price_lower)
            
            breakdown['speed_lower'] = speed_lower
            breakdown['speed_upper'] = speed_upper
            breakdown['price_lower'] = price_lower
            breakdown['price_upper'] = price_upper
            breakdown['interpolation_ratio'] = round(ratio, 3)
            
        elif lower_speeds:
            speed_lower = max(lower_speeds)
            
            if len(speeds_sorted) >= 2:
                speed_second = speeds_sorted[-2]
                price_lower = speeds[speed_lower]
                price_second = speeds[speed_second]
                slope = (price_lower - price_second) / (speed_lower - speed_second)
                
                extra_speed = speed - speed_lower
                extra_price = slope * extra_speed
                base_price = price_lower + min(extra_price, price_lower * 0.5)
            else:
                price_lower = speeds[speed_lower]
                ratio = speed / speed_lower
                base_price = price_lower * min(ratio, 1.5)
            
            breakdown['speed_lower'] = speed_lower
            breakdown['extrapolation'] = 'upward'
            
        else:
            speed_upper = min(upper_speeds)
            base_price = speeds[speed_upper]
            
            breakdown['speed_upper'] = speed_upper
            breakdown['extrapolation'] = 'downward'
            breakdown['note'] = f"ใช้ราคาแพ็คเกจต่ำสุด ({speed_upper} Mbps)"
        
        breakdown['base_price'] = round(base_price, 2)
    
    installation_details = _compute_installation_details(pricing_config, customer_type, distance)
    breakdown['distance_km'] = distance
    breakdown['distance_meters'] = round(installation_details['distance_m'], 2)
    breakdown['installation_base_cost'] = round(installation_details['base_cost'], 2)
    breakdown['installation_base_length_m'] = installation_details['base_length_m']
    breakdown['installation_extra_cost'] = round(installation_details['extra_cost'], 2)
    breakdown['installation_total_cost_if_new'] = round(installation_details['total_cost'], 2)
    
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
    subtotal = base_price + fixed_ip_cost + equipment_cost
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
    
    # 8. Final floor price (ไม่รวมค่าติดตั้ง)
    floor_price = subtotal_with_premium - discount_amount
    breakdown['floor_price'] = round(floor_price, 2)
    breakdown['customer_type'] = customer_type
    breakdown['includes_installation'] = False
    
    return {
        'floor_price': round(floor_price, 2),
        'breakdown': breakdown,
        'installation_details': installation_details
    }


def calculate_floor_price_with_installation(customer_type, speed, distance, equipment_list, 
                                            contract_months, has_fixed_ip=False):
    """
    คำนวณ floor price โดยรวมค่าติดตั้ง (amortized)
    ** สำหรับลูกค้าใหม่ **
    """
    # เรียกฟังก์ชันหลัก
    result = calculate_floor_price(customer_type, speed, distance, equipment_list, 
                                   contract_months, has_fixed_ip)
    
    floor_without_install = result['floor_price']
    breakdown = result['breakdown']
    installation_details = result['installation_details']

    # รวมค่าติดตั้งพื้นฐานและค่าระยะเพิ่มเติม (ถ้ามี)
    install_total = installation_details['total_cost']
    installation_monthly = install_total / contract_months if contract_months else 0

    floor_with_install = floor_without_install + installation_monthly

    breakdown['installation_fee_total'] = round(install_total, 2)
    breakdown['installation_monthly'] = round(installation_monthly, 2)
    breakdown['floor_price_with_install'] = round(floor_with_install, 2)
    breakdown['includes_installation'] = True

    return {
        'floor_price': round(floor_with_install, 2),
        'breakdown': breakdown,
        'installation_details': installation_details
    }


def calculate_weighted_floor(customer_type, speed, distance, equipment_list, 
                             contract_months, has_fixed_ip=False,
                             existing_customer_ratio=0.7):
    """
    คำนวณ Floor Price แบบถัวเฉลี่ย (Weighted Average)
    โดยพิจารณาสัดส่วนลูกค้าเดิมและลูกค้าใหม่
    
    Args:
        existing_customer_ratio: สัดส่วนลูกค้าเดิม (default 70% = 0.7)
    
    Returns:
        dict: {
            'floor_existing': floor price สำหรับลูกค้าเดิม (ไม่มีค่าติดตั้ง)
            'floor_new': floor price สำหรับลูกค้าใหม่ (มีค่าติดตั้ง)
            'floor_weighted': floor price ถัวเฉลี่ย
            'breakdown_existing': รายละเอียดลูกค้าเดิม
            'breakdown_new': รายละเอียดลูกค้าใหม่
        }
    """
    # คำนวณ floor สำหรับลูกค้าเดิม (ไม่มีค่าติดตั้ง)
    result_existing = calculate_floor_price(
        customer_type, speed, distance, equipment_list, 
        contract_months, has_fixed_ip
    )
    
    # คำนวณ floor สำหรับลูกค้าใหม่ (มีค่าติดตั้ง)
    result_new = calculate_floor_price_with_installation(
        customer_type, speed, distance, equipment_list, 
        contract_months, has_fixed_ip
    )
    
    floor_existing = result_existing['floor_price']
    floor_new = result_new['floor_price']
    
    # คำนวณถัวเฉลี่ย
    new_customer_ratio = 1 - existing_customer_ratio
    floor_weighted = (floor_existing * existing_customer_ratio) + (floor_new * new_customer_ratio)
    
    return {
        'floor_existing': round(floor_existing, 2),
        'floor_new': round(floor_new, 2),
        'floor_weighted': round(floor_weighted, 2),
        'existing_ratio': existing_customer_ratio,
        'new_ratio': new_customer_ratio,
        'weighted_existing': round(floor_existing * existing_customer_ratio, 2),
        'weighted_new': round(floor_new * new_customer_ratio, 2),
        'breakdown_existing': result_existing['breakdown'],
        'breakdown_new': result_new['breakdown'],
        'installation_existing': result_existing['installation_details'],
        'installation_new': result_new['installation_details']
    }


def calculate_net_revenue_after_fees(proposed_price, discount_percent=0):
    """
    คำนวณรายได้สุทธิหลังหักส่วนลดและค่าธรรมเนียม กสทช. 4%
    
    Args:
        proposed_price: ราคาที่เสนอขาย
        discount_percent: ส่วนลด (%) เช่น 10 = ลด 10%
    
    Returns:
        dict: {
            'gross_price': ราคาขายเต็ม
            'discount_amount': จำนวนเงินส่วนลด
            'price_after_discount': ราคาหลังหักส่วนลด
            'regulator_fee': ค่าธรรมเนียม กสทช. 4%
            'net_revenue': รายได้สุทธิ
        }
    """
    # ส่วนลด
    discount_amount = proposed_price * (discount_percent / 100)
    price_after_discount = proposed_price - discount_amount
    
    # ค่าธรรมเนียม กสทช. 4% (คิดจากรายได้หลังหักส่วนลด)
    regulator_fee = price_after_discount * 0.04
    
    # รายได้สุทธิ
    net_revenue = price_after_discount - regulator_fee
    
    return {
        'gross_price': round(proposed_price, 2),
        'discount_percent': discount_percent,
        'discount_amount': round(discount_amount, 2),
        'price_after_discount': round(price_after_discount, 2),
        'regulator_fee': round(regulator_fee, 2),
        'net_revenue': round(net_revenue, 2)
    }


def calculate_comprehensive_margin(proposed_price, floor_price, discount_percent=0):
    """
    คำนวณ Margin แบบครบถ้วน
    - คำนวณรายได้สุทธิหลังหัก discount และ regulator fee
    - เทียบกับ floor price
    
    Returns:
        dict: {
            'revenue_details': รายละเอียดรายได้
            'margin_baht': กำไรส่วนต่าง (บาท)
            'margin_percent': กำไรส่วนต่าง (%)
            'is_valid': ผ่านหรือไม่
        }
    """
    # คำนวณรายได้สุทธิ
    revenue = calculate_net_revenue_after_fees(proposed_price, discount_percent)
    net_revenue = revenue['net_revenue']
    
    # คำนวณ margin
    margin_baht = net_revenue - floor_price
    margin_percent = (margin_baht / net_revenue * 100) if net_revenue > 0 else 0
    
    is_valid = net_revenue >= floor_price
    
    return {
        'revenue_details': revenue,
        'floor_price': round(floor_price, 2),
        'margin_baht': round(margin_baht, 2),
        'margin_percent': round(margin_percent, 2),
        'is_valid': is_valid
    }


def calculate_margin(proposed_price, floor_price):
    """คำนวณ margin เปอร์เซ็นต์ (แบบเดิม - เก็บไว้เพื่อ backward compatibility)"""
    if floor_price == 0:
        return 0
    margin = ((proposed_price - floor_price) / floor_price) * 100
    return round(margin, 2)


def get_installation_fee(customer_type):
    """ดึงค่าติดตั้งตามประเภทลูกค้า"""
    db_config = cm.get_active_config()

    if db_config:
        return db_config.installation_fee_residential if customer_type == 'residential' else db_config.installation_fee_business
    return Config.INSTALLATION_FEE.get(customer_type, 0)


def generate_bandwidth_comparison_table(customer_type, equipment_list, contract_months,
                                        has_fixed_ip, discount_percent,
                                        existing_customer_ratio, distance=1.0,
                                        proposed_prices=None):
    """สร้างตารางสรุปราคาตามความเร็วตามรูปแบบในแผน"""
    pricing_config = _load_pricing_config()
    speeds = sorted(pricing_config['speed_prices'][customer_type].keys())

    table_data = []

    for speed in speeds:
        weighted = calculate_weighted_floor(
            customer_type, speed, distance, equipment_list,
            contract_months, has_fixed_ip, existing_customer_ratio
        )

        # คำนวณรายได้สุทธิถ้ามีราคาที่เสนอ
        proposed_price = None
        revenue = None
        if proposed_prices and speed in proposed_prices:
            proposed_price = proposed_prices[speed]
            revenue = calculate_comprehensive_margin(
                proposed_price, weighted['floor_weighted'], discount_percent
            )

        margin_baht = revenue['margin_baht'] if revenue else 0.0
        margin_percent = revenue['margin_percent'] if revenue else 0.0
        net_revenue = revenue['revenue_details']['net_revenue'] if revenue else 0.0
        margin_valid = revenue['is_valid'] if revenue else False

        table_data.append({
            'speed': speed,
            'floor_existing': weighted['floor_existing'],
            'floor_new': weighted['floor_new'],
            'floor_weighted': weighted['floor_weighted'],
            'proposed_price': proposed_price,
            'net_revenue': net_revenue,
            'margin_baht': margin_baht,
            'margin_percent': margin_percent,
            'margin_valid': margin_valid
        })

    return table_data