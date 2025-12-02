"""
Autopilot script for automated daily lead scraping
Runs the lead scraper automatically on a schedule
"""
import time
import schedule
from main import LeadScraper
import logging
import sys
from datetime import datetime

# Set up logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler('autopilot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def daily_job():
    """Main job function that runs the scraping pipeline"""
    logger.info("=" * 70)
    logger.info(f"🚀 Starting daily lead scraping job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    scraper = None
    try:
        scraper = LeadScraper()
        # This will:
        # - scrape leads
        # - save to Google Sheets
        # - send SMS if send_sms=True (set to False to skip SMS)
        scraper.run_full_pipeline(send_sms=False)  # Set to True if you want automatic SMS
        logger.info("✅ Daily job completed successfully!")
    except KeyboardInterrupt:
        logger.warning("⚠️  Job interrupted by user")
    except Exception as e:
        logger.error(f"❌ Error in daily job: {e}", exc_info=True)
    finally:
        if scraper:
            scraper.cleanup()
        logger.info(f"🏁 Daily job finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70 + "\n")


# Schedule the job to run every day at 10:00 AM (local time)
# You can change this to any time you want
schedule.every().day.at("10:00").do(daily_job)

# Optional: Add a test run immediately (comment out if you don't want this)
# logger.info("Running initial test job...")
# daily_job()

logger.info("🤖 Autopilot scheduler started!")
logger.info(f"⏰ Next scheduled run: {schedule.next_run()}")
logger.info("📝 Logs are being saved to 'autopilot.log'")
logger.info("Press Ctrl+C to stop the scheduler\n")

try:
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute
except KeyboardInterrupt:
    logger.info("\n👋 Autopilot scheduler stopped by user")
    sys.exit(0)
