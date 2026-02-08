import os
import io
import base64
import requests
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, CallbackQueryHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Модели
ANALYSIS_MODEL = "google/gemma-3-12b-it:free"
DRAW_MODEL = "blackforest/flux.2-pro"

# Эндпоинты
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
IMAGE_URL = "https://openrouter.ai/api/v1/images/generations"

# Состояние пользователя
user_bouquet_state = {}

# --- Анализ фото ---
async def analyze_bouquet(photo_bytes: bytes):
    image = Image.open(io.BytesIO(photo_bytes))
    image.thumbnail((1024, 1024))
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    img_base64 = base64.b64encode(buf.getvalue()).decode()

    prompt = (
        "📸 Проанализируй фото букета и дай коротко:\n"
        "🌸 Какие цветы и количество (в одном пункте, жирным, без звездочек)\n"
        "💰 Средняя стоимость букета в рублях, конкретно и коротко\n"
        "Используй эмодзи для удобного чтения."
    )

    payload = {
        "model": ANALYSIS_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                ]
            }
        ]
    }

    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    response = requests.post(CHAT_URL, headers=headers, json=payload, timeout=90)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]

# --- Генерация изображения ---
async def generate_bouquet_image(bouquet_text: str):
    prompt = f"🎨 Сгенерируй реалистичное изображение букета по составу:\n{bouquet_text}"
    payload = {
        "model": DRAW_MODEL,
        "prompt": prompt,
        "size": "1024x1024",
        "n": 1
    }
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    response = requests.post(IMAGE_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()

    img_base64 = data["data"][0]["b64_json"]
    img_bytes = base64.b64decode(img_base64)
    return io.BytesIO(img_bytes)

# --- Обработка фото ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🔍 Анализирую букет…")
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        text = await analyze_bouquet(photo_bytes)
        user_bouquet_state[update.message.from_user.id] = text

        keyboard = [
            [InlineKeyboardButton("💐 Сделать меньше", callback_data="smaller")],
            [InlineKeyboardButton("💐 Сделать больше/пышнее", callback_data="bigger")],
            [InlineKeyboardButton("🎨 Получить рисунок", callback_data="draw")],
            [InlineKeyboardButton("🛒 Оформить заказ", callback_data="order")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"{text}", reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"Ошибка: {str(e)}")

# --- Обработка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current_bouquet = user_bouquet_state.get(user_id, "")

    try:
        if query.data in ["smaller", "bigger"]:
            if query.data == "smaller":
                msg = "🔽 Собираю чуть меньший букет (~20% меньше) 🌸"
                instruction = "уменьши букет на ~20%, сохрани концепцию и изюминку"
            else:
                msg = "🔼 Собираю более пышный букет (+20% цветов) 🌸"
                instruction = "увеличь букет на ~20%, сохрани концепцию и изюминку"

            await query.edit_message_text(msg)

            prompt = f"Коротко пересоставь букет, {instruction}:\n{current_bouquet}"
            payload = {
                "model": ANALYSIS_MODEL,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            }
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            response = requests.post(CHAT_URL, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            data = response.json()
            new_bouquet = data["choices"][0]["message"]["content"]
            user_bouquet_state[user_id] = new_bouquet

            keyboard = [
                [InlineKeyboardButton("🎨 Получить рисунок", callback_data="draw")],
                [InlineKeyboardButton("🛒 Оформить заказ", callback_data="order")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(f"{new_bouquet}", reply_markup=reply_markup)

        elif query.data == "draw":
            await query.edit_message_text("🎨 Генерирую рисунок букета…")
            img_io = await generate_bouquet_image(current_bouquet)
            await query.message.reply_photo(photo=InputFile(img_io, filename="bouquet.png"))

            keyboard = [[InlineKeyboardButton("🛒 Отправить флористу и внести предоплату", callback_data="order")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("Что делать дальше?", reply_markup=reply_markup)

        elif query.data == "order":
            await query.edit_message_text("✅ Заказ оформлен! Флорист получит состав букета. Для внесения предоплаты следуйте инструкциям.")

    except Exception as e:
        await query.message.reply_text(f"Ошибка при обработке кнопки: {str(e)}")

# --- Обработка текста ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Отправь фото букета")

# --- Запуск бота ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
