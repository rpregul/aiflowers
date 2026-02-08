import os
import io
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from PIL import Image
import google.generativeai as genai

# Токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🔍 Анализирую...")
        
        # Получаем фото
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Анализ через Gemini
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        prompt = """
        Проанализируй фото букета. Ответь на русском:
        1. Какие цветы? (названия)
        2. Сколько примерно каждого вида?
        3. Примерная стоимость в Москве?
        """
        
        response = model.generate_content([prompt, image])
        
        # Отправляем ответ
        if response.text:
            await update.message.reply_text(f"🌸 Анализ:\n\n{response.text}")
        else:
            await update.message.reply_text("Не удалось проанализировать фото")
            
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)[:100]}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() in ['/start', 'start']:
        await update.message.reply_text("📸 Отправь фото букета для анализа")
    else:
        await update.message.reply_text("Отправь фото букета")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.run_polling()

if __name__ == '__main__':
    main()
