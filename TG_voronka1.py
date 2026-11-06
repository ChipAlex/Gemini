import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
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
REFERRAL_LINK = os.getenv("REFERRAL_LINK")
#************

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)


# --- СОСТОЯНИЯ ---
class FaberlicFunnel(StatesGroup):
    NEW = State()              # Только подписался
    QUIZ_ANSWERED = State()    # Ответил на квиз
    CLIENT_WARMUP = State()    # Прогрев клиента
    BUSINESS_WARMUP = State()  # Прогрев бизнес-кандидата
    REGISTERED = State()       # Зарегистрировался


# --- ТЕКСТЫ ---
TEXTS = {
    "welcome": (
        "Здравствуйте! 👋\n\n"
        "Я — помощник [Имя жены], директора Faberlic.\n\n"
        "Как и обещал, отправляю гайд «Топ-10 бестселлеров Faberlic» 🎁\n"
        "📎 [ссылка на PDF/файл]\n\n"
        "А теперь давайте подберём для вас оптимальный формат сотрудничества. "
        "Это займет 10 секунд 👇"
    ),
    "quiz_question": "Что вам ближе?",
    "quiz_client": "💄 Хочу косметику со скидкой 20%",
    "quiz_business": "💰 Хочу дополнительный заработок",

    # --- ВЕТКА КЛИЕНТА ---
    "client_1": (
        "Отличный выбор! 👌\n\n"
        "Знаете, почему мои клиенты выбирают Faberlic?\n\n"
        "1️⃣ Это российское производство (Новосибирск) — не зависит от курсов валют\n"
        "2️⃣ Кислородная косметика — уникальная технология Novaftem-O2\n"
        "3️⃣ Сертификация по европейским стандартам\n"
        "4️⃣ Цены на 20-40% ниже люкса при качестве не хуже"
    ),
    "client_2": (
        "Кстати, вот что говорят мои клиенты:\n\n"
        "«Перешла на Faberlic год назад — экономлю около 3000₽ в месяц на косметике. "
        "А крем для рук из серии Expert Pharma — вообще мой must-have» — Елена, Москва\n\n"
        "Завтра покажу вам, как собрать первый заказ до 1500₽ и получить максимум пользы 👇"
    ),
    "client_3": (
        "Готовы оформить регистрацию со скидкой 20%?\n\n"
        "Это бесплатно и ни к чему не обязывает. Вы просто получаете:\n"
        "✅ Скидку 20% на всё навсегда\n"
        "✅ Доступ к закрытым акциям\n"
        "✅ Бонусы за каждый заказ\n"
        "✅ Персональную поддержку от меня\n\n"
        "Регистрация занимает 2 минуты 👇"
    ),
    "client_register_btn": "🎁 Зарегистрироваться со скидкой 20%",

    # --- ВЕТКА БИЗНЕСА ---
    "business_1": (
        "Рада это слышать! 💼\n\n"
        "Меня зовут [Имя жены], я директор Faberlic. За [X] лет в компании я:\n"
        "• Построила команду из [N] человек\n"
        "• Вывела доход на [сумма]\n"
        "• Помогаю женщинам обрести финансовую независимость\n\n"
        "Важно: я не предлагаю «успешный успех». Я предлагаю систему."
    ),
    "business_2": (
        "Почему Faberlic в 2026 году — это актуально:\n\n"
        "📈 Рынок российской косметики растет на 15% в год\n"
        "📱 Можно работать полностью онлайн\n"
        "💸 Стартовый порог — 0₽ (регистрация бесплатна)\n"
        "🎓 Компания обучает за вас\n\n"
        "Завтра расскажу подробнее о системе заработка 👇"
    ),
    "business_3": (
        "Если вам откликается такой формат — давайте созвонимся на 15 минут.\n\n"
        "Я разберу вашу ситуацию и расскажу:\n"
        "• С чего начать в первые 7 дней\n"
        "• Сколько реально можно заработать в первый месяц\n"
        "• Подходит ли вам эта модель\n\n"
        "Никаких обязательств — просто разговор 👇"
    ),
    "business_btn": "📞 Записаться на разбор",

    # --- ПОСЛЕ РЕГИСТРАЦИИ ---
    "after_register": (
        "Поздравляю с регистрацией! 🎉\n\n"
        "Чтобы активировать скидку, сделайте первый заказ в течение 30 дней.\n"
        "Я подготовила для вас стартовый набор-рекомендацию — напишите мне "
        "в личные сообщения: @username_жены"
    ),
}


# --- ХЕНДЛЕРЫ ---
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXTS["welcome"])

    # Квиз
    builder = InlineKeyboardBuilder()
    builder.button(text=TEXTS["quiz_client"], callback_data="quiz:client")
    builder.button(text=TEXTS["quiz_business"], callback_data="quiz:business")
    await message.answer(TEXTS["quiz_question"], reply_markup=builder.as_markup())
    await state.set_state(FaberlicFunnel.NEW)


@router.callback_query(F.data.startswith("quiz:"))
async def quiz_handler(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split(":")[1]
    user_id = callback.from_user.id

    if choice == "client":
        await state.set_state(FaberlicFunnel.CLIENT_WARMUP)
        # Прогрев клиента (3 сообщения с интервалом)
        await callback.message.answer(TEXTS["client_1"])
        await asyncio.sleep(3)  # В проде — 24 часа
        await callback.message.answer(TEXTS["client_2"])
        await asyncio.sleep(3)  # В проде — 24 часа
        await callback.message.answer(TEXTS["client_3"])

        # Кнопка регистрации
        builder = InlineKeyboardBuilder()
        builder.button(text=TEXTS["client_register_btn"], url=REFERRAL_LINK)
        await callback.message.answer("⬇️ Нажмите на кнопку ниже:", reply_markup=builder.as_markup())

    elif choice == "business":
        await state.set_state(FaberlicFunnel.BUSINESS_WARMUP)
        await callback.message.answer(TEXTS["business_1"])
        await asyncio.sleep(3)
        await callback.message.answer(TEXTS["business_2"])
        await asyncio.sleep(3)
        await callback.message.answer(TEXTS["business_3"])

        builder = InlineKeyboardBuilder()
        builder.button(text=TEXTS["business_btn"], url="https://t.me/username_жены")
        await callback.message.answer("⬇️ Запись на разбор:", reply_markup=builder.as_markup())

    await callback.answer()


# --- ТОЧКА ВХОДА ---
async def main():
    logging.info("Faberlic bot starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())