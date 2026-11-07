import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import aiosqlite

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Загружаем переменные из .env
load_dotenv()

# --- Настройки ---
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
TELEGRAM_USERNAME = os.getenv("TELEGRAM_USERNAME")
REFERRAL_LINK = os.getenv("REFERRAL_LINK")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
LARISA_CHAT_ID = os.getenv("LARISA_CHAT_ID")

WA_NUMBER = PHONE_NUMBER.replace("+", "") if PHONE_NUMBER else ""
PDF_FILE_PATH = "foto/test.pdf"
DB_PATH = "funnel_tasks.db"

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


# ============================================================
# 🗄️ АНАЛИТИКА И БАЗА ДАННЫХ (SQLite)
# ============================================================
async def init_db():
    """Инициализация таблиц для аналитики и (опционально) отложенных задач"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP
            )
        """)
        # Таблица событий (воронок)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_type TEXT,
                timestamp TIMESTAMP
            )
        """)
        await db.commit()


async def log_user_activity(user_id: int, username: str, full_name: str, event_type: str):
    """Записывает действие пользователя в БД"""
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        # 1. Обновляем или создаем запись пользователя
        await db.execute("""
            INSERT INTO users (user_id, username, full_name, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                last_seen = excluded.last_seen,
                username = COALESCE(excluded.username, users.username),
                full_name = COALESCE(excluded.full_name, users.full_name)
        """, (user_id, username, full_name, now, now))

        # 2. Логируем конкретное событие
        await db.execute("""
            INSERT INTO events (user_id, event_type, timestamp)
            VALUES (?, ?, ?)
        """, (user_id, event_type, now))

        await db.commit()
    logging.info(f"📊 Аналитика: user_id={user_id}, event={event_type}")


# ============================================================
# 🔔 УВЕДОМЛЕНИЯ ЛАРИСЕ
# ============================================================
async def notify_larisa(user, event_type: str, extra_info: str = ""):
    if not LARISA_CHAT_ID:
        return
    full_name = user.full_name or "Неизвестно"
    username = f"@{user.username}" if user.username else "не указан"
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    text = f"🔔 <b>{event_type}</b>\n\n👤 <b>Имя:</b> {full_name}\n🆔 <b>Username:</b> {username}\n"
    if extra_info:
        text += f"\n📌 <b>Детали:</b> {extra_info}\n"
    text += f"\n🕐 <b>Время:</b> {current_time}"

    builder = InlineKeyboardBuilder()
    if user.username:
        builder.button(text="💬 Написать клиенту", url=f"https://t.me/{user.username}")
        builder.adjust(1)

    try:
        await bot.send_message(chat_id=LARISA_CHAT_ID, text=text, parse_mode="HTML",
                               reply_markup=builder.as_markup() if user.username else None)
    except Exception as e:
        logging.error(f"Не удалось уведомить Ларису: {e}")


# --- СОСТОЯНИЯ ---
class FaberlicFunnel(StatesGroup):
    WELCOME = State()
    QUIZ = State()
    CLIENT_WARMUP = State()
    BUSINESS_WARMUP = State()


# --- ТЕКСТЫ ---
TEXTS = {
    "welcome_intro": (
        "Здравствуйте! 👋\n\n"
        "Меня зовут Лариса, я — Директор Faberlic и владелица двух пунктов выдачи.\n\n"
        "Нажмите кнопку ниже, чтобы получить гайд и подобрать формат сотрудничества 👇"
    ),
    "quiz_question": "Что вам ближе?",
    "quiz_client": "💄 Хочу косметику со скидкой 20%",
    "quiz_business": "💰 Хочу дополнительный заработок",

    "client_1": (
        "💎 <b>Почему мои клиенты выбирают Faberlic?</b>\n\n"
        "1️⃣ Российское производство (Новосибирск) — не зависит от курсов валют\n"
        "2️⃣ Кислородная косметика Novaftem-O2 — уникальная технология\n"
        "3️⃣ Цены на 20-40% ниже люкса при отличном качестве\n\n"
        "Как владелица двух пунктов выдачи, я лично контролирую сборку заказов 📦"
    ),
    "client_2": (
        "💬 <b>Отзыв клиента:</b>\n\n"
        "«Перешла на Faberlic год назад — экономлю около 3000₽ в месяц. "
        "Крем Expert Pharma — мой must-have» — Елена, Москва\n\n"
        "Далее покажу, как получить максимальную выгоду 👇"
    ),
    "client_3": (
        "🎁 <b>Готовы оформить регистрацию со скидкой 20%?</b>\n\n"
        "Это бесплатно и ни к чему не обязывает. Вы получаете:\n"
        "✅ Скидку 20% на всё — навсегда\n"
        "✅ Доступ к закрытым акциям\n"
        "✅ Бонусы за каждый заказ\n"
        "✅ Персональную поддержку от меня\n\n"
        "Регистрация занимает 2 минуты 👇"
    ),
    "client_register_btn": "🎁 Зарегистрироваться со скидкой 20%",

    "business_1": (
        "💼 <b>Рада это слышать!</b>\n\n"
        "Я Директор Faberlic и владелица двух пунктов выдачи. "
        "Я не предлагаю «успешный успех», я предлагаю рабочую систему:\n\n"
        "• Стабильная команда и пассивный доход\n"
        "• Помощь женщинам в обретении финансовой независимости\n"
        "• Полная поддержка на каждом этапе"
    ),
    "business_2": (
        "📈 <b>Почему Faberlic в 2026 году — это актуально:</b>\n\n"
        "📊 Рынок российской косметики растёт на 15% в год\n"
        "📱 Можно работать полностью онлайн\n"
        "💸 Стартовый порог — 0₽ (регистрация бесплатна)\n"
        "🎓 Компания обучает за вас\n"
        "📦 У меня 2 пункта выдачи — вам не придётся хранить товар дома"
    ),
    "business_3": (
        "🤝 <b>Если вам откликается такой формат — давайте свяжемся.</b>\n\n"
        "Я разберу вашу ситуацию и расскажу:\n"
        "• С чего начать в первые 7 дней\n"
        "• Сколько реально можно заработать в первый месяц\n"
        "• Подходит ли вам эта модель\n\n"
        f"📞 Мой номер телефона: {PHONE_NUMBER}\n"
        "_(На большинстве смартфонов номер в тексте подсвечивается синим для звонка)_\n\n"
        "Никаких обязательств — просто разговор. Выберите удобный способ 👇"
    ),
    "btn_write_tg": "💬 Написать в Telegram",
    "btn_write_wa": "📱 Написать / Позвонить в WhatsApp",
}


# --- ХЕНДЛЕРЫ ---
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    # 1. Логируем вход в БД
    await log_user_activity(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        event_type="start_bot"
    )

    # 2. Отправляем PDF
    if os.path.exists(PDF_FILE_PATH):
        try:
            document_to_send = FSInputFile(PDF_FILE_PATH)
            await message.answer_document(
                document=document_to_send,
                caption="🎁 Ваш гайд «Топ-10 бестселлеров Faberlic»"
            )
        except Exception as e:
            logging.error(f"Ошибка отправки PDF: {e}")
            await message.answer(f"⚠️ Не удалось загрузить гайд. Напишите мне: @{TELEGRAM_USERNAME}")
    else:
        logging.warning(f"PDF файл не найден: {PDF_FILE_PATH}")

    # 3. Кнопка "Начать"
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Начать", callback_data="start_funnel")
    builder.adjust(1)

    await message.answer(TEXTS["welcome_intro"], reply_markup=builder.as_markup())
    await state.set_state(FaberlicFunnel.WELCOME)


@router.callback_query(F.data == "start_funnel")
async def start_funnel_handler(callback: CallbackQuery, state: FSMContext):
    await log_user_activity(callback.from_user.id, callback.from_user.username, callback.from_user.full_name,
                            "clicked_start")
    await notify_larisa(user=callback.from_user, event_type="🆕 Новый заход в воронку")

    builder = InlineKeyboardBuilder()
    builder.button(text=TEXTS["quiz_client"], callback_data="quiz:client")
    builder.button(text=TEXTS["quiz_business"], callback_data="quiz:business")
    builder.adjust(1)

    await callback.message.answer(TEXTS["quiz_question"], reply_markup=builder.as_markup())
    await state.set_state(FaberlicFunnel.QUIZ)
    await callback.answer()


@router.callback_query(F.data == "back_to_quiz")
async def back_to_quiz_handler(callback: CallbackQuery, state: FSMContext):
    await log_user_activity(callback.from_user.id, callback.from_user.username, callback.from_user.full_name,
                            "back_to_quiz")

    builder = InlineKeyboardBuilder()
    builder.button(text=TEXTS["quiz_client"], callback_data="quiz:client")
    builder.button(text=TEXTS["quiz_business"], callback_data="quiz:business")
    builder.adjust(1)

    await callback.message.answer(TEXTS["quiz_question"], reply_markup=builder.as_markup())
    await state.set_state(FaberlicFunnel.QUIZ)
    await callback.answer("Возврат к выбору")


@router.callback_query(F.data.startswith("quiz:"))
async def quiz_handler(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split(":")[1]
    user = callback.from_user

    if choice == "client":
        await log_user_activity(user.id, user.username, user.full_name, "chose_client")
        await state.set_state(FaberlicFunnel.CLIENT_WARMUP)
        await notify_larisa(user=user, event_type="🎯 Выбор в квизе", extra_info="💄 Ветка «Клиент»")

        await callback.message.answer(TEXTS["client_1"], parse_mode="HTML")
        await callback.message.answer(TEXTS["client_2"], parse_mode="HTML")

        builder = InlineKeyboardBuilder()
        builder.button(text=TEXTS["client_register_btn"], url=REFERRAL_LINK)
        builder.button(text="🔙 Вернуться к выбору", callback_data="back_to_quiz")
        builder.adjust(1)
        await callback.message.answer(TEXTS["client_3"], parse_mode="HTML", reply_markup=builder.as_markup())

    elif choice == "business":
        await log_user_activity(user.id, user.username, user.full_name, "chose_business")
        await state.set_state(FaberlicFunnel.BUSINESS_WARMUP)
        await notify_larisa(user=user, event_type="🔥 ГОРЯЧИЙ ЛИД", extra_info="💰 Ветка «Бизнес»")

        await callback.message.answer(TEXTS["business_1"], parse_mode="HTML")
        await callback.message.answer(TEXTS["business_2"], parse_mode="HTML")

        builder = InlineKeyboardBuilder()
        builder.button(text=TEXTS["btn_write_tg"], url=f"https://t.me/{TELEGRAM_USERNAME}")
        builder.button(text=TEXTS["btn_write_wa"], url=f"https://wa.me/{WA_NUMBER}")
        builder.button(text="🔙 Вернуться к выбору", callback_data="back_to_quiz")
        builder.adjust(1)
        await callback.message.answer(TEXTS["business_3"], parse_mode="HTML", reply_markup=builder.as_markup())

    await callback.answer()


# --- ТОЧКА ВХОДА ---
async def main():
    logging.info("Инициализация базы данных аналитики...")
    await init_db()

    logging.info("Faberlic bot (Larisa) starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())