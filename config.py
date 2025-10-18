import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEV_MODE = True  # ตั้งค่าเป็น True เพื่อพัฒนาในเครื่อง (ไม่ส่ง email จริง)
    # Email
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@ntplc.co.th')
    SENDER_NAME = os.getenv('SENDER_NAME', 'Floor Price Validator')
    
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
            100: 199,
            150: 210,
            200: 221,
            300: 242,
            400: 264,
            500: 285,
            600: 307,
            700: 328,
            800: 350,
            1000: 393
        },
        'business': {
            100: 227,
            150: 240,
            200: 252,
            300: 277,
            400: 302,
            500: 327,
            600: 352,
            700: 378,
            800: 403,
            1000: 453
        }
    }

    # Fixed IP Pricing (บาท/เดือน)
    FIXED_IP_PRICE = {
        'residential': 200,  # บ้าน 200 บาท/เดือน
        'business': 200      # ธุรกิจ 200 บาท/เดือน (มี SLA ดีกว่า)
    }
    
    # Equipment Prices
    EQUIPMENT_PRICES = {
        'ONU Huawei HG8145X6 (AX3000 + 1POTS)': 74,
        'ONU ZTE 6201B (AX3000 + 1POTS)': 69,
        'ONU Huawei HG8140H5 (No WiFi + 1POTS)': 40,
        'ONU ZTE F612 (No WiFi + 1POTS)': 36,
        'WiFi 6 Router (AX.3000)': 26,
        'WiFi 6 Router (AX.1800)': 35,
        'WiFi 6 Router (AX.1200)': 19,
        'Mesh WiFi 6 Router (AX.3000) Pack 2': 106,
        'ATA (2 FXS)': 36,
        'ATA (4 FXS)': 68,
        'ATA (8 FXS)': 132
    }
    
    # Contract Discounts - ส่วนลดตามระยะสัญญา
    CONTRACT_DISCOUNTS = {
        'residential': {
            12: 0.0,   # 12 เดือน ลด 5%
            24: 0.0,   # 24 เดือน ลด 10%
            36: 0.0    # 36 เดือน ลด 15%
        },
        'business': {
            12: 0.0,   # ธุรกิจส่วนลดน้อยกว่า
            24: 0.0,
            36: 0.0
        }
    }
    
    # Business Premium (เพิ่มค่า SLA, Support 24/7)
    BUSINESS_PREMIUM_PERCENT = 0.0
    
    # Installation Fee - ค่าติดตั้งครั้งแรก (ไม่นับใน monthly floor price)
    INSTALLATION_FEE = {
        'residential': 2777,
        'business': 3753
    }

    # Installation configuration (ใช้สำหรับ amortization และค่าระยะทางเพิ่ม)
    INSTALLATION_CONFIG = {
        'residential': {
            'base_cost': 2777,
            'base_length_m': 315
        },
        'business': {
            'base_cost': 3753,
            'base_length_m': 520
        },
        'extra_cost_per_meter': 10.0
    }