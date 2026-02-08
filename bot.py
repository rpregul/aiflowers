import os
import logging
import io
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from PIL import Image

# Новая библиотека Google Gemini
try:
    import google.genai as genai
    GEMINI_NEW = True
except ImportError:
    import google.generativeai as genai
    GEMINI_NEW = False

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
    if GEMINI_NEW:
        # Новая версия API
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✅ Используется НОВАЯ библиотека google.genai")
    else:
        # Старая версия API
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("✅ Используется СТАРАЯ библиотека google.generativeai")
except Exception as e:
    logger.error(f"❌ Ошибка настройки Gemini: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фото"""
    try:
        await update.message.reply_text("📸 Анализирую фото...")
        
        # Получаем фото
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Скачиваем фото
        photo_bytes = await file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        
        logger.info(f"📷 Размер фото: {image.size}")
        
        # Анализируем
        if GEMINI_NEW:
            response = await analyze_with_new_gemini(image)
        else:
            response = await analyze_with_old_gemini(image)
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки: {e}")
        await update.message.reply_text("❌ Ошибка. Используется демо-режим.")

async def analyze_with_new_gemini(image):
    """Анализ через НОВУЮ библиотеку google.genai"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Конвертируем изображение в base64
        import base64
        from io import BytesIO
        
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        prompt = """
        Ты эксперт-флорист. Проанализируй фото букета цветов.
        Ответь на русском:
        1. Какие цветы видишь?
        2. Примерное количество каждого вида?
        3. Примерная стоимость в Москве?
        
        Кратко и с эмодзи.
        """
        
        # Отправляем запрос
        result = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=[prompt, genai.types.Part.from_bytes(
                data=buffered.getvalue(),
                mime_type="image/jpeg"
            )]
        )
        
        return f"🌸 **Анализ букета:**\n\n{result.text}"
        
    except Exception as e:
        logger.error(f"❌ Ошибка новой Gemini: {e}")
        return await get_demo_response()

async def analyze_with_old_gemini(image):
    """Анализ через СТАРУЮ библиотеку google.generativeai"""
    try:
        # Пробуем разные модели
        models_to_try = [
            'gemini-1.0-pro',
            'models/gemini-1.0-pro',
            'gemini-pro',
            'gemini-1.5-flash'
        ]
        
        for model_name in models_to_try:
            try:
                logger.info(f"Пробую модель: {model_name}")
                model = genai.GenerativeModel(model_name)
                
                prompt = "Что на этом фото? Если это цветы, опиши кратко."
                
                response = model.generate_content([prompt, image])
                
                if response.text:
                    return f"📊 **Анализ:**\n\n{response.text}"
                    
            except Exception as e:
                logger.info(f"Модель {model_name} не сработала: {e}")
                continue
        
        # Если ни одна модель не сработала
        return await get_demo_response()
        
    except Exception as e:
        logger.error(f"❌ Ошибка старой Gemini: {e}")
        return await get_demo_response()

async def get_demo_response():
    """Демо-ответ для тестирования"""
    import random
    
    demo_responses = [
        """🌸 **Демо-анализ букета:**
        
        📋 **Состав:**
        - Красные розы: 7-9 шт.
        - Белые хризантемы: 5-7 шт.
        
        💰 **Стоимость в Москве:**
        2500-3500 рублей
        
        💡 **Впечатление:**
        Классический романтический букет""",
        
        """🌷 **Демо-анализ букета:**
        
        📋 **Состав:**
        - Тюльпаны разных цветов: 12-15 шт.
        - Зелень
        
        💰 **Стоимость в Москве:**
        1800-2500 рублей
        
        💡 **Впечатление:**
        Свежий весенний букет""",
        
        """💐 **Демо-анализ букета:**
        
        📋 **Состав:**
        - Пионы: 3-5 шт.
        - Розы: 5-7 шт.
        - Зелень
        
        💰 **Стоимость в Москве:**
        3500-4500 рублей
        
        💡 **Впечатление:**
        Пышный праздничный букет"""
    ]
    
    demo = random.choice(demo_responses)
    demo += "\n\n⚠️ *Это демо-режим. Настройте Gemini API для реального анализа.*"
    return demo

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текста"""
    text = update.message.text.lower()
    
    if text in ['/start', 'start', '/help', 'help']:
        status = "✅ Активен" if GEMINI_API_KEY else "❌ Не настроен"
        lib_version = "НОВАЯ (google.genai)" if GEMINI_NEW else "старая (google.generativeai)"
        
        message = f"""
🌸 **Flower Analyzer Bot** 🌸

📊 **Статус AI:** {status}
🔧 **Библиотека:** {lib_version}

📸 **Как работает:**
1. Отправьте фото букета
2. AI анализирует изображение
3. Получаете детальный анализ

🤖 **Что определяю:**
• Виды цветов в букете
• Примерное количество
• Стоимость в Москве

⚠️ *Сейчас в демо-режиме*
*Настройте Gemini API для реального AI*

📸 **Отправьте фото букета!**
        """
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("📸 Отправьте фото букета для анализа!")

def main():
    """Запуск бота"""
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК FLOWER ANALYZER BOT")
    logger.info(f"📱 Telegram: {'✅' if TELEGRAM_TOKEN else '❌'}")
    logger.info(f"🤖 Gemini: {'✅' if GEMINI_API_KEY else '❌'}")
    logger.info(f"📚 Библиотека: {'НОВАЯ google.genai' if GEMINI_NEW else 'СТАРАЯ google.generativeai'}")
    logger.info("=" * 50)
    
    # Создаем приложение
    app = ApplicationBuilder() \
        .token(TELEGRAM_TOKEN) \
        .pool_timeout(30) \
        .read_timeout(30) \
        .write_timeout(30) \
        .build()
    
    # Добавляем обработчики
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    
    # Запускаем с очисткой старых сообщений
    logger.info("✅ Бот запущен в демо-режиме!")
    app.run_polling(
        poll_interval=1.0,
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        close_loop=False
    )

if __name__ == '__main__':
    main()
