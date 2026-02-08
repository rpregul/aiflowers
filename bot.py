import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import google.generativeai as genai
import tempfile

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токены из переменных окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверяем, что токены установлены
if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не установлен!")
    raise ValueError("TELEGRAM_TOKEN не найден в переменных окружения")

if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY не установлен!")
    raise ValueError("GEMINI_API_KEY не найден в переменных окружения")

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фото с анализом через Gemini"""
    try:
        # Отправляем сообщение о начале анализа
        await update.message.reply_text("Анализирую букет… 🌸")
        
        # Получаем фото наилучшего качества
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Создаем временный файл для изображения
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
            # Скачиваем фото
            await file.download_to_drive(tmp_file.name)
            
            # Анализируем через Gemini
            await analyze_with_gemini(update, tmp_file.name)
            
        # Удаляем временный файл
        os.unlink(tmp_file.name)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке фото: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при анализе. Попробуйте отправить другое фото."
        )

async def analyze_with_gemini(update: Update, image_path: str):
    """Анализ изображения с помощью Google Gemini"""
    try:
        # Загружаем изображение
        import PIL.Image
        img = PIL.Image.open(image_path)
        
        # Выбираем модель (gemini-1.5-flash быстрая и недорогая)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Промпт для анализа букета
        prompt = """
        Ты эксперт по цветам и флористике. Проанализируй фото букета цветов.
        
        ВАЖНО: Отвечай ТОЛЬКО на русском языке.
        
        Определи и ответь по пунктам:
        1. 📋 Какие виды цветов присутствуют в букете (названия)
        2. 🔢 Приблизительное количество каждого вида цветов
        3. 💰 Ориентировочная стоимость такого букета в Москве (в рублях)
        4. 🎨 Общее описание и впечатление от букета
        
        Формат ответа:
        🌸 Анализ букета:
        
        📋 Состав:
        - [Вид цветка 1]: примерно [количество] шт.
        - [Вид цветка 2]: примерно [количество] шт.
        
        💰 Стоимость:
        Примерная цена в Москве: XXXX-XXXX рублей
        
        🎨 Впечатление:
        [Краткое описание]
        
        Отвечай кратко, но информативно.
        """
        
        # Отправляем запрос к Gemini
        response = model.generate_content([prompt, img])
        
        # Отправляем ответ пользователю
        await update.message.reply_text(response.text)
        
        logger.info("✅ Анализ успешно выполнен")
        
    except Exception as e:
        logger.error(f"Ошибка в Gemini: {e}")
        await update.message.reply_text(
            "⚠️ Не удалось проанализировать фото. "
            "Убедитесь, что на фото четко виден букет цветов."
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text.lower()
    
    if text in ['/start', 'start', 'начать']:
        welcome_text = """
        🌸 Добро пожаловать в Flower Analyzer Bot! 🌸
        
        Просто отправьте мне фото букета цветов, и я:
        • Определю виды цветов
        • Посчитаю приблизительное количество
        • Оценю стоимость букета в Москве
        
        Отправьте фото букета для начала анализа!
        """
        await update.message.reply_text(welcome_text)
    
    elif text in ['/help', 'help', 'помощь']:
        help_text = """
        🤖 Как пользоваться ботом:
        
        1. 📸 Сфотографируйте букет цветов
        2. 🖼️ Отправьте фото в этот чат
        3. ⏳ Подождите 10-20 секунд
        4. 📊 Получите детальный анализ
        
        Что я анализирую:
        • Виды цветов в букете
        • Приблизительное количество
        • Ориентировочную стоимость
        
        ❗ Убедитесь, что фото четкое и хорошо освещенное.
        """
        await update.message.reply_text(help_text)
    
    else:
        await update.message.reply_text(
            "📸 Отправьте мне фото букета цветов для анализа!\n"
            "Используйте /help для справки."
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "😔 Произошла непредвиденная ошибка. "
            "Попробуйте отправить фото еще раз или позже."
        )

def main():
    """Запуск бота"""
    logger.info("🚀 Запуск Flower Analyzer Bot...")
    
    # Создаем приложение
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Обработчики команд
    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("start", handle_text))
    app.add_handler(CommandHandler("help", handle_text))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("✅ Бот запущен и готов к работе!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
