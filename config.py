import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEV_MODE = False  # ตั้งค่าเป็น True เพื่อพัฒนาในเครื่อง (ไม่ส่ง email จริง)
    # Email
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    
    # Organization
    ALLOWED_EMAIL_DOMAIN = os.getenv('ALLOWED_EMAIL_DOMAIN')
    ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///floor_price.db')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY')
    OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', 5))
    
    # ==========================================
    # FLOOR PRICE CONFIGURATION
    # ==========================================
    
    # Customer Types
    CUSTOMER_TYPES = {
        'residential': 'Residential (บ้าน)',
        'business': 'Business (ธุรกิจ)'
    }
    
    # Speed Prices - แยกตามประเภทลูกค้า
    SPEED_PRICES = {
        'residential': {
            100: 500,
            200: 800,
            500: 1500,
            1000: 2500
        },
        'business': {
            100: 800,      # ธุรกิจแพงกว่า 60%
            200: 1200,
            500: 2200,
            1000: 3500
        }
    }
    
    # Distance Price Per KM - แยกตามประเภทลูกค้า
    DISTANCE_PRICE_PER_KM = {
        'residential': 50,   # บ้าน 50 บาท/กม.
        'business': 100      # ธุรกิจ 100 บาท/กม. (ติดตั้งซับซ้อนกว่า)
    }
    
    # Maximum Distance (กม.) - เกินนี้คิดพิเศษ
    MAX_STANDARD_DISTANCE = {
        'residential': 5,    # บ้านไม่เกิน 5 กม.
        'business': 10       # ธุรกิจไม่เกิน 10 กม.
    }
    
    # Extra Distance Multiplier (เกินระยะปกติคิดเพิ่ม)
    EXTRA_DISTANCE_MULTIPLIER = 1.5
    
    # Fixed IP Pricing
    FIXED_IP_PRICE = {
        'residential': 300,  # บ้าน 300 บาท/เดือน
        'business': 500      # ธุรกิจ 500 บาท/เดือน (มี SLA ดีกว่า)
    }
    
    # Equipment Prices
    EQUIPMENT_PRICES = {
        'standard_router': 0,
        'wifi6_router': 500,
        'mesh_system': 1500,
        'ont': 300,
        'managed_switch': 800,      # เพิ่มสำหรับธุรกิจ
        'enterprise_router': 2000   # เพิ่มสำหรับธุรกิจ
    }
    
    # Contract Discounts - ส่วนลดตามระยะสัญญา
    CONTRACT_DISCOUNTS = {
        'residential': {
            12: 0.05,   # 12 เดือน ลด 5%
            24: 0.10,   # 24 เดือน ลด 10%
            36: 0.15    # 36 เดือน ลด 15%
        },
        'business': {
            12: 0.03,   # ธุรกิจส่วนลดน้อยกว่า
            24: 0.07,
            36: 0.12
        }
    }
    
    # Business Premium (เพิ่มค่า SLA, Support 24/7)
    BUSINESS_PREMIUM_PERCENT = 0.10  # เพิ่ม 10% สำหรับ business support
    
    # Installation Fee - ค่าติดตั้งครั้งแรก (ไม่นับใน monthly floor price)
    INSTALLATION_FEE = {
        'residential': 500,
        'business': 1500
    }