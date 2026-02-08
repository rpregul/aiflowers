import os
import logging
import io
import base64
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from PIL import Image

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токены
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверка токенов - БЕЗ ТОКЕНОВ БОТ НЕ ЗАПУСТИТСЯ!
if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не найден!")
    raise ValueError("❌ Установите TELEGRAM_TOKEN в Railway Variables")
if not GEMINI_API_KEY:
    logger.error("❌ GEMINI_API_KEY не найден!")
    raise ValueError("❌ Установите GEMINI_API_KEY в Railway Variables")

# Настраиваем Gemini
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini настроен успешно")
except ImportError:
    logger.error("❌ Установите библиотеку: pip install google-generativeai")
    raise
except Exception as e:
    logger.error(f"❌ Ошибка Gemini: {e}")
    raise

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фото - ТОЛЬКО РЕАЛЬНЫЙ AI АНАЛИЗ"""
    try:
        # Сообщение о начале анализа
        processing_msg = await update.message.reply_text("🔍 Загружаю и анализирую фото...")
        
        # Получаем фото максимального качества
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Скачиваем фото
        photo_bytes = await file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        
        logger.info(f"📷 Получено фото: {image.size[0]}x{image.size[1]}")
        
        # Обновляем статус
        await processing_msg.edit_text("🤖 Анализирую с помощью AI...")
        
        # РЕАЛЬНЫЙ AI АНАЛИЗ
        analysis_result = await analyze_photo_with_ai(image)
        
        # Отправляем результат
        await processing_msg.delete()  # Удаляем сообщение о статусе
        await update.message.reply_text(analysis_result, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки фото: {e}")
        error_msg = (
            "❌ <b>Ошибка анализа</b>\n\n"
            "Возможные причины:\n"
            "1. 🔑 Неверный Gemini API ключ\n"
            "2. 📸 Проблема с загрузкой фото\n"
            "3. 🌐 Проблемы с сетью\n\n"
            "Проверьте:\n"
            "• API ключ в Railway Variables\n"
            "• Баланс Gemini API\n"
            "• Качество фото (свет, фокус)"
        )
        await update.message.reply_text(error_msg, parse_mode='HTML')

async def analyze_photo_with_ai(image):
    """РЕАЛЬНЫЙ AI АНАЛИЗ через Gemini"""
    try:
        # Используем модель для анализа изображений
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Оптимизируем изображение для анализа
        optimized_image = optimize_image_for_ai(image)
        
        # ДЕТАЛЬНЫЙ промпт для точного анализа
        prompt = """
        ТЫ ЭКСПЕРТ-ФЛОРИСТ. АНАЛИЗИРУЙ ФОТО БУКЕТА ЦВЕТОВ.

        ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ В СЛЕДУЮЩЕМ ФОРМАТЕ:

        🌸 <b>АНАЛИЗ БУКЕТА</b>

        <b>📋 СОСТАВ БУКЕТА:</b>
        • [Точное название цветка 1] ([цвет]): примерно X-Y шт.
        • [Точное название цветка 2] ([цвет]): примерно X-Y шт.
        • [Зелень/дополнительно]: [название]

        <b>💰 СТОИМОСТЬ В МОСКВЕ:</b>
        • Цветы: XXXX-XXXX руб
        • Упаковка: 300-500 руб
        • <b>ИТОГО: XXXX-XXXX рублей</b>

        <b>🎨 ОПИСАНИЕ:</b>
        [Краткое описание букета: стиль, для какого случая подходит]

        <b>💡 СОВЕТЫ ПО УХОДУ:</b>
        [2-3 практических совета]

        Будь максимально точным в определении видов цветов.
        Если на фото не букет, скажи "На фото не видно букета цветов".
        """
        
        # Отправляем запрос к AI
        response = model.generate_content([prompt, optimized_image])
        
        # Проверяем ответ
        if not response.text:
            return "🤖 AI не смог проанализировать фото. Попробуйте другое изображение."
        
        # Форматируем ответ
        ai_response = response.text
        
        # Добавляем заголовок если его нет
        if "🌸" not in ai_response:
            ai_response = "🌸 <b>АНАЛИЗ БУКЕТА</b>\n\n" + ai_response
        
        # Добавляем информацию о сервисе
        ai_response += "\n\n🤖 <i>Анализ выполнен с помощью Google Gemini AI</i>"
        
        return ai_response
        
    except Exception as e:
        logger.error(f"❌ Ошибка AI анализа: {e}")
        
        # Конкретные ошибки AI
        error_messages = {
            "API key not valid": "❌ Неверный Gemini API ключ",
            "quota": "❌ Превышен лимит запросов",
            "rate limit": "❌ Слишком много запросов",
            "model": "❌ Ошибка модели AI",
        }
        
        for key, message in error_messages.items():
            if key in str(e):
                return f"{message}\n\nПроверьте настройки API в Railway."
        
        return "❌ Ошибка AI сервиса. Попробуйте позже."

def optimize_image_for_ai(image):
    """Оптимизирует изображение для лучшего анализа AI"""
    try:
        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Увеличиваем размер если слишком маленький
        min_size = 512
        if max(image.size) < min_size:
            scale = min_size / max(image.size)
            new_size = (int(image.size[0] * scale), int(image.size[1] * scale))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image
    except:
        return image

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    
    if text.lower() in ['/start', '/help', 'start', 'help']:
        help_text = """
