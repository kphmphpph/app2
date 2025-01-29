import re
import time
import asyncio
from telethon import TelegramClient
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Telegram Configuration
api_id = '23683168'  # Your API ID
api_hash = 'fdd5eb6e3c560ad8b7fbf31543ff66e2'  # Your API Hash
search_keywords = ["Loot & Tricks", "The Deals Master"]  # Channels to monitor
target_channel_username = "@dealsmaster998"  # Channel username to send processed messages to

# Selenium WebDriver setup
def get_affiliate_link_from_url(url, driver):
    """Extract affiliate link for a single Amazon URL."""
    try:
        print(f"Processing URL: {url}")
        driver.get(url)

        # Click the "Text" button to access the short link
        text_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[@title="Text"]'))
        )
        text_button.click()

        # Wait for the affiliate link textarea to load
        affiliate_textarea = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//textarea[@id="amzn-ss-text-shortlink-textarea"]'))
        )
        affiliate_link = affiliate_textarea.get_attribute('value')
        print(f"Extracted affiliate link: {affiliate_link}")
        return affiliate_link
    except Exception as e:
        print(f"Error extracting affiliate link: {e}")
        return url  # Return the original URL if extraction fails

# Process messages to extract and replace Amazon links
def process_message_with_affiliate_links(message):
    """Find and replace Amazon links with affiliate links."""
    urls = re.findall(r'https?://(?:www\.)?amazon\.(?:[a-z]{2,3})(?:\.[a-z]{2})?/dp/[A-Z0-9]+', message)

    if not urls:
        print("No Amazon links found in the message.")
        return message

    # Connect to a running Chrome instance
    options = webdriver.ChromeOptions()
    options.debugger_address = "localhost:9222"  # Ensure Chrome is started with remote debugging
    driver = webdriver.Chrome(options=options)

    for url in urls:
        affiliate_link = get_affiliate_link_from_url(url, driver)
        message = message.replace(url, affiliate_link)

    driver.quit()
    return message

# Function to send a message to a Telegram channel
async def send_message(client, channel_username, message):
    """Send a processed message to the specified Telegram channel by username."""
    try:
        # Find the channel by its username
        channel = await client.get_entity(channel_username)
        await client.send_message(channel, message)
        print(f"Message sent to {channel_username}: {message}")
    except Exception as e:
        # Handle permission issues gracefully
        print(f"Failed to send message: {e}")

# Fetch and process new messages from channels
async def fetch_and_process_messages():
    """Fetch and process messages from specified Telegram channels."""
    session_name = 'user_session'  # Name of the session file (for user login)
    client = TelegramClient(session_name, api_id, api_hash)

    # Start the client and authenticate
    await client.start()
    print("Telegram client started successfully.")

    try:
        # Get dialogs and find the target channels by keywords
        dialogs = await client.get_dialogs()
        target_channels = {
            dialog.entity.id: dialog.entity for dialog in dialogs if any(keyword.lower() in dialog.name.lower() for keyword in search_keywords)
        }

        if not target_channels:
            print(f"No channels found matching keywords: {search_keywords}")
            return

        # Track the latest processed message ID for each channel
        last_processed_message_ids = {channel_id: None for channel_id in target_channels}

        while True:
            for channel_id, channel in target_channels.items():
                print(f"Checking messages in channel: {channel.name if hasattr(channel, 'name') else 'Unknown'}")
                messages = await client.get_messages(channel, limit=5)

                # Process only new messages
                new_messages = [
                    message for message in messages
                    if last_processed_message_ids[channel_id] is None or message.id > last_processed_message_ids[channel_id]
                ]

                for message in reversed(new_messages):  # Process messages in chronological order
                    if message.text:
                        print(f"Processing message: {message.text}")
                        updated_message = process_message_with_affiliate_links(message.text)
                        await send_message(client, target_channel_username, updated_message)
                    last_processed_message_ids[channel_id] = message.id

            await asyncio.sleep(30)  # Wait 30 seconds before the next check

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.disconnect()

# Main entry point
if __name__ == "__main__":
    # Start Chrome in debug mode before running this script
    # Example: chrome.exe --remote-debugging-port=9222 --user-data-dir="C:/ChromeDevSession"
    asyncio.run(fetch_and_process_messages())
