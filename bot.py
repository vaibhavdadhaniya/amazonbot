import os
import re
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

# ✅ Updated Amazon URL matcher (supports long search/product URLs)
AMAZON_REGEX = r"https?://(?:www\.)?(?:amazon\.[a-z.]+|amzn\.to)[^\s]*"

# ✅ Expand amzn.to shortlinks
def expand_amzn_shortlink(url: str) -> str:
    try:
        response = requests.head(url.strip('/'), allow_redirects=True, timeout=5)
        return response.url
    except Exception as e:
        print(f"[!] Error expanding {url}: {e}")
        return url

# ✅ Clean and add/update affiliate tag
def convert_to_affiliate(url: str) -> str:
    if "amzn.to" in url:
        print(f"[🔁] Expanding shortlink: {url}")
        url = expand_amzn_shortlink(url)
        print(f"[✅] Expanded to: {url}")

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    query["tag"] = AFFILIATE_TAG  # Add or replace tag

    new_query = urlencode(query)
    new_url = urlunparse(parsed._replace(query=new_query))

    print(f"[✅] Final URL: {new_url}")
    return new_url

# ✅ Main handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.edited_message

    if not message:
        return

    # Use text or caption (for media messages)
    content = message.text or message.caption
    if not content:
        return

    print(f"[📩] Received message: {content}")

    # Detect Amazon links
    links = re.findall(AMAZON_REGEX, content)
    print(f"[🔎] Found {len(links)} Amazon link(s): {links}")

    if not links:
        return

    # Convert and replace links
    updated_content = content
    for link in links:
        new_link = convert_to_affiliate(link)
        updated_content = updated_content.replace(link, new_link)

    # ✅ Send to your Telegram channel
    print(f"[📤] Sending converted message to channel: {CHANNEL_ID}")
    await context.bot.send_message(chat_id=CHANNEL_ID, text=updated_content)

# ✅ App Entry
if __name__ == "__main__":
    if not BOT_TOKEN or not CHANNEL_ID or not AFFILIATE_TAG:
        print("❌ Missing env variables.")
        exit()

    print(f"Loaded ENV: BOT_TOKEN={'Yes' if BOT_TOKEN else 'No'}, CHANNEL_ID={CHANNEL_ID}, AFFILIATE_TAG={AFFILIATE_TAG}")
    print("🤖 Bot started... Listening for messages.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))  # ✅ Handle ALL message types
    app.run_polling()
