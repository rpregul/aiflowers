import os
import io
import base64
import requests
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, CallbackQueryHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "blackforest/flux.2-pro"  # бесплатная multimodal модель

# Состояние для пользователя
user_bouquet_state = {}

# --- Функция для анализа фото ---
async def analyze_bouquet(photo_bytes: bytes):
    image = Image.open(io.BytesIO(photo_bytes))
    image.thumbnail((1024, 1024))  # уменьшение для стабильности
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
                            "Используй жирный шрифт для названий цветов, без звездочек."
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
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
    response.raise_for_status()
    data = response.json()
    text = data["choices"][0]["message"]["content"]
    return text

# --- Генерация изображения по составу ---
async def generate_bouquet_image(bouquet_text: str):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Сделай рисунок букета по этому списку цветов:\n{bouquet_text}"
                    }
                ]
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
    response.raise_for_status()
    data = response.json()
    # Flux может возвращать base64 картинку или ссылку — здесь упрощенно берем текст
    return data["choices"][0]["message"]["content"]

# --- Обработка фото ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🔍 Анализирую букет…")
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        text = await analyze_bouquet(photo_bytes)

        user_bouquet_state[update.message.from_user.id] = text  # сохраняем состав

        # Кнопки для пользователя
        keyboard = [
            [InlineKeyboardButton("💐 Сделать меньше", callback_data="smaller")],
            [InlineKeyboardButton("💐 Сделать больше/пышнее", callback_data="bigger")],
            [InlineKeyboardButton("🎨 Получить рисунок", callback_data="draw")],
            [InlineKeyboardButton("🛒 Оформить заказ", callback_data="order")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(f"🌸 Анализ:\n\n{text}", reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

# --- Обработка нажатий кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current_bouquet = user_bouquet_state.get(user_id, "")

    if query.data in ["smaller", "bigger"]:
        instruction = "уменьши букет, сохрани его концепцию" if query.data == "smaller" else "сделай букет больше и пышнее, сохрани концепцию"
        prompt = f"Пересоставь этот букет, {instruction}:\n{current_bouquet}"
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        }
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=90)
        data = response.json()
        new_bouquet = data["choices"][0]["message"]["content"]
        user_bouquet_state[user_id] = new_bouquet

        keyboard = [
            [InlineKeyboardButton("🎨 Получить рисунок", callback_data="draw")],
            [InlineKeyboardButton("🛒 Оформить заказ", callback_data="order")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(f"🌸 Обновленный состав:\n\n{new_bouquet}", reply_markup=reply_markup)

    elif query.data == "draw":
        await query.edit_message_text("🎨 Генерирую рисунок букета…")
        image_result = await generate_bouquet_image(current_bouquet)
        # Здесь упрощенно отправляем текст с ссылкой/описанием картинки
        # Для полноценного изображения нужно адаптировать API Flux 2 Pro под base64 картинки
        await query.message.reply_text(f"🖼 Вот пример букета:\n{image_result}")

        keyboard = [[InlineKeyboardButton("🛒 Отправить флористу и внести предоплату", callback_data="order")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Что делать дальше?", reply_markup=reply_markup)

    elif query.data == "order":
        await query.edit_message_text("✅ Заказ оформлен! Флорист получит состав букета. Для внесения предоплаты следуйте инструкциям.")

# --- Обработка текста ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Отправь фото букета")

# --- Запуск ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
