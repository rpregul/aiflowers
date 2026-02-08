import os
import io
import base64
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-1.5-flash:generateContent"
    f"?key={GEMINI_API_KEY}"
)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Анализирую букет… 🌸")

    try:
        # Получаем фото
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        # Кодируем в base64
        img_base64 = base64.b64encode(photo_bytes).decode("utf-8")

        payload = {
            "contents": [{
                "parts": [
                    {
                        "text": (
                            "Проанализируй фото букета. "
                            "Ответь на русском:\n"
                            "1. Какие цветы изображены\n"
                            "2. Примерное количество каждого вида\n"
                            "3. Примерная стоимость такого букета в Москве (в рублях)\n"
                            "Ответ дай списком."
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
            GEMINI_URL,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            await update.message.reply_text(
                f"❌ Ошибка Gemini:\n{response.status_code}\n{response.text[:300]}"
            )
            return

        data = response.json()
        answer = data["candidates"][0]["content"]["parts"][0]["text"]

        await update.message.reply_text(f"🌸 Анализ:\n\n{answer}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {str(e)[:200]}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() in ("/start", "start"):
        await update.message.reply_text(
            "📸 Отправь фото букета — я проанализирую его через Gemini"
        )
    else:
        await update.message.reply_text("📷 Просто отправь фото букета")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
