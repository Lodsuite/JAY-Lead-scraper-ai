"""
Test script to verify setup and configuration
Run this before using the main scraper to ensure everything is configured correctly
"""
import sys
import os

def test_imports():
    """Test if all required packages are installed"""
    print("Testing imports...")
    try:
        import selenium
        print("✓ Selenium installed")
    except ImportError:
        print("✗ Selenium not installed. Run: pip install selenium")
        return False
    
    try:
        import gspread
        print("✓ gspread installed")
    except ImportError:
        print("✗ gspread not installed. Run: pip install gspread")
        return False
    
    try:
        from twilio.rest import Client
        print("✓ Twilio installed")
    except ImportError:
        print("✗ Twilio not installed. Run: pip install twilio")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✓ python-dotenv installed")
    except ImportError:
        print("✗ python-dotenv not installed. Run: pip install python-dotenv")
        return False
    
    return True

def test_config():
    """Test configuration file"""
    print("\nTesting configuration...")
    try:
        import config
        print("✓ config.py loaded")
        
        # Check if locations are set
        if config.SEARCH_LOCATIONS:
            print(f"✓ Search locations configured: {len(config.SEARCH_LOCATIONS)} locations")
        else:
            print("⚠ No search locations configured")
        
        # Check if categories are set
        if config.BUSINESS_CATEGORIES:
            print(f"✓ Business categories configured: {len(config.BUSINESS_CATEGORIES)} categories")
        else:
            print("⚠ No business categories configured")
        
        return True
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return False

def test_google_sheets():
    """Test Google Sheets connection"""
    print("\nTesting Google Sheets connection...")
    try:
        import config
        from google_sheets_manager import GoogleSheetsManager
        
        if not os.path.exists(config.GOOGLE_SHEETS_CREDENTIALS_FILE):
            print(f"✗ Credentials file not found: {config.GOOGLE_SHEETS_CREDENTIALS_FILE}")
            print("  Please download your service account credentials JSON file")
            return False
        
        if not config.GOOGLE_SHEET_ID:
            print("✗ Google Sheet ID not configured")
            print("  Please set GOOGLE_SHEET_ID in config.py or .env")
            return False
        
        gs = GoogleSheetsManager(
            credentials_file=config.GOOGLE_SHEETS_CREDENTIALS_FILE,
            sheet_id=config.GOOGLE_SHEET_ID,
            sheet_name=config.GOOGLE_SHEET_NAME
        )
        print("✓ Google Sheets connection successful")
        return True
        
    except Exception as e:
        print(f"✗ Google Sheets connection failed: {e}")
        print("  Please check:")
        print("  1. credentials.json file exists and is valid")
        print("  2. GOOGLE_SHEET_ID is set correctly")
        print("  3. Service account has access to the sheet")
        return False

def test_twilio():
    """Test Twilio configuration"""
    print("\nTesting Twilio configuration...")
    try:
        import config
        
        if not config.TWILIO_ACCOUNT_SID:
            print("⚠ Twilio Account SID not configured (SMS will be disabled)")
            return True  # Not required for scraping
        
        if not config.TWILIO_AUTH_TOKEN:
            print("⚠ Twilio Auth Token not configured (SMS will be disabled)")
            return True
        
        if not config.TWILIO_PHONE_NUMBER:
            print("⚠ Twilio Phone Number not configured (SMS will be disabled)")
            return True
        
        from sms_sender import SMSSender
        sms = SMSSender(
            account_sid=config.TWILIO_ACCOUNT_SID,
            auth_token=config.TWILIO_AUTH_TOKEN,
            from_number=config.TWILIO_PHONE_NUMBER
        )
        
        if sms.client:
            print("✓ Twilio client initialized successfully")
            return True
        else:
            print("⚠ Twilio client not initialized (check credentials)")
            return True  # Not blocking
        
    except Exception as e:
        print(f"⚠ Twilio configuration issue: {e}")
        print("  SMS functionality will be disabled")
        return True  # Not blocking for scraping

def test_chrome_driver():
    """Test Chrome/ChromeDriver availability"""
    print("\nTesting Chrome/ChromeDriver...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://www.google.com")
        driver.quit()
        print("✓ Chrome/ChromeDriver working correctly")
        return True
        
    except Exception as e:
        print(f"✗ Chrome/ChromeDriver test failed: {e}")
        print("  Please ensure Chrome browser is installed")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Lead Scraper Setup Test")
    print("=" * 50)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Chrome Driver", test_chrome_driver()))
    results.append(("Google Sheets", test_google_sheets()))
    results.append(("Twilio", test_twilio()))
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n✓ All critical tests passed! You're ready to run the scraper.")
        print("\nNext steps:")
        print("1. Review and customize config.py")
        print("2. Run: python main.py")
    else:
        print("\n✗ Some tests failed. Please fix the issues above before running the scraper.")
        sys.exit(1)

if __name__ == "__main__":
    main()




