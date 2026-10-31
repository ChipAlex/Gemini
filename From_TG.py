import os
from openai import OpenAI
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()  # загружает переменные из .env

# --- Настройки ---
#TELEGRAM_TOKEN = "ВАШ_TELEGRAM_BOT_TOKEN"
#OPENROUTER_API_KEY = "ВАШ_OPENROUTER_API_KEY"
tg_token=os.getenv("TELEGRAM_TOKEN")

# Бесплатная модель (роутер сам выберет доступную free-модель)
# Для Gemini 3.8 Flash замените на "google/gemini-3.8-flash"
MODEL = "openrouter/free"

# Клиент OpenRouter (совместим с OpenAI SDK)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Ты полезный ассистент. Отвечай кратко."},
                {"role": "user", "content": user_text},
            ],
            temperature=0.7,
            max_tokens=1024,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        answer = f"Ошибка при запросе к модели: {e}"

    await update.message.reply_text(answer)

def main():
    #app = Application.builder().token(TELEGRAM_TOKEN).build()
    app = Application.builder().token(tg_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()