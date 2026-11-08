import asyncio
import logging
import os
import csv  # <-- Добавлено для экспорта в CSV
import html
from datetime import datetime, timedelta
from dotenv import load_dotenv
import aiosqlite

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command  # <-- Добавлено Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()

# --- Настройки ---
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
raw_admin_ids = os.getenv("ADMIN_ID", "")
ADMIN_IDS = [int(x.strip()) for x in raw_admin_ids.split(",") if x.strip()]
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
# 🗄️ АНАЛИТИКА И БАЗА ДАННЫХ
# ============================================================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP
            )
        """)
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
    now = datetime.now().isoformat()
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                INSERT INTO users (user_id, username, full_name, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET 
                    last_seen = excluded.last_seen,
                    username = COALESCE(excluded.username, users.username),
                    full_name = COALESCE(excluded.full_name, users.full_name)
            """, (user_id, username, full_name, now, now))

            await db.execute("""
                INSERT INTO events (user_id, event_type, timestamp)
                VALUES (?, ?, ?)
            """, (user_id, event_type, now))
            await db.commit()
    except Exception as e:
        logging.error(f"Ошибка логирования в БД: {e}")


# ============================================================
# 📊 ФУНКЦИИ СТАТИСТИКИ
# ============================================================
async def get_stats_summary(start_date: datetime, end_date: datetime) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("SELECT COUNT(DISTINCT user_id) as count FROM users WHERE first_seen BETWEEN ? AND ?",
                                  (start_date.isoformat(), end_date.isoformat()))
        row = await cursor.fetchone()
        total_users = row['count'] if row else 0

        cursor = await db.execute("SELECT COUNT(*) as count FROM events WHERE timestamp BETWEEN ? AND ?",
                                  (start_date.isoformat(), end_date.isoformat()))
        row = await cursor.fetchone()
        total_events = row['count'] if row else 0

        cursor = await db.execute(
            "SELECT event_type, COUNT(*) as count FROM events WHERE timestamp BETWEEN ? AND ? GROUP BY event_type ORDER BY count DESC",
            (start_date.isoformat(), end_date.isoformat()))
        events_dist = await cursor.fetchall()

        chose_client = next((r['count'] for r in events_dist if r['event_type'] == 'chose_client'), 0)
        chose_business = next((r['count'] for r in events_dist if r['event_type'] == 'chose_business'), 0)
        start_bot = next((r['count'] for r in events_dist if r['event_type'] == 'start_bot'), 0)
        clicked_start = next((r['count'] for r in events_dist if r['event_type'] == 'clicked_start'), 0)

        return {
            'total_users': total_users, 'total_events': total_events,
            'chose_client': chose_client, 'chose_business': chose_business,
            'start_bot': start_bot, 'clicked_start': clicked_start,
            'conversion_to_quiz': (clicked_start / start_bot * 100) if start_bot > 0 else 0,
            'conversion_client': (chose_client / clicked_start * 100) if clicked_start > 0 else 0,
            'conversion_business': (chose_business / clicked_start * 100) if clicked_start > 0 else 0,
        }


async def get_user_details(start_date: datetime, end_date: datetime, limit: int = 50) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("""
            SELECT 
                u.user_id, u.username, u.full_name, e.event_type, e.timestamp,
                (strftime('%s', e.timestamp) - strftime('%s', LAG(e.timestamp) OVER (PARTITION BY e.user_id ORDER BY e.timestamp))) as time_spent_seconds
            FROM events e
            JOIN users u ON e.user_id = u.user_id
            WHERE e.timestamp BETWEEN ? AND ?
            ORDER BY u.user_id, e.timestamp
            LIMIT ?
        """, (start_date.isoformat(), end_date.isoformat(), limit)) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                'user_id': row['user_id'],
                'username': row['username'] or 'не указан',
                'full_name': row['full_name'] or 'не указано',
                'event_type': row['event_type'],
                'timestamp': row['timestamp'],
                'time_spent_seconds': row['time_spent_seconds']
            } for row in rows
        ]


