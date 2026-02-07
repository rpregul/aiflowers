import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🌸 Анализирую букет… 🌸")

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_url = file.file_path

    prompt = '''
    Проанализируй фото букета.
    Определи:
    - названия цветов
    - примерное количество каждого
    - ориентировочную стоимость в Москве (в рублях)

    Ответ дай кратко, списком.
    '''

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            }
        ]
    }

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload
    )

    if r.status_code != 200:
    await update.message.reply_text(
        f"Ошибка OpenAI 😢\n\n{r.text}"
    )
    return

data = r.json()

if "choices" not in data:
    await update.message.reply_text(
        f"Неожиданный ответ от OpenAI:\n{data}"
    )
    return

answer = data["choices"][0]["message"]["content"]
await update.message.reply_text(answer)


app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.run_polling()
