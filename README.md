# Lead Scraper AI

AI-powered lead scraper for Google Maps that collects business information and sends SMS messages.

## Quick Start

### Running the Scraper

**Option 1: Use the run script (easiest)**
```bash
./run.sh
```

**Option 2: Use python3 directly**
```bash
python3 main.py
```

**Option 3: Run with SMS sending**
```bash
python3 main.py --send-sms
```

**Option 4: Only send SMS (skip scraping)**
```bash
python3 main.py --sms-only
```

### Running Autopilot (Daily Automation)

```bash
python3 autopilot.py
```

This will run the scraper automatically every day at 10:00 AM. Logs are saved to `autopilot.log`.

## Setup

1. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

2. **Configure your settings:**
   - Edit `lead_config.py` to set your locations and categories
   - Add your Google Sheets credentials as `credentials.json`
   - Add your Twilio credentials to `.env` file:
     ```
     TWILIO_ACCOUNT_SID=your_account_sid
     TWILIO_AUTH_TOKEN=your_auth_token
     TWILIO_PHONE_NUMBER=your_twilio_number
     ```

## Configuration

Edit `lead_config.py` to customize:
- `SEARCH_LOCATIONS`: List of locations to search
- `BUSINESS_CATEGORIES`: List of business types to find
- `MAX_RESULTS_PER_CATEGORY`: Number of leads per category per location
- `DELAY_BETWEEN_REQUESTS`: Delay between searches (seconds)

## Features

- ✅ Deep scrolling to find more leads
- ✅ Two-pass strategy: fast list scrape + detail page enrichment
- ✅ Automatic phone number and website extraction
- ✅ Google Sheets integration
- ✅ SMS sending via Twilio
- ✅ Detailed logging and statistics
- ✅ Daily autopilot scheduling

## Troubleshooting

**"command not found: python"**
- Use `python3` instead of `python` on macOS
- Or use the `./run.sh` script

**CAPTCHA blocking searches**
- The scraper will detect CAPTCHAs and prompt you to solve them manually
- Increase `DELAY_BETWEEN_REQUESTS` in `lead_config.py` to reduce CAPTCHA frequency

**No results for certain categories**
- Check the detailed logs to see why searches are failing
- Some categories may have limited results in certain locations
- Try adjusting the search query in `BUSINESS_CATEGORIES`

## Logs

- Main scraper: Console output
- Autopilot: Saved to `autopilot.log`
