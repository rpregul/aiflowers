import os
import io
import base64
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from PIL import Image
import requests
import json

# Токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🔍 Анализирую через Gemini 2.5...")
        
        # Получаем фото
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Конвертируем в base64
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Подготовка запроса к Gemini 2.5 API
        headers = {
            "Content-Type": "application/json",
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": "Проанализируй фото букета. Ответь на русском: 1. Какие цветы? 2. Сколько примерно каждого вида? 3. Примерная стоимость в Москве?"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_base64
                        }
                    }
                ]
            }]
        }
        
        # ВАЖНО: Попробуйте разные версии URL
        url_versions = [
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}",
            f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generateContent?key={GEMINI_API_KEY}",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-pro:generateContent?key={GEMINI_API_KEY}",
            f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-pro:generateContent?key={GEMINI_API_KEY}",
        ]
        
        response_text = "Ошибка: не удалось подключиться к AI"
        
        for url in url_versions:
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if "candidates" in data and len(data["candidates"]) > 0:
                        response_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        break
                    else:
                        response_text = f"Ошибка ответа: {data}"
                else:
                    response_text = f"Ошибка HTTP {response.status_code}: {response.text[:100]}"
                    
            except Exception as e:
                response_text = f"Ошибка запроса: {str(e)}"
                continue
        
        # Отправляем ответ
        await update.message.reply_text(f"🌸 Анализ:\n\n{response_text}")
            
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)[:150]}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() in ['/start', 'start']:
        await update.message.reply_text("📸 Отправь фото букета для анализа через Gemini 2.5")
    else:
        await update.message.reply_text("Отправь фото букета")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.run_polling()

if __name__ == '__main__':
    main()
