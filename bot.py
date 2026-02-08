import os
import io
import base64
import requests
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, CallbackQueryHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
ANALYSIS_MODEL = "google/gemma-3-12b-it:free"
DRAW_MODEL = "blackforest/flux.2-pro"

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
        "🌸 Какие цветы и их количество (в одном пункте, жирным, без звездочек)\n"
        "💰 Средняя стоимость букета в рублях, конкретно и коротко"
    )

    payload = {
        "model": ANALYSIS_MODEL,
        "modalities": ["text", "image"],
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
    prompt = f"🎨 Сгенерируй реалистичное изображение букета:\n{bouquet_text}"
    payload = {
        "model": DRAW_MODEL,
        "modalities": ["image", "text"],
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        ]
    }
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    response = requests.post(CHAT_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()

    # В ответе должна быть секция images
    images = data["choices"][0]["message"].get("images", [])
    if images:
        # Берём первый image_url.base64
        img_url = images[0]["image_url"]["url"]
        if img_url.startswith("data:image"):
            header, img_base64 = img_url.split(",", 1)
            img_bytes = base64.b64decode(img_base64)
            return io.BytesIO(img_bytes)
    return None

# --- Обработка фото ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("🔍 Анализирую фото и подбираю цветы…")
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        text = await analyze_bouquet(photo_bytes)
        user_bouquet_state[update.message.from_user.id] = text

        keyboard = [
            [InlineKeyboardButton("💐 Сделать букет меньше (~20%)", callback_data="smaller")],
            [InlineKeyboardButton("💐 Собрать пышнее и больше (~20%)", callback_data="bigger")],
            [InlineKeyboardButton("🎨 Нарисовать примерный букет", callback_data="draw")],
            [InlineKeyboardButton("🛒 Оформить заказ", callback_data="order")]
        ]
        await update.message.reply_text(f"{text}", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

# --- Обработка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    current_bouquet = user_bouquet_state.get(user_id, "")

    try:
        if query.data in ["smaller", "bigger"]:
            if query.data == "smaller":
                msg = "🔽 Собираю для вас чуть меньший букет…"
                instruction = "уменьши букет на 20% по стоимости, сохрани стиль и изюминку букета. покупатель хочет немного сэкономить, не потеряв в качестве. дай короткий ответ с количеством цветков и итоговой суммой. "
            else:
                msg = "🔼 Формирую пышнее букет…"
                instruction = "увеличь букет на 20% по стоимости, сохрани стиль и изюминку букета. покупатель хочет сделать более роскошный букет, сохранив его идею,, фишку, изюминку. дай короткий ответ с количеством цветков и итоговой суммой."

            await query.edit_message_text(msg)

            prompt = f"{instruction}:\n{current_bouquet}"
            payload = {
                "model": ANALYSIS_MODEL,
                "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            }
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            resp = requests.post(CHAT_URL, headers=headers, json=payload, timeout=90)
            resp.raise_for_status()
            new_bouquet = resp.json()["choices"][0]["message"]["content"]
            user_bouquet_state[user_id] = new_bouquet

            keyboard = [
                [InlineKeyboardButton("🎨 Нарисовать примерный букет", callback_data="draw")],
                [InlineKeyboardButton("🛒 Оформить заказ", callback_data="order")]
            ]
            await query.message.reply_text(new_bouquet, reply_markup=InlineKeyboardMarkup(keyboard))

        elif query.data == "draw":
            await query.edit_message_text("🎨 Рисую ваш букет...")
            img_io = await generate_bouquet_image(current_bouquet)
            if img_io:
                await query.message.reply_photo(photo=InputFile(img_io, filename="bouquet.png"))
            else:
                await query.message.reply_text("❌ Не удалось сгенерировать картинку.")

            keyboard = [[InlineKeyboardButton("🛒 Купить", callback_data="order")]]
            await query.message.reply_text("Что дальше?", reply_markup=InlineKeyboardMarkup(keyboard))

        elif query.data == "order":
            await query.edit_message_text("✅ Заказ оформлен! Передала ваш букет на сборку флористам в магазин, они начнут собирать его после предоплаты ❤️")
    except Exception as e:
        await query.message.reply_text(f"Ошибка при обработке: {e}")

# --- Текстовые сообщения ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Пришлите фото букета")

# --- Запуск ---
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT, handle_text))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
