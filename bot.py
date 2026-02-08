import os
import io
import base64
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from PIL import Image
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1/models/"
    "gemini-1.5-flash:generateContent"
)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🔍 Анализирую букет…")

        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        image = Image.open(io.BytesIO(photo_bytes))
        buf = io.BytesIO()
        image.save(buf, format="JPEG")

        img_base64 = base64.b64encode(buf.getvalue()).decode()

        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": (
                            "Проанализируй фото букета. "
                            "Ответь на русском:\n"
                            "1. Какие цветы\n"
                            "2. Сколько примерно каждого\n"
                            "3. Примерная стоимость в Москве"
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_base64
                        }
                    }
                ]
            }]
        }

        response = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            await update.message.reply_text(
                f"❌ Ошибка Gemini:\n{response.status_code}\n{response.text}"
            )
            return

        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]

        await update.message.reply_text(f"🌸 Анализ:\n\n{text}")

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Отправь фото букета")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(MessageHandler(filters.TEXT, handle_text)))
    app.run_polling()

if __name__ == "__main__":
    main()
