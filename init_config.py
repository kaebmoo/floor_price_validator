import config_manager as cm

def main():
    """Initialize pricing configuration"""
    print("🚀 Initializing Pricing Configuration...")
    
    # Create default config
    config = cm.create_default_config(created_by="system")
    
    if config:
        print(f"✅ Created default configuration: {config.config_name}")
        print(f"   Status: {'Active' if config.is_active else 'Inactive'}")
        print("\n📋 Configuration Summary:")
        print(f"   - Residential speed prices: {config.speed_prices_residential}")
        print(f"   - Business speed prices: {config.speed_prices_business}")
        print(f"   - Distance pricing: {config.distance_price_residential} (res) / {config.distance_price_business} (bus) ฿/จุดติดตั้ง")
        print("\n✅ Initialization complete!")
    else:
        print("⚠️  Default configuration already exists")

if __name__ == "__main__":
    main()