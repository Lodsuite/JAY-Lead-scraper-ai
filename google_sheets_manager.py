"""
Google Sheets Manager
Handles saving leads to Google Sheets

FIXES APPLIED:
- Batch insert instead of single row appends (avoids rate limiting)
- Efficient duplicate checking (load sheet once, not per lead)
- Better retry logic with exponential backoff
- Proper error handling and logging
"""

import gspread
from google.oauth2.service_account import Credentials
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets API limits
MAX_RETRIES = 5
BASE_RETRY_DELAY = 2  # seconds
BATCH_SIZE = 50  # rows per batch insert


class GoogleSheetsManager:
    def __init__(self, credentials_file, sheet_id, sheet_name):
        """
        Initialize Google Sheets Manager

        Args:
            credentials_file: Path to Google Service Account credentials JSON file
            sheet_id: Google Sheet ID
            sheet_name: Name of the worksheet
        """
        self.credentials_file = credentials_file
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name
        self.client = None
        self.sheet = None
        self.connect()

    def connect(self):
        """Connect to Google Sheets and ensure header row is correct"""
        try:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(
                self.credentials_file, scopes=scope
            )
            self.client = gspread.authorize(creds)
            spreadsheet = self.client.open_by_key(self.sheet_id)

            # Get or create worksheet
            try:
                self.sheet = spreadsheet.worksheet(self.sheet_name)
            except Exception:
                self.sheet = spreadsheet.add_worksheet(
                    title=self.sheet_name, rows=2000, cols=20
                )

            # Ensure header row is what we expect
            expected_header = [
                "Date Added",
                "Business Name",
                "Address",
                "State",
                "Phone",
                "Website",
                "Category",
                "Search Location",
                "Search Category",
                "Rating",
                "SMS Sent",
                "SMS Date",
                "Notes",
            ]

            current_header = self.sheet.row_values(1)
            if current_header != expected_header:
                logger.info("Resetting header row in Google Sheet.")
                self.sheet.clear()
                self.sheet.append_row(expected_header)

            logger.info(f"Connected to Google Sheet: {self.sheet_name}")

        except Exception as e:
            logger.error(f"Error connecting to Google Sheets: {e}")
            raise

    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except gspread.exceptions.APIError as e:
                if e.response.status_code == 429:  # Rate limited
                    delay = BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Rate limited. Waiting {delay}s before retry {attempt + 1}/{MAX_RETRIES}")
                    time.sleep(delay)
                elif attempt < MAX_RETRIES - 1:
                    delay = BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"API error: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    delay = BASE_RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Error: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise
        return None

    def _load_existing_data(self):
        """Load existing sheet data once for efficient duplicate checking"""
        try:
            all_values = self._retry_with_backoff(self.sheet.get_all_values)
            if not all_values:
                return set(), set()

            existing_phones = set()
            existing_name_address = set()

            for row in all_values[1:]:  # Skip header
                if len(row) < 5:
                    continue

                name = (row[1] if len(row) > 1 else "").strip()
                address = (row[2] if len(row) > 2 else "").strip()
                phone = (row[4] if len(row) > 4 else "").strip()

                # Normalize phone for comparison
                if phone and phone != "N/A":
                    normalized_phone = ''.join(filter(str.isdigit, phone))
                    if normalized_phone:
                        existing_phones.add(normalized_phone)

                # Name+address combo
                if name and address and address != "N/A":
                    existing_name_address.add(f"{name.lower()}|{address.lower()}")

            return existing_phones, existing_name_address
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
            return set(), set()

    def add_leads_batch(self, leads, sms_sent=False, sms_date=None, notes=""):
        """
        Add multiple leads to Google Sheets efficiently using batch insert.
        This is MUCH faster and more reliable than adding one at a time.

        Returns: (added_count, skipped_count, failed_count)
        """
        if not leads:
            return 0, 0, 0

        logger.info(f"Loading existing data for duplicate check...")
        existing_phones, existing_name_address = self._load_existing_data()
        logger.info(f"Found {len(existing_phones)} existing phones, {len(existing_name_address)} name+address combos")

        # Filter and prepare rows
        rows_to_add = []
        skipped = 0

        for lead in leads:
            name = lead.get("name", "").strip()
            if not name or name == "N/A":
                skipped += 1
                continue

            phone = lead.get("phone", "").strip()
            address = lead.get("address", "").strip()

            # Check duplicates
            is_duplicate = False

            # Check phone
            if phone and phone != "N/A":
                normalized_phone = ''.join(filter(str.isdigit, phone))
                if normalized_phone and normalized_phone in existing_phones:
                    logger.debug(f"Duplicate (phone): {name}")
                    skipped += 1
                    is_duplicate = True
                else:
                    existing_phones.add(normalized_phone)  # Add to set to catch dupes within batch

            # Check name+address
            if not is_duplicate and name and address and address != "N/A":
                combo = f"{name.lower()}|{address.lower()}"
                if combo in existing_name_address:
                    logger.debug(f"Duplicate (name+address): {name}")
                    skipped += 1
                    is_duplicate = True
                else:
                    existing_name_address.add(combo)

            if is_duplicate:
                continue

            # Prepare row
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                name,
                address if address else "N/A",
                lead.get("state", "N/A"),
                phone if phone else "N/A",
                lead.get("website", "N/A"),
                lead.get("category", "N/A"),
                lead.get("search_location", "N/A"),
                lead.get("search_category", "N/A"),
                lead.get("rating", "N/A"),
                "Yes" if sms_sent else "No",
                sms_date if sms_date else "",
                notes,
            ]
            rows_to_add.append(row)

        if not rows_to_add:
            logger.info("No new leads to add (all duplicates or invalid)")
            return 0, skipped, 0

        # Batch insert with chunking
        added = 0
        failed = 0

        for i in range(0, len(rows_to_add), BATCH_SIZE):
            batch = rows_to_add[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(rows_to_add) + BATCH_SIZE - 1) // BATCH_SIZE

            logger.info(f"Inserting batch {batch_num}/{total_batches} ({len(batch)} rows)...")

            try:
                # Use append_rows for batch insert (much more efficient)
                self._retry_with_backoff(
                    self.sheet.append_rows,
                    batch,
                    value_input_option='USER_ENTERED'
                )
                added += len(batch)
                logger.info(f"✅ Batch {batch_num} inserted successfully")

                # Small delay between batches to be safe
                if i + BATCH_SIZE < len(rows_to_add):
                    time.sleep(1)

            except Exception as e:
                logger.error(f"❌ Failed to insert batch {batch_num}: {e}")
                failed += len(batch)

        logger.info(f"Batch insert complete: {added} added, {skipped} skipped, {failed} failed")
        return added, skipped, failed

    def add_lead(self, business_info, sms_sent=False, sms_date=None, notes=""):
        """
        Add a single lead to Google Sheets.
        NOTE: For multiple leads, use add_leads_batch() instead - it's much faster!

        business_info keys we expect (all optional):
        - name, address, state, phone, website, category
        - search_location, search_category, rating
        """
        try:
            name = business_info.get("name", "").strip()
            if not name or name == "N/A":
                logger.warning("Skipping lead with no name")
                return False

            # Load existing data for duplicate check
            existing_phones, existing_name_address = self._load_existing_data()

            phone = business_info.get("phone", "").strip()
            address = business_info.get("address", "").strip()

            # Check duplicates
            if phone and phone != "N/A":
                normalized_phone = ''.join(filter(str.isdigit, phone))
                if normalized_phone in existing_phones:
                    logger.debug(f"Lead already exists (phone): {name}")
                    return False

            if name and address and address != "N/A":
                combo = f"{name.lower()}|{address.lower()}"
                if combo in existing_name_address:
                    logger.debug(f"Lead already exists (name+address): {name}")
                    return False

            # Prepare row data
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                name,
                address if address else "N/A",
                business_info.get("state", "N/A"),
                phone if phone else "N/A",
                business_info.get("website", "N/A"),
                business_info.get("category", "N/A"),
                business_info.get("search_location", "N/A"),
                business_info.get("search_category", "N/A"),
                business_info.get("rating", "N/A"),
                "Yes" if sms_sent else "No",
                sms_date if sms_date else "",
                notes,
            ]

            # Append with retry
            self._retry_with_backoff(self.sheet.append_row, row)
            logger.info(f"✅ Added lead: {name} | {phone if phone != 'N/A' else 'No phone'}")
            return True

        except Exception as e:
            logger.error(f"❌ Error adding lead to sheet: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def update_lead_sms_status(self, phone, sms_sent=True, sms_date=None, notes=""):
        """
        Update SMS status for a lead based on phone number
        """
        try:
            all_values = self.sheet.get_all_values()
            # Column indices (1-based):
            # 1: Date Added, 2: Name, 3: Address, 4: State, 5: Phone
            PHONE_COL = 5
            SMS_SENT_COL = 11
            SMS_DATE_COL = 12
            NOTES_COL = 13

            for i, row in enumerate(all_values[1:], start=2):  # row 2 onwards
                if len(row) >= PHONE_COL and row[PHONE_COL - 1] == phone:
                    self.sheet.update_cell(i, SMS_SENT_COL, "Yes" if sms_sent else "No")
                    if sms_date:
                        self.sheet.update_cell(i, SMS_DATE_COL, sms_date)
                    if notes:
                        self.sheet.update_cell(i, NOTES_COL, notes)
                    logger.info(f"Updated SMS status for: {phone}")
                    return True

            logger.warning(f"Lead not found with phone: {phone}")
            return False

        except Exception as e:
            logger.error(f"Error updating SMS status: {e}")
            return False

    def get_all_leads(self):
        """Return all leads as list[dict]"""
        try:
            all_values = self.sheet.get_all_values()
            if not all_values:
                return []
            headers = all_values[0]
            leads = []
            for row in all_values[1:]:
                lead = dict(zip(headers, row))
                leads.append(lead)
            return leads
        except Exception as e:
            logger.error(f"Error getting leads: {e}")
            return []

    def get_leads_without_sms(self):
        """Return leads that have not been sent SMS yet"""
        try:
            all_leads = self.get_all_leads()
            return [
                lead
                for lead in all_leads
                if lead.get("SMS Sent", "").strip().lower() != "yes"
            ]
        except Exception as e:
            logger.error(f"Error getting leads without SMS: {e}")
            return []


