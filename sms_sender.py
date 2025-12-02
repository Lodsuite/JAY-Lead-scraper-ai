"""
SMS Sender using Twilio
Handles sending SMS messages to leads
"""
from twilio.rest import Client
import logging
from datetime import datetime
import re
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SMSSender:
    def __init__(self, account_sid, auth_token, from_number):
        """
        Initialize SMS Sender
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Twilio phone number to send from
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.client = None
        
        if account_sid and auth_token:
            try:
                self.client = Client(account_sid, auth_token)
                logger.info("Twilio client initialized")
            except Exception as e:
                logger.error(f"Error initializing Twilio client: {e}")
        else:
            logger.warning("Twilio credentials not provided. SMS sending will be disabled.")
    
    def format_phone_number(self, phone):
        """
        Format phone number to E.164 format for Twilio
        
        Args:
            phone: Phone number string
            
        Returns:
            Formatted phone number or None if invalid
        """
        if not phone or phone == "N/A":
            return None
        
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # If it doesn't start with +, assume US number
        if not cleaned.startswith('+'):
            if len(cleaned) == 10:
                cleaned = '+1' + cleaned
            elif len(cleaned) == 11 and cleaned.startswith('1'):
                cleaned = '+' + cleaned
            else:
                logger.warning(f"Invalid phone number format: {phone}")
                return None
        
        return cleaned
    
    def send_sms(self, to_number, message):
        """
        Send SMS message
        
        Args:
            to_number: Recipient phone number
            message: Message text
            
        Returns:
            Dictionary with status information or None if failed
        """
        if not self.client:
            logger.error("Twilio client not initialized. Cannot send SMS.")
            return None
        
        try:
            formatted_number = self.format_phone_number(to_number)
            if not formatted_number:
                logger.warning(f"Could not format phone number: {to_number}")
                return None
            
            # Send SMS
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=formatted_number
            )
            
            logger.info(f"SMS sent successfully to {formatted_number}. SID: {message_obj.sid}")
            
            return {
                'success': True,
                'sid': message_obj.sid,
                'status': message_obj.status,
                'to': formatted_number,
                'date_sent': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"Error sending SMS to {to_number}: {e}")
            return {
                'success': False,
                'error': str(e),
                'to': to_number
            }
    
    def send_bulk_sms(self, leads, message_template, delay=2):
        """
        Send SMS to multiple leads
        
        Args:
            leads: List of lead dictionaries
            message_template: Message template with {business_name} placeholder
            delay: Delay between messages in seconds
            
        Returns:
            List of results for each SMS sent
        """
        results = []
        
        for lead in leads:
            # Handle both lowercase (from scraper) and capitalized (from Google Sheets) keys
            phone = lead.get('phone', '') or lead.get('Phone', '')
            business_name = lead.get('name', '') or lead.get('Business Name', 'Business')
            
            if not phone or phone == "N/A":
                logger.warning(f"No phone number for {business_name}. Skipping.")
                results.append({
                    'success': False,
                    'error': 'No phone number',
                    'business': business_name
                })
                continue
            
            # Format message
            message = message_template.format(business_name=business_name)
            
            # Send SMS
            result = self.send_sms(phone, message)
            if result:
                result['business'] = business_name
                results.append(result)
            
            # Delay between messages to avoid rate limiting
            time.sleep(delay)
        
        return results

