import requests
from bs4 import BeautifulSoup
import re
import time
from amazon_paapi import AmazonApi
import asyncio
import aiohttp
import random
import streamlit as st

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
# TELEGRAM_CHANNEL_ID = st.secrets["TELEGRAM_CHANNEL_ID"]
AMAZON_ACCESS_KEY = st.secrets["AMAZON_ACCESS_KEY"]
AMAZON_SECRET_KEY = st.secrets["AMAZON_SECRET_KEY"]
AMAZON_ASSOC_TAG = st.secrets["AMAZON_ASSOC_TAG"]
# deals_url = "https://www.amazon.in/deals?language=en_IN&ref_=as_li_ss_tl"

class AmazonTelegramDealsBot:
    def __init__(self, telegram_bot_token, telegram_channel_id):
        # Initialize Amazon PA API with much higher throttling
        self.amazon = AmazonApi(
            AMAZON_ACCESS_KEY ,
            AMAZON_SECRET_KEY ,
            AMAZON_ASSOC_TAG,
            "IN",
            throttling=5  # Increased throttling to 5 seconds between requests
)

        # Telegram settings
        self.bot_token = telegram_bot_token
        self.channel_id = telegram_channel_id
        self.telegram_api_url = f"https://api.telegram.org/bot{telegram_bot_token}"

        # Setup session with headers to avoid blocking
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

        # Track failed requests for exponential backoff
        self.consecutive_failures = 0
        self.base_delay = 5  # Base delay in seconds

    def extract_asins_from_deals_page(self, deals_url):
        """Extract all ASINs from the Amazon deals page"""
        print(f"Scraping deals from: {deals_url}")

        try:
            response = self.session.get(deals_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            asins = set()

            # Patterns for ASINs
            asin_patterns = [
                r'/dp/([A-Z0-9]{10})',
                r'/gp/product/([A-Z0-9]{10})',
                r'data-asin="([A-Z0-9]{10})"',
                r'asin["\']?\s*[:=]\s*["\']([A-Z0-9]{10})["\']',
                r'/([A-Z0-9]{10})/'
            ]

            page_content = response.text
            for pattern in asin_patterns:
                matches = re.findall(pattern, page_content)
                for match in matches:
                    if len(match) == 10 and match.isalnum():
                        asins.add(match)

            print(f"Found {len(asins)} unique ASINs")
            return list(asins)

        except Exception as e:
            print(f"Error scraping deals page: {e}")
            return []

    def calculate_delay(self):
        """Calculate delay with exponential backoff for failed requests"""
        if self.consecutive_failures > 0:
            # Exponential backoff: base_delay * (2 ^ failures) + random jitter
            delay = self.base_delay * (2 ** min(self.consecutive_failures, 5))  # Cap at 2^5 = 32
            jitter = random.uniform(0, 2)  # Add 0-2 seconds random jitter
            total_delay = delay + jitter
            print(f"⏱️ Using exponential backoff delay: {total_delay:.1f} seconds")
            return total_delay
        return self.base_delay

    def get_product_details_single(self, asin):
        """Get detailed product information for a single ASIN with enhanced error handling"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Calculate dynamic delay based on failures
                delay = self.calculate_delay()
                print(f"⏳ Waiting {delay:.1f} seconds before API call...")
                time.sleep(delay)
                
                items = self.amazon.get_items([asin])
                
                if not items:
                    print(f"❌ No data returned for ASIN: {asin}")
                    return None

                item = items[0]
                product_details = {
                    'asin': asin,
                    'title': 'N/A',
                    'primary_image': 'N/A',
                    'current_price': 'N/A',
                    'mrp': 'N/A',
                    'discount': 'N/A',
                    'availability': 'N/A',
                    'max_order_quantity': 'N/A',
                    'affiliate_url': f"https://www.amazon.in/dp/{asin}?tag={AMAZON_ASSOC_TAG}"
                }

                # Title
                if item.item_info and item.item_info.title:
                    product_details['title'] = item.item_info.title.display_value

                # Image
                if item.images and item.images.primary:
                    product_details['primary_image'] = item.images.primary.large.url

                # Price info
                if item.offers and item.offers.listings:
                    listing = item.offers.listings[0]

                    if listing.price:
                        product_details['current_price'] = f"₹{listing.price.amount}"

                    if listing.saving_basis:
                        product_details['mrp'] = f"₹{listing.saving_basis.amount}"
                    elif hasattr(listing, 'list_price') and listing.list_price:
                        product_details['mrp'] = f"₹{listing.list_price.amount}"

                    if listing.price and listing.saving_basis:
                        discount_amount = listing.saving_basis.amount - listing.price.amount
                        discount_percentage = (discount_amount / listing.saving_basis.amount) * 100
                        product_details['discount'] = f"₹{discount_amount:.2f} ({discount_percentage:.1f}% off)"

                    if listing.availability:
                        product_details['availability'] = listing.availability.message
                        if listing.availability.max_order_quantity:
                            product_details['max_order_quantity'] = listing.availability.max_order_quantity

                # Reset failure counter on success
                self.consecutive_failures = 0

                # Only return if we have meaningful data
                if product_details['title'] != 'N/A' and product_details['current_price'] != 'N/A':
                    print(f"✅ Successfully fetched data for ASIN: {asin}")
                    return product_details
                else:
                    print(f"⚠️ Incomplete data for ASIN: {asin}")
                    return None

            except Exception as e:
                error_msg = str(e).lower()
                if "requests limit reached" in error_msg or "throttle" in error_msg or "rate limit" in error_msg:
                    self.consecutive_failures += 1
                    print(f"⚠️ Rate limit hit for ASIN {asin} (attempt {attempt + 1}/{max_retries})")
                    print(f"❌ Error: {e}")
                    
                    if attempt < max_retries - 1:
                        # Wait longer before retry
                        retry_delay = self.base_delay * (2 ** (attempt + 1)) + random.uniform(5, 15)
                        print(f"⏳ Waiting {retry_delay:.1f} seconds before retry...")
                        time.sleep(retry_delay)
                        continue
                else:
                    print(f"❌ Non-rate-limit error for ASIN {asin}: {e}")
                    break
        
        # If we get here, all retries failed
        print(f"❌ All retries failed for ASIN: {asin}")
        return None

    def format_product_message(self, product):
        """Format product details for Telegram message"""
        title = product['title']
        if len(title) > 100:
            title = title[:97] + "..."

        message = f"""🛒 **Amazon Deal Alert!**

📦 **{title}**

💰 **Price:** {product['current_price']}
🏷️ **MRP:** {product['mrp']}
🎯 **Discount:** {product['discount']}
📋 **Availability:** {product['availability']}

🔗 ({product['affiliate_url']})

#AmazonDeals #Shopping #Discount"""
        return message

    def send_telegram_message(self, message, image_url=None):
        """Send message to Telegram channel - simplified to only send product messages"""
        try:
            if image_url and image_url != 'N/A':
                url = f"{self.telegram_api_url}/sendPhoto"
                data = {
                    'chat_id': self.channel_id,
                    'photo': image_url,
                    'caption': message,
                    'parse_mode': 'Markdown'
                }
            else:
                url = f"{self.telegram_api_url}/sendMessage"
                data = {
                    'chat_id': self.channel_id,
                    'text': message,
                    'parse_mode': 'Markdown',
                    'disable_web_page_preview': False
                }

            response = requests.post(url, data=data)

            if response.status_code == 200:
                result = response.json()
                if result['ok']:
                    print("✅ Product message sent successfully to Telegram")
                    return True
                else:
                    print(f"❌ Telegram API error: {result.get('description', 'Unknown error')}")
                    return False
            else:
                print(f"❌ HTTP error: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error sending to Telegram: {e}")
            return False

    def process_all_deals_to_telegram(self, deals_url, max_products=5, delay_between_messages=3):
        """Process all deals and send ONLY product information to Telegram channel"""
        print("=" * 60)
        print("AMAZON DEALS TO TELEGRAM BOT")
        print("=" * 60)

        # Step 1: Extract ASINs
        asins = self.extract_asins_from_deals_page(deals_url)
        if not asins:
            print("No ASINs found. The page might be blocked or structure changed.")
            return

        asins = asins[:max_products]
        print(f"Processing {len(asins)} products...")

        # DO NOT send initial/status messages to Telegram - only log locally
        print(f"🚀 Starting Amazon Deals Extraction - Found {len(asins)} products to process")

        successful_sends = 0
        processed_count = 0

        # Step 2: Process ASINs one by one with enhanced throttling
        for i, asin in enumerate(asins, 1):
            print(f"\n{'='*40}")
            print(f"Processing ASIN {i}/{len(asins)}: {asin}")
            print(f"{'='*40}")
            
            # Get product details for single ASIN
            product = self.get_product_details_single(asin)
            processed_count += 1
            
            if product:
                # Format and send product message (ONLY product messages go to Telegram)
                message = self.format_product_message(product)
                if self.send_telegram_message(message, product['primary_image']):
                    successful_sends += 1
                    print(f"✅ Sent {product['asin']} to Telegram")
                else:
                    print(f"❌ Failed to send {product['asin']} to Telegram")
                
                # Add delay between Telegram messages
                print(f"⏳ Waiting {delay_between_messages} seconds before next message...")
                time.sleep(delay_between_messages)
            else:
                print(f"❌ Skipping {asin} - no valid product data")
            
            # Add a small delay between processing items
            time.sleep(1)

        # Step 3: Summary (LOCAL ONLY - not sent to Telegram)
        print("=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)
        print(f"✅ Products Successfully Sent to Telegram: {successful_sends}")
        print(f"❌ Products Failed: {processed_count - successful_sends}")
        print(f"📊 Total Processed: {processed_count}")
        print("=" * 60)

    def test_telegram_connection(self):
        """Test Telegram bot connection silently without sending message"""
        print("Testing Telegram connection...")
        
        try:
            # Just test the connection by getting bot info instead of sending a message
            url = f"{self.telegram_api_url}/getMe"
            response = requests.get(url)
            
            if response.status_code == 200:
                result = response.json()
                if result['ok']:
                    bot_info = result['result']
                    print(f"✅ Telegram connection successful! Bot: @{bot_info.get('username', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Telegram API error: {result.get('description', 'Unknown error')}")
                    return False
            else:
                print(f"❌ HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram connection failed: {e}")
            return False

def main():
    TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
    TELEGRAM_CHANNEL_ID = st.secrets["TELEGRAM_CHANNEL_ID"]
    deals_url = "https://www.amazon.in/deals?language=en_IN&ref_=as_li_ss_tl"

    bot = AmazonTelegramDealsBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID)

    if not bot.test_telegram_connection():
        st.error("❌ Please check your Telegram bot token and channel ID")
        return

    bot.process_all_deals_to_telegram(deals_url, max_products=10, delay_between_messages=6)
    st.success("✅ Deals sent successfully to Telegram!")


# Streamlit UI
st.title("Amazon Deals to Telegram Bot")

# Manual trigger
if st.button("🚀 Send Deals to Telegram"):
    main()

# Auto trigger every 1 hour (3600*1000 ms)
count = st_autorefresh(interval=3600 * 1000, limit=None, key="hourly_refresh")

# Run automatically on refresh
if count > 0:  # ensures it runs after the first refresh
    main()
