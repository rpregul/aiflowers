import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import google.generativeai as genai
import io

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверка токенов
if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не установлен!")
    raise ValueError("TELEGRAM_TOKEN не найден")

if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY не установлен!")
    raise ValueError("GEMINI_API_KEY не найден")

# Настройка Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini настроен успешно")
except Exception as e:
    logger.error(f"❌ Ошибка настройки Gemini: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фото"""
    try:
        await update.message.reply_text("📸 Получил фото, анализирую через AI...")
        
        # Получаем фото
        photo = update.message.photo[-1]  # Самое качественное
        file = await context.bot.get_file(photo.file_id)
        
        # Скачиваем фото в память
        photo_bytes = await file.download_as_bytearray()
        
        # Конвертируем в PIL Image
        from PIL import Image
        image = Image.open(io.BytesIO(photo_bytes))
        
        # Проверяем размер
        logger.info(f"Размер изображения: {image.size}")
        
        # Анализируем
        response = await analyze_photo_with_gemini(image)
        
        # Отправляем результат
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_photo: {e}")
        await update.message.reply_text(
            f"❌ Ошибка анализа: {str(e)[:100]}"
        )

async def analyze_photo_with_gemini(image):
    """Анализ фото через Gemini"""
    try:
        # ИСПРАВЛЕНО: Используем правильное имя модели
        # Доступные модели: gemini-1.0-pro, gemini-1.5-pro, gemini-1.5-flash-latest
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Простой промпт
        prompt = """
        Посмотри на фото. Это букет цветов?
        Если да, то:
        1. Какие цветы ты видишь? (названия на русском)
        2. Сколько примерно каждого вида?
        3. Сколько может стоить такой букет в Москве?
        
        Ответь на русском языке кратко и понятно.
        """
        
        # Отправляем запрос
        response = model.generate_content([prompt, image])
        
        # Проверяем ответ
        if response.text:
            return f"🌸 Анализ букета:\n\n{response.text}"
        else:
            return "🤔 AI не смог определить цветы на фото. Попробуйте другое изображение."
            
    except Exception as e:
        logger.error(f"❌ Ошибка Gemini: {e}")
        return f"⚠️ Ошибка AI. Попробуйте другое фото."

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текста"""
    text = update.message.text
    
    if text in ['/start', '/help', 'start', 'help']:
        message = """
        🌸 **Flower Analyzer Bot** 🌸

        Просто отправьте мне фото букета цветов!

        Я проанализирую его с помощью AI и скажу:
        • Какие цветы в букете
        • Примерное количество
        • Ориентировочную стоимость в Москве

        📸 Отправьте фото прямо сейчас!
        """
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("📸 Отправьте фото букета для анализа!")

def main():
    """Запуск бота"""
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК БОТА...")
    logger.info(f"Telegram Token: {'УСТАНОВЛЕН' if TELEGRAM_TOKEN else 'ОТСУТСТВУЕТ'}")
    logger.info(f"Gemini API Key: {'УСТАНОВЛЕН' if GEMINI_API_KEY else 'ОТСУТСТВУЕТ'}")
    logger.info("=" * 50)
    
    # Создаем приложение с более стабильными настройками
    app = ApplicationBuilder() \
        .token(TELEGRAM_TOKEN) \
        .connection_pool_size(8) \
        .pool_timeout(30) \
        .build()
    
    # Добавляем обработчики
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    
    # Запускаем с обработкой ошибок
    logger.info("✅ Бот запущен! Ожидаю сообщений...")
    
    try:
        app.run_polling(
            poll_interval=0.5,
            timeout=30,
            drop_pending_updates=True  # Важно: игнорируем старые сообщения
        )
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == '__main__':
    main()
