import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

#*********
import os
from dotenv import load_dotenv
load_dotenv()  # загружает переменные из .env
# --- Настройки ---
BOT_TOKEN=os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
#************

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage() # В проде заменить на RedisStorage
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# --- СОСТОЯНИЯ ВОРОНКИ (FSM) ---
class FunnelStates(StatesGroup):
    NEW_USER = State()          # Только подписался
    STAGE_1_SENT = State()      # Получил лид-магнит
    STAGE_2_SENT = State()      # Получил кейс
    STAGE_3_SENT = State()      # Получил оффер
    FINISHED = State()          # Воронка пройдена

# --- БАЗА ДАННЫХ (Упрощенный словарь для примера) ---
# В реальности здесь SQLAlchemy + PostgreSQL
users_db = {}

# --- МАРКЕТИНГОВЫЕ ТЕКСТЫ ---
MESSAGES = {
    "welcome": "Здравствуйте! Рад видеть вас. Как и обещал, отправляю ваш Лид-магнит 🎁\n\n[Ссылка на файл/чат]",
    "intro": "Немного обо мне: я занимаюсь [Ваша сфера] уже более 20 лет. Моя цель — помогать людям решать [Проблема].",
    "case": "Кстати, вчера мы завершили проект, где увеличили показатели на 40%. Хотите посмотреть, как мы это сделали? Вот ссылка на разбор: [Ссылка]",
    "offer": "Если вы готовы делегировать эту задачу и получить гарантированный результат, я предлагаю вам свою консультацию. Стоимость: [Цена]. Записаться: [Ссылка]",
    "follow_up": "Вижу, вы пока не взяли консультацию. Возможно, остались вопросы? Напишите мне лично: @YourUsername, разберем вашу ситуацию."
}

# --- ФУНКЦИИ ОТПРАВКИ (Имитация отложенных сообщений) ---
async def send_delayed_message(user_id: int, text: str, delay_seconds: int, next_state: State):
    """Отправляет сообщение с задержкой и обновляет FSM"""
    try:
        await asyncio.sleep(delay_seconds)
        await bot.send_message(user_id, text)

        # Обновляем состояние в FSM
        context = dp.fsm.get_context(bot=bot, chat_id=user_id, user_id=user_id)
        await context.set_state(next_state)

        logger.info(f"Sent delayed message to {user_id}. State: {next_state.state}")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error sending delayed message to {user_id}: {e}")

# --- ХЕНДЛЕРЫ ---
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    # Сохраняем пользователя в БД
    users_db[user_id] = {"joined": datetime.now()}

    # Шаг 1: Приветствие и Лид-магнит
    await message.answer(MESSAGES["welcome"])
    await message.answer(MESSAGES["intro"])
    await state.set_state(FunnelStates.STAGE_1_SENT)

    # Запускаем фоновые задачи для следующих шагов воронки
    # 24 часа = 86400 секунд
    asyncio.create_task(send_delayed_message(
        user_id, MESSAGES["case"], 86400, FunnelStates.STAGE_2_SENT
    ))
    # 48 часов от старта (24 часа после кейса)
    asyncio.create_task(send_delayed_message(
        user_id, MESSAGES["offer"], 172800, FunnelStates.STAGE_3_SENT
    ))
    # 72 часа от старта
    asyncio.create_task(send_delayed_message(
        user_id, MESSAGES["follow_up"], 259200, FunnelStates.FINISHED
    ))

@router.message(F.text == "Отписаться")
async def unsubscribe(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Вы отписались от рассылки. Если передумаете, просто напишите /start")

# --- ТОЧКА ВХОДА ---
async def main():
    logger.info("Bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())