# ============================================================
# 🎯 РЕТАРГЕТИНГ: ПОИСК "ЗАВИСШИХ" ЛИДОВ
# ============================================================
async def get_stuck_leads(hours_threshold: int = 48) -> list:
    """
    Возвращает список пользователей, чье последнее действие - выбор ветки,
    и это действие произошло более hours_threshold часов назад.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        query = """
            SELECT u.user_id, u.username, u.full_name, e.event_type, e.timestamp
            FROM users u
            JOIN events e ON u.user_id = e.user_id
            WHERE e.timestamp = (
                SELECT MAX(timestamp) FROM events WHERE user_id = u.user_id
            )
            AND e.event_type IN ('chose_client', 'chose_business')
            AND e.timestamp < datetime('now', '-' || ? || ' hours')
            ORDER BY e.timestamp ASC
        """
        async with db.execute(query, (hours_threshold,)) as cursor:
            rows = await cursor.fetchall()

        return [
            {
                'user_id': row['user_id'],
                'username': row['username'] or 'не указан',
                'full_name': row['full_name'] or 'не указано',
                'event_type': 'Клиент' if row['event_type'] == 'chose_client' else 'Бизнес',
                'timestamp': row['timestamp']
            }
            for row in rows
        ]

async def generate_stuck_leads_csv(leads: list, filename: str = "stuck_leads_report.csv") -> str:
    """
    Генерирует CSV-файл с оптимизированной структурой для удобного просмотра.
    """
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        # Более компактные заголовки
        fieldnames = ['ID', 'Username', 'Имя', 'Ветка', 'Когда завис', 'Контакт']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for lead in leads:
            # Формируем короткую ссылку только с username
            contact = f"@{lead['username']}" if lead['username'] != 'не указан' else f"ID: {lead['user_id']}"

            # Форматируем дату в более компактный вид
            dt = datetime.fromisoformat(lead['timestamp'])
            date_compact = dt.strftime("%d.%m %H:%M")

            writer.writerow({
                'ID': lead['user_id'],
                'Username': f"@{lead['username']}" if lead['username'] != 'не указан' else "-",
                'Имя': lead['full_name'][:30] + "..." if len(lead['full_name'] or "") > 30 else (
                            lead['full_name'] or "-"),
                'Ветка': lead['event_type'],
                'Когда завис': date_compact,
                'Контакт': contact
            })
    return filename
# ============================================================
# 🔔 УВЕДОМЛЕНИЯ ЛАРИСЕ
# ============================================================
async def notify_larisa(user, event_type: str, extra_info: str = ""):
    if not LARISA_CHAT_ID: return
    full_name = user.full_name or "Неизвестно"
    username = f"@{user.username}" if user.username else "не указан"
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")

    text = f"🔔 <b>{event_type}</b>\n\n👤 <b>Имя:</b> {full_name}\n🆔 <b>Username:</b> {username}\n"
    if extra_info: text += f"\n📌 <b>Детали:</b> {extra_info}\n"
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


# --- СОСТОЯНИЯ И ТЕКСТЫ ---
class FaberlicFunnel(StatesGroup):
    WELCOME = State()
    QUIZ = State()
    CLIENT_WARMUP = State()
    BUSINESS_WARMUP = State()


TEXTS = {
    "welcome_intro": "Здравствуйте! 👋\n\nМеня зовут Лариса, я — Директор Faberlic и владелица двух пунктов выдачи.\n\nНажмите кнопку ниже, чтобы получить гайд и подобрать формат сотрудничества 👇",
    "quiz_question": "Что вам ближе?",
    "quiz_client": "💄 Хочу косметику со скидкой 20%",
    "quiz_business": "💰 Хочу дополнительный заработок",
    "client_1": "💎 <b>Почему мои клиенты выбирают Faberlic?</b>\n\n1️⃣ Российское производство (Новосибирск)\n2️⃣ Кислородная косметика Novaftem-O2\n3️⃣ Цены на 20-40% ниже люкса\n\nКак владелица двух пунктов выдачи, я лично контролирую сборку заказов 📦",
    "client_2": "💬 <b>Отзыв клиента:</b>\n\n«Перешла на Faberlic год назад — экономлю около 3000₽ в месяц. Крем Expert Pharma — мой must-have» — Елена, Москва\n\nДалее покажу, как получить максимальную выгоду 👇",
    "client_3": "🎁 <b>Готовы оформить регистрацию со скидкой 20%?</b>\n\n✅ Скидка 20% на всё навсегда\n✅ Доступ к закрытым акциям\n✅ Бонусы за каждый заказ\n✅ Персональная поддержка\n\nРегистрация занимает 2 минуты 👇",
    "client_register_btn": "🎁 Зарегистрироваться со скидкой 20%",
    "business_1": "💼 <b>Рада это слышать!</b>\n\nЯ Директор Faberlic и владелица двух пунктов выдачи. Я не предлагаю «успешный успех», я предлагаю рабочую систему:\n\n• Стабильная команда и пассивный доход\n• Помощь женщинам в обретении финансовой независимости",
    "business_2": "📈 <b>Почему Faberlic в 2026 году — это актуально:</b>\n\n📊 Рынок растёт на 15% в год\n📱 Можно работать полностью онлайн\n💸 Стартовый порог — 0₽\n📦 У меня 2 пункта выдачи — вам не придётся хранить товар дома",
    "business_3": f"🤝 <b>Если вам откликается такой формат — давайте свяжемся.</b>\n\nЯ разберу вашу ситуацию и расскажу, с чего начать.\n\n📞 Мой номер телефона: {PHONE_NUMBER}\n_(Нажмите на номер, чтобы позвонить)_\n\nНикаких обязательств — просто разговор. Выберите удобный способ 👇",
    "btn_write_tg": "💬 Написать в Telegram",
    "btn_write_wa": "📱 Написать / Позвонить в WhatsApp",
}


# --- ХЕНДЛЕРЫ ВОРОНКИ ---
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await log_user_activity(message.from_user.id, message.from_user.username, message.from_user.full_name, "start_bot")

    if os.path.exists(PDF_FILE_PATH):
        try:
            await message.answer_document(document=FSInputFile(PDF_FILE_PATH),
                                          caption="🎁 Ваш гайд «Топ-10 бестселлеров Faberlic»")
        except Exception as e:
            logging.error(f"Ошибка отправки PDF: {e}")
    else:
        logging.warning(f"PDF файл не найден: {PDF_FILE_PATH}")

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
        builder.button(text="⬅️ Вернуться к выбору", callback_data="back_to_quiz")
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
        builder.button(text="⬅️ Вернуться к выбору", callback_data="back_to_quiz")
        builder.adjust(1)
        await callback.message.answer(TEXTS["business_3"], parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()


# ============================================================
# 📊 АДМИН-КОМАНДЫ
# ============================================================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде")
        return

    await bot.send_chat_action(message.chat.id, "typing")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    try:
        await show_stats_summary(message, start_date, end_date)
    except Exception as e:
        logging.exception("Ошибка при формировании сводной статистики")
        await message.answer(f"⚠️ Не удалось получить статистику. Возможно, база данных заблокирована.\n\nОшибка: {e}")


async def show_stats_summary(message: Message, start_date: datetime, end_date: datetime):
    stats = await get_stats_summary(start_date, end_date)
    period_str = f"с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')}"

    text = (
        f"📊 <b>Статистика воронки</b>\n📅 Период: {period_str}\n\n"
        f"👥 <b>Пользователи:</b>\n• Всего уникальных: {stats['total_users']}\n• Всего событий: {stats['total_events']}\n\n"
        f"📈 <b>Конверсии:</b>\n• Запустили бота: {stats['start_bot']}\n• Нажали «Начать»: {stats['clicked_start']}\n• Конверсия в старт: {stats['conversion_to_quiz']:.1f}%\n\n"
        f"🎯 <b>Выбор ветки:</b>\n• 💄 Клиенты: {stats['chose_client']} ({stats['conversion_client']:.1f}%)\n• 💰 Бизнес: {stats['chose_business']} ({stats['conversion_business']:.1f}%)\n"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Детализация по пользователям", callback_data="stats:details")
    builder.button(text="📅 За месяц", callback_data="stats:period:month")
    builder.button(text="🌐 За всё время", callback_data="stats:period:all")
    builder.adjust(1)

    await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("stats:"))
async def callback_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    action = callback.data.split(":")[1]
    try:
        if action == "details":
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            await show_user_details(callback.message, start_date, end_date)
        elif action == "period":
            period = callback.data.split(":")[2]
            end_date = datetime.now()
            if period == "month":
                start_date = end_date - timedelta(days=30)
            elif period == "all":
                start_date = datetime(2020, 1, 1)
            else:
                start_date = end_date - timedelta(days=7)
            await show_stats_summary(callback.message, start_date, end_date)
        elif action == "back":
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            await show_stats_summary(callback.message, start_date, end_date)
    except Exception as e:
        logging.exception("Ошибка при обработке кнопок статистики")
        await callback.message.answer(f"⚠️ Ошибка: {e}")

    await callback.answer()


async def show_user_details(message: Message, start_date: datetime, end_date: datetime):
    await bot.send_chat_action(message.chat.id, "typing")
    users_data = await get_user_details(start_date, end_date)

    if not users_data:
        await message.answer("📭 Нет данных за выбранный период")
        return

    current_user = None
    text = f"📋 <b>Детализация за {start_date.strftime('%d.%m')} по {end_date.strftime('%d.%m.%Y')}</b>\n\n"

    event_names = {
        'start_bot': 'Запуск бота',
        'clicked_start': 'Нажал Старт',
        'chose_client': 'Выбрал Клиент',
        'chose_business': 'Выбрал Бизнес',
        'back_to_quiz': 'Вернулся назад'
    }

    for row in users_data:
        if row['user_id'] != current_user:
            if current_user is not None:
                text += "\n"
            current_user = row['user_id']
            safe_name = html.escape(row['full_name'])
            safe_username = html.escape(row['username'])
            text += f"👤 <b>{safe_name}</b> (@{safe_username})\n"

        timestamp = datetime.fromisoformat(row['timestamp']).strftime("%d.%m %H:%M")
        time_str = ""
        if row['time_spent_seconds'] is not None and row['time_spent_seconds'] > 0:
            minutes = int(row['time_spent_seconds'] // 60)
            seconds = int(row['time_spent_seconds'] % 60)
            time_str = f" ({minutes}м {seconds}с)"

        event_name = event_names.get(row['event_type'], row['event_type'])
        text += f"  • {event_name}: {timestamp}{time_str}\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="К сводке", callback_data="stats:back")
    builder.adjust(1)

    if len(text) > 4000:
        parts = [text[i:i + 4000] for i in range(0, len(text), 4000)]
        for i, part in enumerate(parts):
            await message.answer(part, parse_mode="HTML",
                                 reply_markup=builder.as_markup() if i == len(parts) - 1 else None)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())


# ============================================================
# 🎯 АДМИН-КОМАНДА: ВЫГРУЗКА ЗАВИСШИХ ЛИДОВ
# ============================================================
@router.message(Command("stuck_leads"))
async def cmd_stuck_leads(message: Message):
    """Команда для выгрузки списка зависших лидов в CSV"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к этой команде")
        return

    await message.answer("⏳ Анализирую базу данных, ищу зависших лидов (за последние 48 часов)...")

    # 1. Получаем данные (порог = 48 часов)
    leads = await get_stuck_leads(hours_threshold=48)

    if not leads:
        await message.answer("✅ Отличная новость! Зависших лидов нет. Все, кто выбрал ветку, сделали это недавно.")
        return

    # 2. Генерируем CSV файл
    csv_filename = "stuck_leads_report.csv"
    await generate_stuck_leads_csv(leads, csv_filename)

    # 3. Отправляем файл админу
    caption = (
        f"📊 <b>Отчет по зависшим лидам</b>\n"
        f"Найдено: {len(leads)} чел.\n\n"
        f"Это пользователи, которые выбрали ветку, но не перешли к связи.\n"
        f"Используйте колонку 'Ссылка для связи' для ручного дожима."
    )
    document = FSInputFile(csv_filename)
    await message.answer_document(document=document, caption=caption, parse_mode="HTML")

    # 4. Очищаем временный файл с диска после отправки
    if os.path.exists(csv_filename):
        os.remove(csv_filename)


# --- ТОЧКА ВХОДА ---
async def main():
    logging.info("Инициализация базы данных аналитики...")
    await init_db()
    logging.info(f"Faberlic bot (Larisa) starting... Admin IDs: {ADMIN_IDS}")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())