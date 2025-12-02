# Quick Setup Guide

Follow these steps to get your lead scraper up and running:

## Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Google Sheets API

1. **Create a Google Cloud Project:**
   - Go to https://console.cloud.google.com/
   - Click "Create Project" or select an existing one
   - Give it a name (e.g., "Lead Scraper")

2. **Enable APIs:**
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API" and enable it
   - Search for "Google Drive API" and enable it

3. **Create Service Account:**
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Name: "lead-scraper-service"
   - Click "Create and Continue"
   - Grant role: "Editor"
   - Click "Continue" then "Done"

4. **Create Credentials:**
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Select "JSON"
   - Download the file
   - Rename it to `credentials.json` and place it in the project folder

5. **Create Google Sheet:**
   - Create a new Google Sheet at https://sheets.google.com
   - Name it "Lead Scraper Results" (or any name you prefer)
   - Click "Share" button
   - Add the service account email (found in credentials.json, looks like: `xxx@xxx.iam.gserviceaccount.com`)
   - Give it "Editor" access
   - Copy the Sheet ID from the URL:
     - URL format: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
     - Copy the `SHEET_ID_HERE` part

## Step 3: Set Up Twilio (for SMS)

1. **Sign up for Twilio:**
   - Go to https://www.twilio.com/try-twilio
   - Create a free account (includes trial credits)

2. **Get Credentials:**
   - Go to Twilio Console Dashboard
   - Copy your "Account SID" and "Auth Token"
   - Go to "Phone Numbers" > "Manage" > "Buy a number" (or use trial number)
   - Copy your Twilio phone number

## Step 4: Configure the Application

1. **Create .env file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit .env file** and add your credentials:
   ```
   GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
   GOOGLE_SHEET_ID=your_sheet_id_here
   GOOGLE_SHEET_NAME=Leads
   
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
   ```

3. **Edit lead_config.py** to customize:
   - `SEARCH_LOCATIONS`: Add cities/areas you want to search
   - `BUSINESS_CATEGORIES`: Modify if needed
   - `SMS_MESSAGE_TEMPLATE`: Customize your message
   - `MAX_RESULTS_PER_CATEGORY`: Adjust based on your needs

## Step 5: Test the Setup

1. **Test Google Sheets connection:**
   ```bash
   python -c "from google_sheets_manager import GoogleSheetsManager; import lead_config as config; gs = GoogleSheetsManager(config.GOOGLE_SHEETS_CREDENTIALS_FILE, config.GOOGLE_SHEET_ID, config.GOOGLE_SHEET_NAME); print('Connected successfully!')"
   ```

2. **Run a small test scrape:**
   - Edit `lead_config.py` and set `MAX_RESULTS_PER_CATEGORY = 5` for testing
   - Edit `SEARCH_LOCATIONS` to just one city for testing
   - Run: `python main.py`
   - Check your Google Sheet to see if leads were added

## Step 6: Run the Full Scraper

Once testing works:

1. **Update lead_config.py** with your full settings
2. **Run the scraper:**
   ```bash
   python main.py
   ```

3. **To also send SMS:**
   ```bash
   python main.py --send-sms
   ```

## Troubleshooting

### ChromeDriver Issues
- Make sure Chrome browser is installed
- The script will auto-download ChromeDriver, but if it fails:
  - Download manually from https://chromedriver.chromium.org/
  - Or install via: `brew install chromedriver` (Mac)

### Google Sheets Permission Errors
- Double-check the service account email has access to the sheet
- Make sure `credentials.json` is in the project folder
- Verify the Sheet ID is correct

### Twilio SMS Errors
- Check your Twilio account balance
- Verify phone numbers are in E.164 format (+1234567890)
- Make sure you've verified recipient numbers in trial mode

### No Results Found
- Try running with `headless=False` in `google_maps_scraper.py` to see what's happening
- Google Maps may require solving captchas - you may need to run in non-headless mode initially
- Adjust `DELAY_BETWEEN_REQUESTS` if you're being rate-limited

## Important Legal Notes

⚠️ **Compliance Requirements:**
- **TCPA Compliance (US)**: You must have consent before sending SMS to businesses
- **Terms of Service**: Review Google Maps ToS and Twilio ToS
- **Data Privacy**: Ensure compliance with GDPR, CCPA, etc.

## Next Steps

1. Customize your SMS message in `lead_config.py`
2. Add more search locations
3. Set up automated scheduling (cron job, etc.)
4. Monitor your Google Sheet for new leads
5. Track SMS delivery status in the sheet

Good luck with your lead generation! 🚀

