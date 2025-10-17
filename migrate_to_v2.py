#!/usr/bin/env python3
"""
Migration Script - Floor Price Validator v1.0 → v2.0

This script helps migrate from the old system to the new weighted average system.
"""

import os
import sys
from datetime import datetime

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_step(step, text):
    print(f"\n[Step {step}] {text}")

def print_success(text):
    print(f"  ✅ {text}")

def print_warning(text):
    print(f"  ⚠️  {text}")

def print_error(text):
    print(f"  ❌ {text}")

def check_files():
    """ตรวจสอบไฟล์ที่จำเป็น"""
    print_step(1, "Checking required files...")
    
    required_files = [
        'floor_price.py',
        'database.py',
        'document_export.py',
        'config.py',
        'auth.py',
        'config_manager.py',
        'app.py'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print_success(f"Found: {file}")
        else:
            print_error(f"Missing: {file}")
            missing_files.append(file)
    
    if missing_files:
        print_error(f"Missing {len(missing_files)} required files!")
        return False
    
    return True

def backup_old_files():
    """สำรองไฟล์เดิม"""
    print_step(2, "Backing up old files...")
    
    backup_dir = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
        print_success(f"Created backup directory: {backup_dir}")
        
        files_to_backup = ['app.py', 'floor_price.py', 'database.py']
        
        for file in files_to_backup:
            if os.path.exists(file):
                import shutil
                shutil.copy2(file, os.path.join(backup_dir, file))
                print_success(f"Backed up: {file}")
        
        return True
    except Exception as e:
        print_error(f"Backup failed: {str(e)}")
        return False

def check_dependencies():
    """ตรวจสอบ Python packages"""
    print_step(3, "Checking dependencies...")
    
    required_packages = {
        'streamlit': 'streamlit',
        'pandas': 'pandas',
        'plotly': 'plotly',
        'qrcode': 'qrcode[pil]',
        'reportlab': 'reportlab',
        'sqlalchemy': 'sqlalchemy'
    }
    
    missing_packages = []
    
    for package, install_name in required_packages.items():
        try:
            __import__(package)
            print_success(f"Found: {package}")
        except ImportError:
            print_error(f"Missing: {package}")
            missing_packages.append(install_name)
    
    if missing_packages:
        print_warning("Some packages are missing. Install with:")
        print(f"\n  pip install {' '.join(missing_packages)}\n")
        return False
    
    return True

def create_database_tables():
    """สร้างตาราง database ใหม่"""
    print_step(4, "Creating new database tables...")
    
    try:
        import database as db
        print_success("Database tables created successfully")
        return True
    except Exception as e:
        print_error(f"Failed to create tables: {str(e)}")
        return False

def test_calculations():
    """ทดสอบการคำนวณ"""
    print_step(5, "Testing calculations...")
    
    try:
        import floor_price as fp

        equipments = [
            'ONU ZTE F612 (No WiFi + 1POTS)',
            'ONU Huawei HG8145X6 (AX3000 + 1POTS)',
            'WiFi 6 Router (AX.3000)',
            'WiFi 6 Router (AX.1200)'
        ]

        result = fp.calculate_floor_price(
            customer_type='residential',
            speed=500,
            distance=0.315,
            equipment_list=equipments,
            contract_months=12,
            has_fixed_ip=True
        )
        print_success(f"Base floor (existing customers): {result['floor_price']} baht/month")

        weighted = fp.calculate_weighted_floor(
            customer_type='residential',
            speed=500,
            distance=0.315,
            equipment_list=equipments,
            contract_months=12,
            has_fixed_ip=True,
            existing_customer_ratio=0.7
        )
        print_success(f"Weighted floor: {weighted['floor_weighted']} baht/month")

        revenue = fp.calculate_net_revenue_after_fees(800, 0)
        print_success(f"Net revenue after fees: {revenue['net_revenue']} baht/month")
        
        return True
        
    except Exception as e:
        print_error(f"Calculation test failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def show_migration_summary():
    """แสดงสรุปการ migrate"""
    print_header("Migration Summary")
    
    print("""
📋 What's New in v2.0:

1. ✅ Weighted Average Calculation
   - Separate floor for existing vs new customers
   - Amortized installation fee
   - Customizable customer mix ratio

2. ✅ Revenue Calculation
   - Discount support
   - 4% regulator fee deduction
   - Net revenue calculation

3. ✅ Document System
   - Reference ID for every check
   - HTML/TXT export
   - Verification system

4. ✅ Comparison Table
   - Compare floor prices across speeds
   - Interactive charts
   - CSV export

📁 Components Touched:
- floor_price.py (weighted calculations & revenue)
- database.py (updated schema + history)
- document_export.py (HTML/TXT export)
- app.py (Streamlit UI v2.0)

🗄️ Database Changes:
- price_checks table expanded for weighted metrics and exports
- Legacy table price_checks_legacy preserved for reference

🚀 Next Steps:
1. Review the new code
2. Update app.py or create app_updated.py
3. Test with sample data
4. Update documentation & train users on new features
5. Monitor logs and user feedback

⚠️ Important Notes:
- Old system continues to work
- No data loss
- Can run both systems in parallel
- Gradual migration recommended
    """)

def run_migration():
    """รัน migration script หลัก"""
    print_header("Floor Price Validator - Migration to v2.0")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Check files
    if not check_files():
        print_error("\n❌ Migration aborted: Missing required files")
        return False
    
    # Step 2: Backup
    if not backup_old_files():
        print_error("\n❌ Migration aborted: Backup failed")
        return False
    
    # Step 3: Dependencies
    if not check_dependencies():
        print_warning("\n⚠️ Some dependencies missing. Install them first.")
        response = input("\nContinue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print_error("Migration aborted by user")
            return False
    
    # Step 4: Database
    if not create_database_tables():
        print_error("\n❌ Migration aborted: Database setup failed")
        return False
    
    # Step 5: Test
    if not test_calculations():
        print_error("\n❌ Migration aborted: Calculation tests failed")
        return False
    
    # Success!
    print_header("🎉 Migration Completed Successfully!")
    show_migration_summary()
    
    return True

if __name__ == "__main__":
    try:
        success = run_migration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print_error("\n\n❌ Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\n❌ Migration failed with error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)