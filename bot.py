"""
Бот записи на сессию
aiogram 3.x | Python 3.11+
"""

import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile
import os

from config import BOT_TOKEN, ADMIN_IDS
import database as db
import admin

router = Router()

# Приветственный текст
WELCOME_TEXT = """👋 <b>Добро пожаловать!</b>

Здесь ты можешь записаться на сессию с профессиональным слушателем, который понимает контекст бизнеса, а не смотрит на всё со стороны теории.

<b>Без коучей и советов</b>

Пространство, где можно выговориться, проговорить сложные решения, сомнения или просто разгрузить голову."""

LOGO_PATH = "logo.jpg"


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def has_logo() -> bool:
    return os.path.exists(LOGO_PATH)


async def send_with_logo(message: Message, text: str, keyboard: InlineKeyboardMarkup):
    """Отправить сообщение с логотипом или без"""
    if has_logo():
        await message.answer_photo(
            photo=FSInputFile(LOGO_PATH),
            caption=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


# ═══════════════════════════════════════════════════════════
# FSM States
# ═══════════════════════════════════════════════════════════

class BookingState(StatesGroup):
    viewing_specialist = State()
    choosing_time_type = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()


# ═══════════════════════════════════════════════════════════
# Keyboards
# ═══════════════════════════════════════════════════════════

def welcome_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Записаться на сессию", callback_data="choose_specialist")]
    ])


def specialists_keyboard() -> InlineKeyboardMarkup:
    specs = db.get_specialists()
    buttons = [
        [InlineKeyboardButton(text=f"👤 {spec['name']}", callback_data=f"spec_{spec['id']}")]
        for spec in specs
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="backstart")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def specialist_info_keyboard(spec_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Записаться", callback_data=f"book_{spec_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="backlist")],
    ])


def time_type_keyboard(spec_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚨 В течение 15 минут", callback_data=f"urgent_15_{spec_id}")],
        [InlineKeyboardButton(text="⏰ В течение часа", callback_data=f"urgent_60_{spec_id}")],
        [InlineKeyboardButton(text="📅 Выбрать другое время", callback_data=f"schedule_{spec_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"backspec_{spec_id}")],
    ])


def generate_time_slots() -> list[str]:
    """Генерация слотов 8:00 - 01:00 с шагом 1 час"""
    slots = []
    for hour in range(8, 24):
        slots.append(f"{hour:02d}:00")
    slots.extend(["00:00", "01:00"])
    return slots


def time_slots_keyboard(specialist_id: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []

    for time in generate_time_slots():
        time_safe = time.replace(":", "-")
        row.append(InlineKeyboardButton(text=time, callback_data=f"slot_{time_safe}_{specialist_id}"))

        if len(row) == 4:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"backtime_{specialist_id}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ═══════════════════════════════════════════════════════════
# /start - Приветствие с логотипом
# ═══════════════════════════════════════════════════════════

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    specs = db.get_specialists()
    if not specs:
        await message.answer("⚠️ Нет доступных слушателей.\nПопробуйте позже.")
        return

    await send_with_logo(message, WELCOME_TEXT, welcome_keyboard())


# ═══════════════════════════════════════════════════════════
# Список слушателей (с логотипом)
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "choose_specialist")
async def choose_specialist(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()

    text = "👤 <b>Выберите слушателя:</b>"
    await send_with_logo(callback.message, text, specialists_keyboard())


# ═══════════════════════════════════════════════════════════
# Карточка слушателя (фото специалиста)
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("spec_"))
async def show_specialist_info(callback: CallbackQuery, state: FSMContext):
    spec_id = callback.data.replace("spec_", "")
    specialist = db.get_specialist(spec_id)

    if not specialist:
        await callback.answer("Слушатель не найден", show_alert=True)
        return

    await state.update_data(specialist_id=spec_id, specialist_name=specialist["name"])
    await state.set_state(BookingState.viewing_specialist)

    text = f"<b>{specialist['name']}</b>\n\n{specialist.get('description') or 'Описание отсутствует'}"

    await callback.message.delete()

    if specialist.get('photo_file_id'):
        await callback.message.answer_photo(
            photo=specialist['photo_file_id'],
            caption=text,
            reply_markup=specialist_info_keyboard(spec_id),
            parse_mode="HTML"
        )
    elif has_logo():
        await callback.message.answer_photo(
            photo=FSInputFile(LOGO_PATH),
            caption=text,
            reply_markup=specialist_info_keyboard(spec_id),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            text,
            reply_markup=specialist_info_keyboard(spec_id),
            parse_mode="HTML"
        )


# ═══════════════════════════════════════════════════════════
# Выбор времени (с логотипом)
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("book_"))
async def choose_time_type(callback: CallbackQuery, state: FSMContext):
    spec_id = callback.data.replace("book_", "")
    specialist = db.get_specialist(spec_id)

    await state.update_data(specialist_id=spec_id, specialist_name=specialist["name"])
    await state.set_state(BookingState.choosing_time_type)

    await callback.message.delete()

    text = f"👤 <b>{specialist['name']}</b>\n\n🕐 Когда вам удобно?"
    await send_with_logo(callback.message, text, time_type_keyboard(spec_id))


