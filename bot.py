import os
import re
import logging
import pytz
import httpx
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
YOUR_TAG = os.getenv("YOUR_TAG")
RENDER_EXTERNAL_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
PORT = int(os.environ.get("PORT", 5000))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Unshorten Amazon Link ===
def unshorten_amazon_link(url: str) -> str:
    try:
        with httpx.Client(follow_redirects=True, timeout=10) as client:
            response = client.head(url, headers={"User-Agent": "Mozilla/5.0"})
            return str(response.url)
    except Exception as e:
        logger.error(f"Failed to unshorten {url}: {e}")
        return url

# === Convert Link ===
def replace_affiliate_tag(link: str) -> str:
    if link.startswith("https://amzn.to/"):
        link = unshorten_amazon_link(link)

    if not link.startswith("https://www.amazon.in/"):
        return link

    base_link, sep, query = link.partition('?')
    params = dict(re.findall(r'([^=&]+)=([^&]*)', query))
    params['smid'] = ''
    params['tag'] = YOUR_TAG

    query_str = '&'.join([f"{k}={v}" for k, v in params.items()])
    return f"{base_link}?{query_str}"

def process_text(text: str) -> str:
    url_pattern = r"(https://(?:www\.amazon\.in|amzn\.to)/[^\s]+)"
    return re.sub(url_pattern, lambda m: replace_affiliate_tag(m.group()), text)

# === Handler ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    try:
        modified_text = process_text(message.text or "")
        modified_caption = process_text(message.caption or "")

        if message.photo:
            await context.bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=message.photo[-1].file_id,
                caption=modified_caption,
                parse_mode='HTML'
            )
        elif message.video:
            await context.bot.send_video(
                chat_id=CHANNEL_USERNAME,
                video=message.video.file_id,
                caption=modified_caption,
                parse_mode='HTML'
            )
        elif message.text:
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=modified_text,
                parse_mode='HTML'
            )
    except Exception as e:
        logger.error(f"Error while processing message: {e}")

# === Main ===
async def main():
    logger.info("Starting bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://{RENDER_EXTERNAL_HOSTNAME}/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    import nest_asyncio
    import asyncio

    nest_asyncio.apply()  # ✅ Fix for environments where loop is already running

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
