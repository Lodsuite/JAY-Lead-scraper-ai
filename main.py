"""
Main Lead Scraper Script
Orchestrates scraping, saving to Google Sheets, and sending SMS
"""

import logging
import time
import random
import os
from google_maps_scraper import GoogleMapsScraper
from google_sheets_manager import GoogleSheetsManager
from sms_sender import SMSSender
import lead_config as config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LeadScraper:
    def __init__(self):
        """Initialize the Lead Scraper with all components"""
        self.scraper = None
        self.sheets_manager = None
        self.sms_sender = None
        self.all_leads = []

        # Initialize components
        self.initialize_components()

    def initialize_components(self):
        """Initialize all components"""
        try:
            # Validate credentials file exists
            if not os.path.exists(config.GOOGLE_SHEETS_CREDENTIALS_FILE):
                error_msg = f"❌ Missing credentials file: {config.GOOGLE_SHEETS_CREDENTIALS_FILE}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Initialize Google Maps Scraper
            logger.info("Initializing Google Maps Scraper...")
            self.scraper = GoogleMapsScraper(headless=False)

            # Initialize Google Sheets Manager
            logger.info("Initializing Google Sheets Manager...")
            self.sheets_manager = GoogleSheetsManager(
                credentials_file=config.GOOGLE_SHEETS_CREDENTIALS_FILE,
                sheet_id=config.GOOGLE_SHEET_ID,
                sheet_name=config.GOOGLE_SHEET_NAME
            )

            # Initialize SMS Sender
            logger.info("Initializing SMS Sender...")
            if not config.TWILIO_ACCOUNT_SID or not config.TWILIO_AUTH_TOKEN:
                logger.warning("⚠️  Twilio credentials not found in .env file. SMS sending will be disabled.")
            self.sms_sender = SMSSender(
                account_sid=config.TWILIO_ACCOUNT_SID,
                auth_token=config.TWILIO_AUTH_TOKEN,
                from_number=config.TWILIO_PHONE_NUMBER
            )

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise

    def scrape_leads(self):
        """Scrape leads from Google Maps for all categories and locations"""
        logger.info("=" * 70)
        logger.info("🚀 Starting lead scraping process...")
        logger.info("=" * 70)
        logger.info(f"📍 Locations to search: {len(config.SEARCH_LOCATIONS)}")
        for loc in config.SEARCH_LOCATIONS:
            logger.info(f"   - {loc}")
        logger.info(f"🏢 Categories to search: {len(config.BUSINESS_CATEGORIES)}")
        for cat in config.BUSINESS_CATEGORIES:
            logger.info(f"   - {cat}")
        logger.info(f"🎯 Target: {config.MAX_RESULTS_PER_CATEGORY} leads per category per location")
        logger.info(f"📊 Expected total: ~{len(config.SEARCH_LOCATIONS) * len(config.BUSINESS_CATEGORIES) * config.MAX_RESULTS_PER_CATEGORY} leads")
        logger.info("=" * 70 + "\n")
        
        all_leads = []
        
        # Track statistics
        stats = {}
        category_stats = {}  # Track stats per category
        total_searches = len(config.SEARCH_LOCATIONS) * len(config.BUSINESS_CATEGORIES)
        successful_searches = 0
        failed_searches = 0
        zero_result_searches = 0

        for location in config.SEARCH_LOCATIONS:
            logger.info(f"\n{'=' * 50}")
            logger.info(f"Searching in location: {location}")
            logger.info(f"{'=' * 50}\n")
            
            location_leads = 0

            for category in config.BUSINESS_CATEGORIES:
                logger.info(f"\n{'─' * 60}")
                logger.info(f"🔍 Searching for: '{category}' in '{location}'")
                logger.info(f"{'─' * 60}")

                try:
                    # Pass 1: fast list-only scrape
                    businesses = self.scraper.search_businesses(
                        query=category,
                        location=location,
                        max_results=config.MAX_RESULTS_PER_CATEGORY
                    )

                    # Track results
                    category_key = f"{category}"
                    if category_key not in category_stats:
                        category_stats[category_key] = {"total": 0, "successful": 0, "zero": 0, "failed": 0}
                    
                    if len(businesses) == 0:
                        zero_result_searches += 1
                        category_stats[category_key]["zero"] += 1
                        logger.warning(f"⚠️  Found 0 results for '{category}' in '{location}'")
                        logger.warning(f"   Possible causes: No businesses match this category, CAPTCHA blocking, or search query issue")
                    else:
                        successful_searches += 1
                        location_leads += len(businesses)
                        category_stats[category_key]["total"] += len(businesses)
                        category_stats[category_key]["successful"] += 1
                        logger.info(f"   ✅ Successfully found {len(businesses)} leads")

                    # Optional Pass 2: enrich only leads that are missing phone numbers
                    if config.ENRICH_MISSING_PHONES and len(businesses) > 0:
                        businesses = self.scraper.enrich_missing_phones(
                            leads=businesses,
                            query=category,
                            location=location,
                            max_clicks=getattr(
                                config,
                                "ENRICH_MAX_CLICKS_PER_SEARCH",
                                20,
                            ),
                        )

                    # Add location and search category to each business
                    for business in businesses:
                        business["search_location"] = location
                        business["search_category"] = category

                    all_leads.extend(businesses)
                    logger.info(f"✅ Found {len(businesses)}/{config.MAX_RESULTS_PER_CATEGORY} businesses for {category} in {location}")

                    # Random delay between searches to appear more human-like and avoid rate limiting
                    # Adds 0-3 seconds randomly to the base delay
                    random_delay = config.DELAY_BETWEEN_REQUESTS + random.uniform(0, 3)
                    logger.debug(f"Waiting {random_delay:.1f} seconds before next search...")
                    time.sleep(random_delay)

                except Exception as e:
                    failed_searches += 1
                    category_key = f"{category}"
                    if category_key not in category_stats:
                        category_stats[category_key] = {"total": 0, "successful": 0, "zero": 0, "failed": 0}
                    category_stats[category_key]["failed"] += 1
                    logger.error(f"❌ Error searching for '{category}' in '{location}': {e}")
                    logger.error(f"   This search will be skipped. Check logs above for details.")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue
            
            stats[location] = location_leads
            logger.info(f"📍 Total for {location}: {location_leads} leads")

        # Print summary
        logger.info(f"\n{'=' * 70}")
        logger.info("📊 SCRAPING SUMMARY")
        logger.info(f"{'=' * 70}")
        logger.info(f"Total searches attempted: {total_searches}")
        logger.info(f"✅ Successful searches (found results): {successful_searches}")
        logger.info(f"⚠️  Searches with 0 results: {zero_result_searches}")
        logger.info(f"❌ Failed searches (errors): {failed_searches}")
        logger.info(f"\n📍 Leads per location:")
        for loc, count in stats.items():
            logger.info(f"   {loc}: {count} leads")
        
        # Category breakdown - detailed stats
        logger.info(f"\n📋 Detailed results by category:")
        category_lead_counts = {}
        for lead in all_leads:
            cat = lead.get("search_category", "Unknown")
            category_lead_counts[cat] = category_lead_counts.get(cat, 0) + 1
        
        # Show stats for each category
        for cat in config.BUSINESS_CATEGORIES:
            lead_count = category_lead_counts.get(cat, 0)
            stats = category_stats.get(cat, {"total": 0, "successful": 0, "zero": 0, "failed": 0})
            logger.info(f"   {cat}:")
            logger.info(f"      Leads collected: {lead_count}")
            logger.info(f"      Successful searches: {stats['successful']}/{len(config.SEARCH_LOCATIONS)}")
            logger.info(f"      Zero-result searches: {stats['zero']}")
            logger.info(f"      Failed searches: {stats['failed']}")
            if stats['successful'] == 0 and stats['failed'] == 0 and stats['zero'] == len(config.SEARCH_LOCATIONS):
                logger.warning(f"      ⚠️  WARNING: This category returned 0 results in ALL locations!")
        
        logger.info(f"\n{'=' * 70}")
        logger.info(f"🎯 TOTAL LEADS COLLECTED: {len(all_leads)}")
        expected = total_searches * config.MAX_RESULTS_PER_CATEGORY
        if expected > 0:
            percentage = (len(all_leads) / expected) * 100
            logger.info(f"Expected: ~{expected} leads")
            logger.info(f"Actual: {len(all_leads)} leads ({percentage:.1f}% of expected)")
        logger.info(f"{'=' * 70}\n")

        # Keep ALL leads - no deduplication (you can filter duplicates in Google Sheets if needed)
        self.all_leads = all_leads
        return all_leads

    def remove_duplicates(self, leads):
        """
        Remove duplicates - only by phone number (if phone exists).
        This is less aggressive - we only remove if it's the exact same phone number.
        Different businesses with same name but different locations will be kept.
        """
        seen_phones = set()
        unique_leads = []
        skipped_count = 0

        for lead in leads:
            phone = lead.get("phone", "")
            
            # Only dedupe if we have a valid phone number
            if phone and phone != "N/A" and phone.strip():
                # Normalize phone (remove spaces, dashes, etc. for comparison)
                normalized_phone = ''.join(filter(str.isdigit, phone))
                if normalized_phone in seen_phones:
                    skipped_count += 1
                    continue
                seen_phones.add(normalized_phone)
            
            # Always add the lead (even if no phone - we want all leads)
            unique_leads.append(lead)

        if skipped_count > 0:
            logger.info(f"Removed {skipped_count} duplicate leads (same phone number)")

        return unique_leads

    def save_leads_to_sheets(self, leads):
        """Save leads to Google Sheets using efficient batch insert"""
        # Get existing leads count before saving
        try:
            existing_leads = self.sheets_manager.get_all_leads()
            existing_leads_count = len(existing_leads)
        except Exception as e:
            logger.warning(f"Could not get existing leads count: {e}")
            existing_leads_count = 0

        logger.info(f"\n{'=' * 70}")
        logger.info(f"💾 SAVING LEADS TO GOOGLE SHEETS")
        logger.info(f"{'=' * 70}")
        logger.info(f"Leads to process: {len(leads)}")
        logger.info(f"Using batch insert for reliability...")

        try:
            # Use batch insert - MUCH faster and more reliable
            added, skipped, failed = self.sheets_manager.add_leads_batch(leads)

            # Print statistics
            print(f"\n{'=' * 70}")
            print(f"📊 GOOGLE SHEETS SAVE RESULTS")
            print(f"{'=' * 70}")
            print(f"📋 Existing leads before this run: {existing_leads_count}")
            print(f"✅ New leads added: {added}")
            print(f"⏭️  Skipped (duplicates/invalid): {skipped}")
            if failed > 0:
                print(f"❌ Failed to save: {failed}")
            print(f"🎯 Total leads after this run: {existing_leads_count + added}")
            print(f"{'=' * 70}\n")

            if failed > 0:
                logger.warning(f"⚠️  {failed} leads failed to save. Check logs for details.")

            return added

        except Exception as e:
            logger.error(f"❌ Critical error saving leads: {e}")
            import traceback
            logger.debug(traceback.format_exc())

            # Fallback to single insert if batch fails
            logger.info("Attempting fallback to single-row insert...")
            saved_count = 0
            for lead in leads:
                try:
                    if self.sheets_manager.add_lead(lead):
                        saved_count += 1
                    time.sleep(1)  # Longer delay for safety
                except Exception as inner_e:
                    logger.error(f"Error saving {lead.get('name', 'Unknown')}: {inner_e}")

            return saved_count

    def send_sms_to_leads(self, send_to_all: bool = False):
        """
        Send SMS to leads

        Args:
            send_to_all: If True, send to all leads. If False, only send to leads without SMS
        """
        logger.info("\nPreparing to send SMS messages...")

        if send_to_all:
            leads = self.sheets_manager.get_all_leads()
        else:
            leads = self.sheets_manager.get_leads_without_sms()

        if not leads:
            logger.info("No leads found to send SMS to.")
            return

        logger.info(f"Found {len(leads)} leads to send SMS to.")

        # Filter leads with valid phone numbers (handle both case variations)
        valid_leads = []
        for lead in leads:
            phone = lead.get("Phone", "") or lead.get("phone", "")
            if phone and phone != "N/A":
                valid_leads.append(lead)

        logger.info(f"{len(valid_leads)} leads have valid phone numbers.")

        if not valid_leads:
            logger.warning("No leads with valid phone numbers found.")
            return

        # Confirm before sending
        print(f"\n{'=' * 50}")
        print(f"Ready to send SMS to {len(valid_leads)} leads")
        print(f"{'=' * 50}")
        response = input("Do you want to proceed? (yes/no): ").strip().lower()

        if response != "yes":
            logger.info("SMS sending cancelled by user.")
            return

        # Send SMS
        logger.info("Sending SMS messages...")
        results = self.sms_sender.send_bulk_sms(
            leads=valid_leads,
            message_template=config.SMS_MESSAGE_TEMPLATE,
            delay=config.DELAY_BETWEEN_REQUESTS
        )

        # Update Google Sheets with SMS status
        successful = 0
        failed = 0

        for result in results:
            if result.get("success"):
                successful += 1
                # Update sheet
                self.sheets_manager.update_lead_sms_status(
                    phone=result.get("to", ""),
                    sms_sent=True,
                    sms_date=result.get("date_sent", "")
                )
            else:
                failed += 1
                logger.warning(
                    f"Failed to send SMS to {result.get('business', 'Unknown')}: "
                    f"{result.get('error', 'Unknown error')}"
                )

        logger.info(f"\nSMS sending complete!")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")

    def run_full_pipeline(self, send_sms: bool = False):
        """
        Run the complete lead scraping pipeline

        Args:
            send_sms: Whether to send SMS after scraping (default: False)
        """
        try:
            # Step 1: Scrape leads
            leads = self.scrape_leads()

            if not leads:
                logger.warning("No leads found. Exiting.")
                return

            # Step 2: Save to Google Sheets
            self.save_leads_to_sheets(leads)

            # Step 3: Send SMS (if requested)
            if send_sms:
                self.send_sms_to_leads(send_to_all=False)

            logger.info("\n" + "=" * 50)
            logger.info("Lead scraping pipeline completed successfully!")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Error in pipeline: {e}")
            raise
        finally:
            # Cleanup
            if self.scraper:
                self.scraper.close()

    def cleanup(self):
        """Cleanup resources"""
        if self.scraper:
            self.scraper.close()
        logger.info("Cleanup complete")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Lead Scraper for Security Services")
    parser.add_argument(
        "--send-sms",
        action="store_true",
        help="Send SMS messages to leads after scraping",
    )
    parser.add_argument(
        "--sms-only",
        action="store_true",
        help="Only send SMS to existing leads (skip scraping)",
    )

    args = parser.parse_args()

    scraper = LeadScraper()

    try:
        if args.sms_only:
            scraper.send_sms_to_leads(send_to_all=False)
        else:
            scraper.run_full_pipeline(send_sms=args.send_sms)
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        scraper.cleanup()


if __name__ == "__main__":
    main()
