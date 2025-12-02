# Next Steps to Complete Your Lead Scraper Project

## ✅ What Should Be Working Now

1. **No Deduplication** - All leads are saved (no filtering)
2. **Search Box Method** - More reliable than URL navigation
3. **Two-Pass Strategy** - Gets phones/websites from detail pages when missing
4. **Comprehensive Extraction** - Multiple fallback selectors for phones/websites

## 🔍 Step 1: Test with Small Numbers First

1. **Set test configuration** in `lead_config.py`:
   ```python
   MAX_RESULTS_PER_CATEGORY = 2  # Just 2 per category for testing
   SEARCH_LOCATIONS = ["New York, NY"]  # Just one location
   BUSINESS_CATEGORIES = ["bars"]  # Just one category
   ```

2. **Run the scraper**:
   ```bash
   python3 main.py
   ```

3. **Check your Google Sheet** - You should see leads appearing

## 🔧 Step 2: Verify Each Component

### A. Check Google Sheets Connection
```bash
python3 -c "from google_sheets_manager import GoogleSheetsManager; import lead_config as config; gs = GoogleSheetsManager(config.GOOGLE_SHEETS_CREDENTIALS_FILE, config.GOOGLE_SHEET_ID, config.GOOGLE_SHEET_NAME); print('✅ Connected!')"
```

### B. Check What's Being Scraped
Watch the console output - you should see lines like:
```
[1/2] Business Name | Address | State | Phone | Website | Rating
```

### C. Check Your Google Sheet
- Open: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
- Check the "Leads3" tab
- Verify columns: Date Added, Business Name, Address, State, Phone, Website, etc.

## 📊 Step 3: Scale Up Gradually

Once testing works:

1. **Increase locations** (one at a time):
   ```python
   SEARCH_LOCATIONS = ["New York, NY", "Queens, NY"]  # Add one more
   ```

2. **Increase categories** (one at a time):
   ```python
   BUSINESS_CATEGORIES = ["bars", "restaurants"]  # Add one more
   ```

3. **Increase results per category**:
   ```python
   MAX_RESULTS_PER_CATEGORY = 10  # Then 20, then 50
   ```

## 🐛 Common Issues & Fixes

### Issue: "0 leads found"
**Fix**: 
- Check if Chrome browser opens (headless=False)
- Look for Google Maps captcha - you may need to solve it manually
- Check console for error messages

### Issue: "No phone numbers"
**Fix**:
- The enrichment pass should fill these in
- Check `ENRICH_MISSING_PHONES = True` in config
- Increase `ENRICH_MAX_CLICKS_PER_SEARCH` if needed

### Issue: "Leads not saving to sheet"
**Fix**:
- Verify `credentials.json` exists and is valid
- Check service account email has access to the sheet
- Verify `GOOGLE_SHEET_ID` and `GOOGLE_SHEET_NAME` are correct

### Issue: "Too slow"
**Fix**:
- Reduce `MAX_RESULTS_PER_CATEGORY`
- Reduce number of locations/categories
- Increase `DELAY_BETWEEN_REQUESTS` if getting rate limited

## 🎯 Step 4: Final Configuration

When everything works, set your final config:

```python
# lead_config.py
MAX_RESULTS_PER_CATEGORY = 20  # Adjust based on your needs
ENRICH_MISSING_PHONES = True
ENRICH_MAX_CLICKS_PER_SEARCH = 50  # Enough to get missing phones
DELAY_BETWEEN_REQUESTS = 2  # Don't go too fast
```

## 📱 Step 5: Test SMS (Optional)

Once you have leads in the sheet:

```bash
python3 main.py --sms-only
```

This will send SMS to leads that haven't received one yet.

## ✅ Final Checklist

- [ ] Test scraper with 1 location, 1 category, 2 results
- [ ] Verify leads appear in Google Sheet
- [ ] Check that phone numbers are being collected
- [ ] Verify enrichment pass is filling missing phones
- [ ] Scale up gradually (add locations/categories one at a time)
- [ ] Test SMS sending (if using Twilio)
- [ ] Set final configuration for production use

## 🆘 If Still Not Working

1. **Check the logs** - Look for ERROR messages
2. **Run with visible browser** - `headless=False` to see what's happening
3. **Test one component at a time** - Scraper, then Sheets, then SMS
4. **Check Google Sheets** - Make sure the sheet exists and is accessible

## 📝 Notes

- The scraper now saves ALL leads (no deduplication)
- You can remove duplicates in Google Sheets using filters if needed
- The two-pass strategy ensures maximum phone/website collection
- Be patient - scraping takes time, especially with enrichment enabled

Good luck! 🚀

