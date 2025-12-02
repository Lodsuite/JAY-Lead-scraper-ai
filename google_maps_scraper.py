"""
Google Maps Scraper for Lead Generation
Clicks into each business and collects:
- name
- full address
- state (parsed from address)
- phone
- website
- rating
"""

import logging
import re
import time
import random
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleMapsScraper:
    def __init__(self, headless: bool = True):
        self.driver = None
        self.headless = headless
        self.setup_driver()

    def setup_driver(self):
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        # Anti-detection measures to reduce CAPTCHA frequency
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Standard options
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Updated user agent to latest Chrome version
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        driver_path = Path(ChromeDriverManager().install())

        # Newer Chrome-for-Testing bundles sometimes point to the THIRD_PARTY notice file.
        if driver_path.name.startswith("THIRD_PARTY") or not driver_path.is_file():
            candidate = driver_path.with_name("chromedriver")
            if candidate.exists():
                driver_path = candidate
            else:
                # Look inside the directory for an executable named chromedriver
                for child in driver_path.parent.iterdir():
                    if child.name == "chromedriver":
                        driver_path = child
                        break

        # Ensure the binary is executable
        driver_path.chmod(driver_path.stat().st_mode | 0o111)

        service = Service(str(driver_path))
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to remove webdriver property (anti-detection)
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            '''
        })
        
        logger.info("Chrome WebDriver successfully initialized with anti-detection measures.")

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome driver closed successfully.")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")

    # ---------- helpers ----------

    def _wait_and_get_text(self, candidates, timeout=8):
        """
        candidates: list of tuples (By, selector, attribute)
        attr can be None to use element.text
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            for by, selector, attr in candidates:
                try:
                    el = self.driver.find_element(by, selector)
                    text = el.get_attribute(attr) if attr else el.text
                    if text:
                        text = text.strip()
                        if text:
                            return text
                except Exception:
                    continue
            time.sleep(0.3)
        return "N/A"

    def _clean_phone_text(self, phone_text: str) -> str:
        if phone_text.startswith("Phone:"):
            phone_text = phone_text.split("Phone:", 1)[1].strip()
        if phone_text.startswith("Call:"):
            phone_text = phone_text.split("Call:", 1)[1].strip()
        return phone_text or "N/A"

    def _get_state_from_address(self, address: str) -> str:
        """
        Try to extract a 2-letter state code from something like:
        '123 Main St, New York, NY 10001'
        """
        try:
            parts = [p.strip() for p in address.split(",")]
            if len(parts) >= 3:
                state_zip = parts[-1]  # 'NY 10001'
                state_part = state_zip.split()[0]
                if len(state_part) == 2 and state_part.isalpha():
                    return state_part.upper()
        except Exception:
            pass
        return "N/A"

    # ---------- main search ----------

    def search_businesses(self, query, location, max_results=50):
        """
        Search Google Maps for businesses using the search box (more reliable than URL navigation).
        """
        logger.info(f"Searching Google Maps for '{query}' in '{location}'")
        results = []

        wait_results = WebDriverWait(self.driver, 20)
        wait_search = WebDriverWait(self.driver, 10)

        # Always start fresh at Google Maps homepage
        self.driver.get("https://www.google.com/maps")
        # Random wait to appear more human-like
        time.sleep(2 + random.uniform(0, 2))

        # Handle cookie / consent popups if they appear
        try:
            consent_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(., 'Accept all') or contains(., 'I agree') or contains(., 'Accept')]",
            )
            consent_button.click()
            logger.info("Clicked consent/accept button.")
            time.sleep(2)
        except NoSuchElementException:
            pass
        
        # Check for captcha with multiple detection methods
        captcha_detected = False
        captcha_indicators = [
            "//*[contains(text(), 'captcha') or contains(text(), 'CAPTCHA')]",
            "//iframe[contains(@src, 'recaptcha')]",
            "//div[contains(@class, 'g-recaptcha')]",
            "//*[contains(@id, 'recaptcha')]",
            "//*[contains(@class, 'captcha')]",
            "//*[contains(text(), 'verify you') or contains(text(), 'verify that')]",
        ]
        
        for indicator in captcha_indicators:
            try:
                captcha = self.driver.find_element(By.XPATH, indicator)
                if captcha and captcha.is_displayed():
                    captcha_detected = True
                    break
            except (NoSuchElementException, Exception):
                continue
        
        # Also check page source for CAPTCHA-related text
        if not captcha_detected:
            try:
                page_source = self.driver.page_source.lower()
                if 'recaptcha' in page_source or 'captcha' in page_source:
                    # Check if it's actually visible
                    try:
                        if self.driver.find_element(By.XPATH, "//iframe[contains(@src, 'recaptcha')]"):
                            captcha_detected = True
                    except:
                        pass
            except:
                pass
        
        if captcha_detected:
            logger.warning("⚠️ CAPTCHA detected! Please solve it manually in the browser...")
            logger.warning("   The scraper will wait for you to solve it.")
            input("   Press Enter in the terminal after solving the CAPTCHA...")
            time.sleep(3)  # Give it a moment after solving

        # Find and use the search box
        try:
            # Try multiple selectors for the search box
            search_box = None
            search_selectors = [
                (By.ID, "searchboxinput"),
                (By.XPATH, "//input[@id='searchboxinput']"),
                (By.XPATH, "//input[@placeholder*='Search' or @aria-label*='Search']"),
                (By.CSS_SELECTOR, "input#searchboxinput"),
            ]
            
            for by, selector in search_selectors:
                try:
                    search_box = wait_search.until(EC.presence_of_element_located((by, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not search_box:
                logger.error("Could not find Google Maps search box")
                return results

            # Clear any existing text and enter new search
            search_box.clear()
            time.sleep(0.5)
            search_query = f"{query} in {location}"
            search_box.send_keys(search_query)
            time.sleep(1)
            
            # Submit search (press Enter)
            search_box.send_keys(Keys.ENTER)
            # Random wait to appear more human-like
            time.sleep(3 + random.uniform(1, 2))  # Wait 4-5 seconds for results to load
            
        except Exception as e:
            logger.error(f"Error using search box: {e}")
            return results

        # Now wait for results to appear - with retry
        max_retries = 2
        results_loaded = False
        for attempt in range(max_retries):
            if self._load_initial_results(wait_results):
                results_loaded = True
                break
            else:
                if attempt < max_retries - 1:
                    logger.warning(f"Retry {attempt + 1}/{max_retries}: Could not load results, trying again...")
                    time.sleep(3)
                    # Try clicking search again
                    try:
                        search_box = self.driver.find_element(By.ID, "searchboxinput")
                        search_box.clear()
                        search_box.send_keys(f"{query} in {location}")
                        search_box.send_keys(Keys.ENTER)
                        time.sleep(4)
                    except:
                        pass
        
        if not results_loaded:
            logger.error(f"❌ Could not load results for '{query}' in '{location}' after {max_retries} attempts")
            logger.error("   Possible causes: CAPTCHA, rate limiting, or no results found")
            logger.error("   Trying one more time with fresh page load...")
            
            # Final attempt: completely fresh start
            try:
                self.driver.get("https://www.google.com/maps")
                time.sleep(4)
                
                # Try search box again
                search_box = self.driver.find_element(By.ID, "searchboxinput")
                search_box.clear()
                search_box.send_keys(f"{query} in {location}")
                search_box.send_keys(Keys.ENTER)
                time.sleep(5)
                
                if self._load_initial_results(wait_results):
                    logger.info("✅ Fresh page load worked! Continuing...")
                else:
                    logger.warning("⚠️  Still no results after fresh page load")
                    return results
            except Exception as e:
                logger.error(f"Final attempt failed: {e}")
                return results

        seen_ids = set()
        pages_without_new = 0
        max_pages_without_new = 15  # Increased significantly to allow deep scrolling for more leads
        consecutive_empty_scrolls = 0
        total_scrolls = 0

        logger.info(f"Starting to collect up to {max_results} results for '{query}' in '{location}'...")

        while len(results) < max_results and pages_without_new < max_pages_without_new:
            cards = self._find_result_cards()
            if not cards:
                logger.debug(f"No cards found, scrolling... (scroll {total_scrolls + 1}, empty pages: {pages_without_new + 1}/{max_pages_without_new})")
                if not self._scroll_results_panel():
                    consecutive_empty_scrolls += 1
                    if consecutive_empty_scrolls >= 5:  # Increased from 3 to 5 for more persistence
                        logger.info(f"Reached end of results after {total_scrolls} scrolls. Found {len(results)}/{max_results} results.")
                        break
                    time.sleep(2)
                    continue
                consecutive_empty_scrolls = 0
                pages_without_new += 1
                total_scrolls += 1
                time.sleep(1.5 + random.uniform(0, 1))  # Wait for new cards to load with random delay
                continue

            consecutive_empty_scrolls = 0
            new_this_page = 0

            for card in cards:
                identifier = self._card_identifier(card)
                if identifier in seen_ids:
                    continue
                seen_ids.add(identifier)

                info = self._extract_from_card(card, query, location)
                if info:
                    results.append(info)
                    new_this_page += 1
                    logger.info(
                        f"[{len(results)}/{max_results}] "
                        f"{info['name']} | {info['address']} | {info['state']} | "
                        f"{info['phone']} | {info['website']} | {info['rating']}"
                    )

                if len(results) >= max_results:
                    break

            if new_this_page == 0:
                # No new cards this page, try scrolling
                logger.debug(f"No new cards found this iteration, scrolling to load more... (scroll {total_scrolls + 1})")
                if not self._scroll_results_panel():
                    pages_without_new += 1
                    total_scrolls += 1
                    if pages_without_new >= max_pages_without_new:
                        logger.info(f"Reached max scroll attempts ({max_pages_without_new}). Found {len(results)}/{max_results} results.")
                        break
                else:
                    pages_without_new += 1
                    total_scrolls += 1
                    time.sleep(1.5 + random.uniform(0, 1))  # Wait for new content with random delay
            else:
                pages_without_new = 0  # Reset counter when we find new cards
                # Scroll to load more if we haven't reached max yet
                if len(results) < max_results:
                    self._scroll_results_panel()
                    total_scrolls += 1
                    time.sleep(1 + random.uniform(0, 0.5))

        logger.info(f"✅ Collected {len(results)}/{max_results} results for '{query}' in '{location}' (after {total_scrolls} scrolls)")
        if len(results) < max_results:
            logger.warning(f"⚠️  Only found {len(results)}/{max_results} results. Possible reasons: limited results available, rate limiting, or need more scrolling.")
        return results

    def _load_initial_results(self, wait_results: WebDriverWait) -> bool:
        """Ensure the results list is rendered and scroll a bit to load items."""
        try:
            # Wait for results container with longer timeout
            wait_results.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[role='feed'], div[aria-label*='Results']")
                )
            )
        except TimeoutException:
            # Check if we're on a "no results" page
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "no results" in page_text.lower() or "didn't match" in page_text.lower():
                    logger.warning("Google Maps shows 'No results found' for this search")
                    return False
            except:
                pass
            logger.warning("Results list did not appear in time.")
            return False

        list_container = self._get_results_container()
        if not list_container:
            logger.warning("Could not find results container")
            return False

        # Wait for initial cards to render
        time.sleep(2)
        
        # Scroll multiple times to force Google Maps to load cards
        for i in range(6):  # Increased from 4 to 6 for better initial loading
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", list_container
            )
            time.sleep(1.5 + random.uniform(0, 0.5))
            # Check if we got cards after each scroll
            cards = self._find_result_cards()
            if cards:
                logger.debug(f"Found {len(cards)} cards after scroll {i+1}")
                return True
        
        # Final check
        cards = self._find_result_cards()
        if cards:
            logger.debug(f"Found {len(cards)} cards total")
            return True
        else:
            logger.warning("No cards found after scrolling")
            return False

    def _get_results_container(self):
        selectors = [
            "div[aria-label*='Results'] div[role='feed']",
            "div[role='feed']",
            "div.section-layout.section-scrollbox",
        ]
        for selector in selectors:
            try:
                container = self.driver.find_element(By.CSS_SELECTOR, selector)
                return container
            except Exception:
                continue
        return None

    def _find_result_cards(self):
        """Find result cards with multiple fallback selectors."""
        selectors = [
            "div[role='article']",
            "div[class*='Nv2PK']",
            "div[jsaction*='mouseover:pane']",
        ]
        for selector in selectors:
            cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if cards:
                return cards
        return []

    def _extract_from_card(self, card_element, query, location):
        """
        Extract as much info as possible from a single result card
        without clicking into the place detail page.
        """
        try:
            text = card_element.text or ""
            if not text.strip():
                return None

            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            if not lines:
                return None

            # Name is almost always the first non-empty line
            name = lines[0]

            # Address heuristic: line with a number and a street keyword
            address = "N/A"
            street_keywords = ["St", "Street", "Ave", "Avenue", "Blvd", "Road", "Rd", "Dr", "Lane", "Ln"]
            for ln in lines[1:]:
                if any(kw in ln for kw in street_keywords) and re.search(r"\d", ln):
                    address = ln
                    break

            # Fallback address: first line after name that looks like it has a comma
            if address == "N/A":
                for ln in lines[1:]:
                    if "," in ln and any(ch.isalpha() for ch in ln):
                        address = ln
                        break

            state = self._get_state_from_address(address)
            if state == "N/A" and "," in location:
                state = location.split(",")[-1].strip()

            # Phone: try multiple extraction methods
            phone = "N/A"
            
            # Method 1: Look for tel: links in the card
            try:
                tel_links = card_element.find_elements(By.CSS_SELECTOR, "a[href^='tel:']")
                for tel_link in tel_links:
                    href = tel_link.get_attribute("href") or ""
                    if href.startswith("tel:"):
                        phone = href.replace("tel:", "").strip()
                        break
            except Exception:
                pass
            
            # Method 2: Look for phone buttons with data attributes
            if phone == "N/A":
                try:
                    phone_buttons = card_element.find_elements(
                        By.CSS_SELECTOR, 
                        "button[data-item-id*='phone'], button[aria-label*='Phone'], button[aria-label*='Call']"
                    )
                    for btn in phone_buttons:
                        aria_label = btn.get_attribute("aria-label") or ""
                        if "phone" in aria_label.lower() or "call" in aria_label.lower():
                            # Extract phone from aria-label
                            phone_match = re.search(r"(\+?\d[\d\-\.\s\(\)]{7,}\d)", aria_label)
                            if phone_match:
                                phone = phone_match.group(1).strip()
                                break
                        # Or get text directly
                        btn_text = btn.text.strip()
                        if btn_text and re.search(r"\d", btn_text):
                            phone_match = re.search(r"(\+?\d[\d\-\.\s\(\)]{7,}\d)", btn_text)
                            if phone_match:
                                phone = phone_match.group(1).strip()
                                break
                except Exception:
                    pass
            
            # Method 3: Regex on entire card text (multiple patterns)
            if phone == "N/A":
                phone_patterns = [
                    r"(\+?1?[\s\-\.]?\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4})",  # US format
                    r"(\+\d{1,3}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,9})",  # International
                    r"(\(?\d{3}\)?[\s\-\.]?\d{3}[\s\-\.]?\d{4})",  # Simple US
                    r"(\d{3}[\s\-\.]\d{3}[\s\-\.]\d{4})",  # Dotted/dashed
                ]
                for pattern in phone_patterns:
                    phone_match = re.search(pattern, text)
                    if phone_match:
                        phone = phone_match.group(1).strip()
                        break
            
            # Method 4: Look in all links and spans for phone-like text
            if phone == "N/A":
                try:
                    all_elements = card_element.find_elements(By.CSS_SELECTOR, "a, span, div, button")
                    for elem in all_elements:
                        elem_text = elem.text or elem.get_attribute("textContent") or ""
                        if elem_text and re.search(r"\d{3}.*\d{3}.*\d{4}", elem_text):
                            phone_match = re.search(r"(\+?\d[\d\-\.\s\(\)]{7,}\d)", elem_text)
                            if phone_match:
                                phone = phone_match.group(1).strip()
                                break
                except Exception:
                    pass
            
            phone = self._clean_phone_text(phone)

            # Rating: look for something like "4.3" followed by "★" or "stars"
            rating = "N/A"
            rating_match = re.search(r"(\d\.\d)\s*★", text)
            if rating_match:
                rating = rating_match.group(1)
            else:
                rating_match = re.search(r"Rated\s+(\d\.\d)\s+out of", text)
                if rating_match:
                    rating = rating_match.group(1)

            # Website: try multiple extraction methods
            website = "N/A"
            
            # Method 1: Look for website links with specific attributes
            try:
                website_links = card_element.find_elements(
                    By.CSS_SELECTOR,
                    "a[href^='http'], a[data-item-id='authority'], a[aria-label*='Website'], a[aria-label*='website']"
                )
                for link in website_links:
                    href = link.get_attribute("href") or ""
                    if href and (href.startswith("http://") or href.startswith("https://")):
                        # Filter out Google Maps links
                        if "google.com/maps" not in href and "maps.google.com" not in href:
                            website = href
                            break
            except Exception:
                pass
            
            # Method 2: Look for website in aria-labels
            if website == "N/A":
                try:
                    website_buttons = card_element.find_elements(
                        By.CSS_SELECTOR,
                        "button[aria-label*='Website'], button[aria-label*='website'], button[data-item-id*='authority']"
                    )
                    for btn in website_buttons:
                        aria_label = btn.get_attribute("aria-label") or ""
                        # Sometimes website URL is in aria-label
                        url_match = re.search(r"(https?://[^\s]+)", aria_label)
                        if url_match:
                            website = url_match.group(1)
                            break
                except Exception:
                    pass
            
            # Method 3: Extract from text if it looks like a URL
            if website == "N/A":
                url_match = re.search(r"(https?://[^\s\n]+)", text)
                if url_match:
                    potential_url = url_match.group(1)
                    if "google.com/maps" not in potential_url and "maps.google.com" not in potential_url:
                        website = potential_url

            return {
                "name": name,
                "address": address,
                "state": state,
                "phone": phone,
                "website": website,
                "category": query,
                "rating": rating,
            }
        except Exception as e:
            logger.warning(f"Error extracting from card: {e}")
            return None

    def _scroll_results_panel(self):
        """Scroll the results panel to load more cards. Returns True if scroll was successful."""
        container = self._get_results_container()
        if not container:
            return False
        try:
            # Get current scroll position
            current_scroll = self.driver.execute_script(
                "return arguments[0].scrollTop", container
            )
            scroll_height = self.driver.execute_script(
                "return arguments[0].scrollHeight", container
            )
            
            # Scroll down - use smooth scrolling to appear more human-like
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight", container
            )
            # Random delay to mimic human behavior
            time.sleep(1.5 + random.uniform(0, 1))  # Wait for new content to load
            
            # Check if we actually scrolled
            new_scroll = self.driver.execute_script(
                "return arguments[0].scrollTop", container
            )
            
            # If we're at the bottom and scroll didn't change, we've reached the end
            if new_scroll == current_scroll and new_scroll > 0:
                logger.debug("Reached end of results list")
                return False
            
            return True
        except Exception as e:
            logger.debug(f"Error scrolling: {e}")
            return False

    def _card_identifier(self, card_element):
        candidates = [
            card_element.get_attribute("data-result-id"),
            card_element.get_attribute("aria-label"),
            card_element.text.split("\n")[0] if card_element.text else "",
        ]
        for candidate in candidates:
            if candidate:
                return candidate.strip()
        return str(id(card_element))

    # ---------- second pass: enrich missing phones by clicking ----------

    def enrich_missing_phones(self, leads, query, location, max_clicks: int = 20):
        """
        Second pass:
        - Re-run the same search
        - For leads that are missing phone numbers OR websites, click into matching cards
          and try to pull phone/website from the detail panel using comprehensive selectors.
        """
        missing_phone = [lead for lead in leads if not lead.get("phone") or lead["phone"] == "N/A"]
        missing_website = [lead for lead in leads if not lead.get("website") or lead["website"] == "N/A"]
        missing = list(set(missing_phone + missing_website))  # Unique leads that need enrichment
        
        if not missing or max_clicks <= 0:
            return leads

        logger.info(
            f"Enriching phones/websites for {len(missing)} leads (up to {max_clicks} clicks) "
            f"for '{query}' in '{location}'"
        )

        name_to_lead = {lead.get("name"): lead for lead in missing if lead.get("name")}

        wait_results = WebDriverWait(self.driver, 20)
        wait_details = WebDriverWait(self.driver, 20)

        search_url = (
            "https://www.google.com/maps/search/"
            f"{query.replace(' ', '+')}+{location.replace(' ', '+')}"
        )
        self.driver.get(search_url)

        # Handle cookie / consent popups if they appear
        time.sleep(2 + random.uniform(0, 1))
        try:
            consent_button = self.driver.find_element(
                By.XPATH,
                "//button[contains(., 'Accept all') or contains(., 'I agree') or contains(., 'Accept')]",
            )
            consent_button.click()
            logger.info("Clicked consent/accept button (enrich pass).")
            time.sleep(2)
        except NoSuchElementException:
            pass
        
        # Check for CAPTCHA in enrichment pass too
        captcha_detected = False
        captcha_indicators = [
            "//iframe[contains(@src, 'recaptcha')]",
            "//div[contains(@class, 'g-recaptcha')]",
            "//*[contains(@id, 'recaptcha')]",
            "//*[contains(text(), 'captcha') or contains(text(), 'CAPTCHA')]",
        ]
        for indicator in captcha_indicators:
            try:
                captcha = self.driver.find_element(By.XPATH, indicator)
                if captcha and captcha.is_displayed():
                    captcha_detected = True
                    break
            except:
                continue
        
        if captcha_detected:
            logger.warning("⚠️ CAPTCHA detected in enrichment pass! Please solve it...")
            input("Press Enter after solving the CAPTCHA...")
            time.sleep(3)

        if not self._load_initial_results(wait_results):
            logger.warning("Enrich pass: could not load results list.")
            return leads

        clicks_done = 0
        pages_without_new = 0

        while clicks_done < max_clicks and pages_without_new < 4 and name_to_lead:
            cards = self._find_result_cards()
            if not cards:
                if not self._scroll_results_panel():
                    break
                pages_without_new += 1
                continue

            new_clicks_this_page = 0

            for card in cards:
                # Identify card's business name from its text
                card_text = card.text or ""
                lines = [ln.strip() for ln in card_text.split("\n") if ln.strip()]
                if not lines:
                    continue

                card_name = lines[0]
                lead = name_to_lead.get(card_name)
                if not lead:
                    continue

                # Click into detail
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                    time.sleep(0.5 + random.uniform(0, 0.5))  # Random 0.5-1 second
                    card.click()
                except Exception as e:
                    logger.debug(f"Enrich pass: could not click card '{card_name}': {e}")
                    continue

                # wait for detail header
                try:
                    wait_details.until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//h1[contains(@class,'DUwDvf') or contains(@class,'fontHeadlineLarge')]")
                        )
                    )
                    time.sleep(1)
                except TimeoutException:
                    logger.debug(f"Enrich pass: timeout waiting for details of '{card_name}'")
                    # try going back
                    try:
                        self.driver.back()
                        time.sleep(2)
                        wait_results.until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div[role='feed'], div[aria-label*='Results']")
                            )
                        )
                    except Exception:
                        pass
                    continue

                # Try to get phone from detail panel with comprehensive selectors
                phone_detail = self._wait_and_get_text(
                    [
                        (By.XPATH, "//button[contains(@aria-label,'Phone:')]", "aria-label"),
                        (By.XPATH, "//button[contains(@aria-label,'Call:')]", "aria-label"),
                        (By.XPATH, "//button[contains(@data-item-id,'phone:tel')]//div[contains(@class,'fontBodyMedium')]", None),
                        (By.XPATH, "//button[contains(@data-item-id,'phone:tel')]", None),
                        (By.XPATH, "//a[starts-with(@href,'tel:')]", "href"),
                        (By.XPATH, "//button[contains(@data-value,'Phone')]", None),
                        (By.XPATH, "//div[contains(@data-value,'Phone')]", None),
                        (By.XPATH, "//span[contains(@class,'phone')]", None),
                        (By.XPATH, "//div[contains(@class,'phone')]", None),
                        (By.CSS_SELECTOR, "button[data-item-id*='phone']", None),
                        (By.CSS_SELECTOR, "a[href^='tel:']", "href"),
                        (By.XPATH, "//*[contains(text(),'Phone') or contains(text(),'Call')]/following-sibling::*[1]", None),
                        # Additional fallbacks
                        (By.XPATH, "//button[contains(@jsaction,'phone')]", None),
                        (By.XPATH, "//div[contains(@jsaction,'phone')]", None),
                    ],
                    timeout=6,  # Reduced timeout for speed
                )
                if phone_detail.startswith("tel:"):
                    phone_detail = phone_detail.replace("tel:", "")
                if phone_detail.startswith("Phone:"):
                    phone_detail = phone_detail.split("Phone:", 1)[1].strip()
                if phone_detail.startswith("Call:"):
                    phone_detail = phone_detail.split("Call:", 1)[1].strip()
                phone_detail = self._clean_phone_text(phone_detail)

                # Try to get website from detail panel with comprehensive selectors
                website_detail = self._wait_and_get_text(
                    [
                        (By.XPATH, "//a[contains(@aria-label,'Website')]", "href"),
                        (By.XPATH, "//a[contains(@data-item-id,'authority')]", "href"),
                        (By.XPATH, "//a[contains(@href,'http') and not(contains(@href,'google.com/maps'))]", "href"),
                        (By.XPATH, "//button[contains(@aria-label,'Website')]", "aria-label"),
                        (By.XPATH, "//button[contains(@data-item-id,'authority')]", None),
                        (By.CSS_SELECTOR, "a[data-item-id='authority']", "href"),
                        (By.CSS_SELECTOR, "a[href^='http']:not([href*='google.com/maps'])", "href"),
                        (By.XPATH, "//*[contains(text(),'Website')]/following-sibling::a[1]", "href"),
                        (By.XPATH, "//*[contains(@class,'website')]//a", "href"),
                    ],
                    timeout=6,  # Reduced timeout for speed
                )
                if website_detail and "google.com/maps" in website_detail:
                    website_detail = "N/A"
                if website_detail and not (website_detail.startswith("http://") or website_detail.startswith("https://")):
                    # Might be in aria-label, try to extract URL
                    url_match = re.search(r"(https?://[^\s]+)", website_detail)
                    if url_match:
                        website_detail = url_match.group(1)
                    else:
                        website_detail = "N/A"

                # Update lead if we found phone or website
                updated = False
                if phone_detail != "N/A" and (not lead.get("phone") or lead["phone"] == "N/A"):
                    lead["phone"] = phone_detail
                    logger.info(f"Enrich pass: found phone {phone_detail} for '{card_name}'")
                    updated = True
                
                if website_detail != "N/A" and (not lead.get("website") or lead["website"] == "N/A"):
                    lead["website"] = website_detail
                    logger.info(f"Enrich pass: found website {website_detail} for '{card_name}'")
                    updated = True
                
                # Remove from pending if both phone and website are now filled
                if updated and lead.get("phone") != "N/A" and lead.get("website") != "N/A":
                    name_to_lead.pop(card_name, None)
                elif updated and (lead.get("phone") != "N/A" or lead.get("website") != "N/A"):
                    # Still keep in pending if only one was filled
                    pass

                clicks_done += 1
                new_clicks_this_page += 1

                # Go back to results (with random delay to appear human-like)
                try:
                    self.driver.back()
                    time.sleep(1 + random.uniform(0.5, 1.5))  # Random 1.5-2.5 seconds
                    wait_results.until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div[role='feed'], div[aria-label*='Results']")
                        )
                    )
                except Exception:
                    logger.debug("Enrich pass: error going back to results, stopping.")
                    return leads

                if clicks_done >= max_clicks or not name_to_lead:
                    break

            if new_clicks_this_page == 0:
                if not self._scroll_results_panel():
                    pages_without_new += 1
                    break
                pages_without_new += 1
            else:
                pages_without_new = 0

        logger.info(f"Enrich pass complete. Clicks used: {clicks_done}")
        return leads