<b>🌸 FLOWER ANALYZER BOT 🌸</b>

🤖 <b>НАСТОЯЩИЙ AI-АНАЛИЗ ЦВЕТОВ</b>

<b>📸 КАК РАБОТАЕТ:</b>
1. Вы отправляете фото букета
2. AI анализирует изображение
3. Вы получаете детальный анализ

<b>📊 ЧТО ОПРЕДЕЛЯЕТ AI:</b>
• ✅ Виды цветов в букете
• ✅ Приблизительное количество
• ✅ Стоимость в Москве
• ✅ Рекомендации по уходу

<b>🔧 ДЛЯ ЛУЧШЕГО АНАЛИЗА:</b>
• 📷 Хорошее освещение
• 🔍 Четкий фокус на цветах
• 🎯 Крупный план букета
• ⚪ Простой фон

<b>⚡ ОТПРАВЬТЕ ФОТО БУКЕТА ПРЯМО СЕЙЧАС!</b>

<i>Используется Google Gemini AI для анализа изображений</i>
        """
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    elif text.lower() in ['/status', 'status', 'статус']:
        # Проверяем статус API
        try:
            import google.generativeai as genai
            models = genai.list_models()
            model_count = len(list(models))
            status_msg = f"✅ <b>СИСТЕМА РАБОТАЕТ</b>\n\n• Gemini API: Активен\n• Доступно моделей: {model_count}\n• Бот: В сети"
        except Exception as e:
            status_msg = f"❌ <b>ПРОБЛЕМА С API</b>\n\nОшибка: {str(e)[:100]}"
        
        await update.message.reply_text(status_msg, parse_mode='HTML')
    
    else:
        await update.message.reply_text(
            "📸 <b>Отправьте фото букета для анализа!</b>\n\n"
            "AI определит:\n"
            "• Какие цветы в букете\n"
            "• Сколько их\n"
            "• Сколько стоит букет\n\n"
            "Используйте /help для справки",
            parse_mode='HTML'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    # Отправляем пользователю понятное сообщение
    try:
        if update and update.message:
            await update.message.reply_text(
                "⚠️ <b>Техническая ошибка</b>\n\n"
                "Попробуйте:\n"
                "1. Отправить фото еще раз\n"
                "2. Проверить соединение\n"
                "3. Подождать 1-2 минуты\n\n"
                "<i>Если ошибка повторяется, проверьте настройки API</i>",
                parse_mode='HTML'
            )
    except:
        pass

def main():
    """ЗАПУСК БОТА"""
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК FLOWER ANALYZER BOT")
    logger.info("🤖 РЕЖИМ: ТОЛЬКО РЕАЛЬНЫЙ AI АНАЛИЗ")
    logger.info(f"📱 Telegram Token: {'✅' if TELEGRAM_TOKEN else '❌'}")
    logger.info(f"🔑 Gemini API Key: {'✅' if GEMINI_API_KEY else '❌'}")
    logger.info("=" * 60)
    
    if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
        logger.error("❌ ОШИБКА: Не все токены установлены!")
        logger.error("❌ Добавьте в Railway Variables:")
        logger.error("❌ TELEGRAM_TOKEN и GEMINI_API_KEY")
        raise ValueError("Токены не установлены")
    
    # Создаем приложение
    app = ApplicationBuilder() \
        .token(TELEGRAM_TOKEN) \
        .pool_timeout(30) \
        .read_timeout(30) \
        .build()
    
    # Добавляем обработчики
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("✅ Бот запущен! Ожидаю фото для анализа...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()