# ═══════════════════════════════════════════════════════════
# Срочная запись (15 мин / час)
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("urgent_"))
async def urgent_booking(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    minutes = int(parts[1])
    spec_id = "_".join(parts[2:])

    specialist = db.get_specialist(spec_id)

    now = datetime.now()
    booking_time = now + timedelta(minutes=minutes)
    date_str = booking_time.strftime("%Y-%m-%d")
    time_str = booking_time.strftime("%H:%M")

    booking_type = "urgent_15" if minutes == 15 else "urgent_60"
    time_label = "в течение 15 минут" if minutes == 15 else "в течение часа"

    await state.update_data(
        specialist_id=spec_id,
        specialist_name=specialist['name'],
        date=date_str,
        time=time_str,
        booking_type=booking_type,
        time_label=time_label
    )
    await state.set_state(BookingState.entering_name)

    await callback.message.delete()

    await callback.message.answer(
        f"👤 <b>{specialist['name']}</b>\n"
        f"🚨 <b>{time_label.capitalize()}</b>\n\n"
        "✍️ Введите ваше имя:",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════
# Выбор времени (без календаря)
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("schedule_"))
async def show_time_slots(callback: CallbackQuery, state: FSMContext):
    spec_id = callback.data.replace("schedule_", "")
    specialist = db.get_specialist(spec_id)

    await state.update_data(specialist_id=spec_id, specialist_name=specialist['name'])
    await state.set_state(BookingState.choosing_time)

    await callback.message.delete()

    await callback.message.answer(
        f"👤 <b>{specialist['name']}</b>\n\n🕐 Выберите удобное время:",
        reply_markup=time_slots_keyboard(spec_id),
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════
# Выбор слота времени
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("slot_"))
async def select_time_slot(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    time_safe = parts[1]
    spec_id = "_".join(parts[2:])

    time = time_safe.replace("-", ":")

    specialist = db.get_specialist(spec_id)
    date_str = datetime.now().strftime("%Y-%m-%d")

    await state.update_data(
        specialist_id=spec_id,
        specialist_name=specialist['name'],
        date=date_str,
        time=time,
        booking_type='scheduled',
        time_label=time
    )
    await state.set_state(BookingState.entering_name)

    await callback.message.edit_text(
        f"👤 <b>{specialist['name']}</b>\n"
        f"🕐 <b>{time}</b>\n\n"
        "✍️ Введите ваше имя:",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════
# Ввод контактов и подтверждение
# ═══════════════════════════════════════════════════════════

@router.message(BookingState.entering_name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(client_name=message.text)
    await state.set_state(BookingState.entering_phone)
    await message.answer("📱 Введите номер телефона:")


@router.message(BookingState.entering_phone)
async def enter_phone(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    phone = message.text

    # Сохраняем
    booking_id = db.create_booking(
        specialist_id=data['specialist_id'],
        date=data['date'],
        time=data['time'],
        client_name=data['client_name'],
        client_phone=phone,
        client_username=message.from_user.username or "",
        client_user_id=message.from_user.id,
        booking_type=data.get('booking_type', 'scheduled')
    )

    time_label = data.get('time_label', data['time'])

    # Подтверждение с логотипом
    confirm_text = (
        "✅ <b>Сессия забронирована!</b>\n\n"
        f"👤 Слушатель: <b>{data['specialist_name']}</b>\n"
        f"🕐 Время: <b>{time_label}</b>\n\n"
        "С вами свяжутся для подтверждения."
    )
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Новая сессия", callback_data="restart")]
    ])

    await send_with_logo(message, confirm_text, confirm_kb)

    # Уведомление админам
    booking_type_text = {
        'urgent_15': '🚨 СРОЧНО (15 мин)',
        'urgent_60': '⏰ В течение часа',
        'scheduled': '📅 По записи'
    }.get(data.get('booking_type', 'scheduled'), '📅 По записи')

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 <b>Новая сессия #{booking_id}</b>\n\n"
                f"📌 Тип: <b>{booking_type_text}</b>\n"
                f"👤 Слушатель: {data['specialist_name']}\n"
                f"🕐 Время: {time_label}\n\n"
                f"👤 Клиент: <b>{data['client_name']}</b>\n"
                f"📱 Телефон: <code>{phone}</code>\n"
                f"🆔 @{message.from_user.username or 'нет'}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await state.clear()


# ═══════════════════════════════════════════════════════════
# Навигация "Назад"
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "backstart")
async def back_to_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await send_with_logo(callback.message, WELCOME_TEXT, welcome_keyboard())


@router.callback_query(F.data == "backlist")
async def back_to_list(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    text = "👤 <b>Выберите слушателя:</b>"
    await send_with_logo(callback.message, text, specialists_keyboard())


@router.callback_query(F.data.startswith("backspec_"))
async def back_to_specialist(callback: CallbackQuery, state: FSMContext):
    spec_id = callback.data.replace("backspec_", "")
    specialist = db.get_specialist(spec_id)

    await state.set_state(BookingState.viewing_specialist)

    text = f"<b>{specialist['name']}</b>\n\n{specialist.get('description') or 'Описание отсутствует'}"

    await callback.message.delete()

    if specialist.get('photo_file_id'):
        await callback.message.answer_photo(
            photo=specialist['photo_file_id'],
            caption=text,
            reply_markup=specialist_info_keyboard(spec_id),
            parse_mode="HTML"
        )
    elif has_logo():
        await callback.message.answer_photo(
            photo=FSInputFile(LOGO_PATH),
            caption=text,
            reply_markup=specialist_info_keyboard(spec_id),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            text,
            reply_markup=specialist_info_keyboard(spec_id),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("backtime_"))
async def back_to_time_type(callback: CallbackQuery, state: FSMContext):
    spec_id = callback.data.replace("backtime_", "")
    specialist = db.get_specialist(spec_id)

    await state.set_state(BookingState.choosing_time_type)

    await callback.message.delete()

    text = f"👤 <b>{specialist['name']}</b>\n\n🕐 Когда вам удобно?"
    await send_with_logo(callback.message, text, time_type_keyboard(spec_id))


@router.callback_query(F.data == "restart")
async def restart_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await send_with_logo(callback.message, WELCOME_TEXT, welcome_keyboard())


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

async def main():
    db.init_db()
    db.seed_default_data()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(admin.router)
    dp.include_router(router)

    print("🚀 Bot started")
    print(f"📋 Admins: {ADMIN_IDS}")
    print(f"🖼 Logo: {'✅' if has_logo() else '❌'} {LOGO_PATH}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())