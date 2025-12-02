"""
Google Sheets Manager
Handles saving leads to Google Sheets
"""

import gspread
from google.oauth2.service_account import Credentials
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    def add_lead(self, business_info, sms_sent=False, sms_date=None, notes=""):
        """
        Add a lead to Google Sheets with improved error handling

        business_info keys we expect (all optional):
        - name
        - address
        - state
        - phone
        - website
        - category
        - search_location
        - search_category
        - rating
        """
        try:
            # Validate we have at least a name
            name = business_info.get("name", "").strip()
            if not name or name == "N/A":
                logger.warning("Skipping lead with no name")
                return False
            
            # Get existing leads (with retry)
            all_values = []
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    all_values = self.sheet.get_all_values()
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Error reading sheet (attempt {attempt + 1}), retrying...")
                        time.sleep(1)
                    else:
                        logger.error(f"Failed to read sheet after {max_retries} attempts: {e}")
                        return False
            
            phone = business_info.get("phone", "").strip()
            address = business_info.get("address", "").strip()

            # Skip if already exists (same phone or same name+address)
            for row in all_values[1:]:  # Skip header
                if len(row) < 5:  # Skip incomplete rows
                    continue
                    
                existing_name = (row[1] if len(row) > 1 else "").strip()
                existing_phone = (row[4] if len(row) > 4 else "").strip()
                existing_address = (row[2] if len(row) > 2 else "").strip()

                # Check by phone (if both have phones)
                if phone and phone != "N/A" and existing_phone and existing_phone == phone:
                    logger.debug(f"Lead already exists (phone): {name}")
                    return False

                # Check by name+address (if both have addresses)
                if (
                    name
                    and existing_name == name
                    and address
                    and address != "N/A"
                    and existing_address
                    and existing_address == address
                ):
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
            for attempt in range(max_retries):
                try:
                    self.sheet.append_row(row)
                    logger.info(f"✅ Added lead: {name} | {phone if phone != 'N/A' else 'No phone'}")
                    return True
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"Error appending row (attempt {attempt + 1}), retrying...")
                        time.sleep(1)
                    else:
                        logger.error(f"Failed to add lead after {max_retries} attempts: {e}")
                        return False

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


