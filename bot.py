import os
import io
import base64
import requests
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "black-forest-labs/flux.2-flex"

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
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Проанализируй фото букета. Ответь на русском:\n"
                                "1. Какие цветы\n"
                                "2. Сколько примерно каждого вида\n"
                                "3. Примерная стоимость букета в Москве"
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://railway.app",
            "X-Title": "Flower Telegram Bot"
        }

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            await update.message.reply_text(
                f"❌ Ошибка AI:\n{response.status_code}\n{response.text}"
            )
            return

        data = response.json()
        text = data["choices"][0]["message"]["content"]

        await update.message.reply_text(f"🌸 Анализ:\n\n{text}")

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Отправь фото букета")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
