import re
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

AFFILIATE_TAG = "hp0369-21"
CHANNEL_ID = "@easyshopping0369"  # <-- Replace with your actual channel username or ID

# Regex to match both normal and short amazon links
AMAZON_REGEX = r"(https?://(?:www\.)?(?:amazon\.[a-z\.]+|amzn\.to)/[\w/\-?=%.]+)"

def expand_amzn_shortlink(url: str) -> str:
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.url
    except Exception as e:
        print(f"[!] Error expanding {url}: {e}")
        return url  # fallback to original

def convert_to_affiliate(url: str) -> str:
    if "amzn.to" in url:
        url = expand_amzn_shortlink(url)

    if "tag=" in url:
        return re.sub(r'tag=[\w\-]+', f'tag={AFFILIATE_TAG}', url)
    elif "?" in url:
        return f"{url}&tag={AFFILIATE_TAG}"
    else:
        return f"{url}?tag={AFFILIATE_TAG}"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    original_text = update.message.text
    matches = re.findall(AMAZON_REGEX, original_text)

    if matches:
        updated_text = original_text
        for url in matches:
            new_url = convert_to_affiliate(url)
            updated_text = updated_text.replace(url, new_url)

        # ✅ Send to your channel instead of replying to user
        await context.bot.send_message(chat_id=CHANNEL_ID, text=updated_text)

if __name__ == "__main__":
    app = ApplicationBuilder().token("7983966637:AAG0jFLRFCNeVbaTw_zrZaUjzwFNCFW6Kas").build()

    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🤖 Bot started...")
    app.run_polling(close_loop=True)
