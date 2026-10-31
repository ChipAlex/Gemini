import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()  # загружает переменные из .env

# --- Настройки ---
#TELEGRAM_TOKEN = "ВАШ_TELEGRAM_BOT_TOKEN"
#OPENROUTER_API_KEY = "ВАШ_OPENROUTER_API_KEY"
TELEGRAM_TOKEN=os.getenv("TELEGRAM_TOKEN")

# Бесплатная модель (роутер сам выберет доступную free-модель)
# Для Gemini 3.8 Flash замените на "google/gemini-3.8-flash"
MODEL = "openrouter/free"

MODEL = "openrouter/free"

# Асинхронный клиент — не блокирует event loop
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

SYSTEM_PROMPT = "Ты полезный ассистент. Отвечай кратко."


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и инициализация истории."""
    context.user_data["history"] = []
    await update.message.reply_text(
        "Привет! Я бот с доступом к LLM через OpenRouter.\n"
        "Просто напиши сообщение — я отвечу.\n"
        "Команды:\n"
        "/start — начать заново\n"
        "/reset — очистить историю диалога"
    )


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очищает историю диалога для текущего пользователя."""
    context.user_data["history"] = []
    await update.message.reply_text("История диалога очищена. Начинаем с чистого листа.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not user_text:
        return

    # Инициализируем историю, если её ещё нет
    history = context.user_data.setdefault("history", [])

    # Добавляем сообщение пользователя
    history.append({"role": "user", "content": user_text})

    # Ограничиваем историю последними 10 сообщениями, чтобы не раздувать запрос
    history[:] = history[-10:]

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            temperature=0.7,
            max_tokens=1024,
        )
        answer = (response.choices[0].message.content or "").strip()
        if not answer:
            answer = "Модель вернула пустой ответ."
    except Exception as e:
        answer = f"Ошибка при запросе к модели: {e}"

    # Сохраняем ответ ассистента в историю
    history.append({"role": "assistant", "content": answer})

    await update.message.reply_text(answer)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("reset", reset_command))

    # Обычные текстовые сообщения (кроме команд)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()