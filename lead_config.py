"""
Configuration file for Lead Scraper
Set your API keys and settings here or use environment variables
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ----------------- Google Sheets -----------------
GOOGLE_SHEETS_CREDENTIALS_FILE = "credentials.json"  # service account json
GOOGLE_SHEET_ID = "16wrh8G47dISqeS9Emqocwp6p10--VZ3DBtnI8H5UUuE"
GOOGLE_SHEET_NAME = "Leads3"  # make sure the tab name matches this

# ----------------- Twilio SMS --------------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")  # Your Twilio number

# ----------------- Email SMTP (optional) ---------
# Fill these in your .env if you want email sending later
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "")      # e.g. "smtp.gmail.com"
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")                # e.g. "you@yourdomain.com"

# ----------------- Scraping Settings -------------
# Keep this smaller while testing so it’s fast
SEARCH_LOCATIONS = [
    "Queens, NY",
    "Brooklyn, NY",
    "Manhattan, NY",
    "Long Island, NY",
    "Staten Island, NY",
  
]

BUSINESS_CATEGORIES = [
    "bars",
    "restaurants",
    "hotels",
    "construction companies",
    "property management companies",
    "nightclubs",
    "event venues",
    
]

# Limit results per category/location.
# This is how many leads to collect per category in each location.
# With 5 locations and 7 categories at 10 each = ~350 potential leads
MAX_RESULTS_PER_CATEGORY = 10  # 10 leads per category
DELAY_BETWEEN_REQUESTS = 12     # seconds between searches (increased for stability)

# Two-pass strategy:
# 1) Fast list scrape
# 2) Click-into-detail for leads missing phone numbers OR websites
ENRICH_MISSING_PHONES = True
ENRICH_MAX_CLICKS_PER_SEARCH = 100  # High limit to ensure we get ALL missing phones/websites

# ----------------- SMS Template ------------------
SMS_MESSAGE_TEMPLATE = """Hello {business_name},

I hope this message finds you well. I'm reaching out because I noticed your business could benefit from professional security services.

We specialize in providing comprehensive security solutions for businesses like yours, including:
- 24/7 security personnel
- Access control systems
- Surveillance monitoring
- Emergency response

Would you be interested in a free consultation to discuss how we can help protect your business?

Best regards,
[Your Name]
[Your Company]
[Your Phone Number]
"""
