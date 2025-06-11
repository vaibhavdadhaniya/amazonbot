import os
import re
import logging
import pytz
import httpx
from dotenv import load_dotenv 
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()


# ==== CONFIGURATION ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
YOUR_TAG = os.getenv("YOUR_TAG")

# ==== LOGGING SETUP ====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==== UNSHORTEN AMAZON SHORTLINK ====
def unshorten_amazon_link(url: str) -> str:
    try:
        with httpx.Client(follow_redirects=True, timeout=10) as client:
            response = client.head(url, headers={"User-Agent": "Mozilla/5.0"})
            final_url = str(response.url)
            logger.info(f"Unshortened {url} -> {final_url}")
            return final_url
    except Exception as e:
        logger.error(f"Failed to unshorten {url}: {e}")
        return url

# ==== AFFILIATE LINK CONVERSION ====
def replace_affiliate_tag(link: str) -> str:
    logger.debug(f"Original link: {link}")

    if link.startswith("https://amzn.to/"):
        link = unshorten_amazon_link(link)

    if not link.startswith("https://www.amazon.in/"):
        logger.debug("Not an Amazon.in link. Skipping.")
        return link

    base_link, sep, query = link.partition('?')
    params = dict(re.findall(r'([^=&]+)=([^&]*)', query))

    params['smid'] = ''
    params['tag'] = YOUR_TAG

    query_str = '&'.join([f"{k}={v}" for k, v in params.items()])
    new_link = f"{base_link}?{query_str}"

    logger.info(f"Converted link: {new_link}")
    return new_link

def process_text(text: str) -> str:
    logger.debug(f"Processing text: {text}")
    url_pattern = r"(https://(?:www\.amazon\.in|amzn\.to)/[^\s]+)"
    modified_text = re.sub(url_pattern, lambda m: replace_affiliate_tag(m.group()), text)
    logger.debug(f"Modified text: {modified_text}")
    return modified_text

# ==== MESSAGE HANDLER ====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        logger.warning("Received update without message.")
        return

    logger.info(f"Received message from @{message.from_user.username or message.from_user.id}")

    try:
        modified_text = process_text(message.text or "")
        modified_caption = process_text(message.caption or "")

        if message.photo:
            logger.info("Forwarding photo message with modified caption.")
            await context.bot.send_photo(
                chat_id=CHANNEL_USERNAME,
                photo=message.photo[-1].file_id,
                caption=modified_caption,
                parse_mode='HTML'
            )
        elif message.video:
            logger.info("Forwarding video message with modified caption.")
            await context.bot.send_video(
                chat_id=CHANNEL_USERNAME,
                video=message.video.file_id,
                caption=modified_caption,
                parse_mode='HTML'
            )
        elif message.text:
            logger.info("Forwarding text message with modified link.")
            await context.bot.send_message(
                chat_id=CHANNEL_USERNAME,
                text=modified_text,
                parse_mode='HTML'
            )
        else:
            logger.info("Message has no text, photo, or video. Ignoring.")
    except Exception as e:
        logger.error(f"Error while processing message: {e}")

# ==== MAIN ENTRY POINT ====
if __name__ == '__main__':
    logger.info("Starting bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    logger.info("Bot is running with webhook...")

    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        webhook_url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{BOT_TOKEN}"
    )
