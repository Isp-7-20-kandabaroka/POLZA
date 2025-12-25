"""
Admin Panel - Full control over bot
With photo upload support
"""

from datetime import datetime, timedelta
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
import database as db

router = Router()

# ═══════════════════════════════════════════════════════════
# FSM States
# ═══════════════════════════════════════════════════════════

class AdminState(StatesGroup):
    add_specialist_id = State()
    add_specialist_name = State()
    add_specialist_desc = State()
    add_specialist_photo = State()
    edit_specialist_name = State()
    edit_specialist_desc = State()
    edit_specialist_photo = State()
    add_time_slot = State()

# ═══════════════════════════════════════════════════════════
# Access Control
# ═══════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ═══════════════════════════════════════════════════════════
# Keyboards
# ═══════════════════════════════════════════════════════════

def admin_main_keyboard() -> InlineKeyboardMarkup:
    stats = db.get_stats()
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="━━━━━ 📊 СТАТИСТИКА ━━━━━", callback_data="ignore")],
        [
            InlineKeyboardButton(text=f"📅 Сегодня: {stats['today_bookings']}", callback_data="admin:bookings:today"),
            InlineKeyboardButton(text=f"📈 Всего: {stats['total_bookings']}", callback_data="admin:stats"),
        ],
        [InlineKeyboardButton(text="━━━━━ ⚙️ УПРАВЛЕНИЕ ━━━━━", callback_data="ignore")],
        [
            InlineKeyboardButton(text="👥 Специалисты", callback_data="admin:specialists"),
            InlineKeyboardButton(text="🕐 Слоты", callback_data="admin:slots"),
        ],
        [
            InlineKeyboardButton(text="📋 Записи", callback_data="admin:bookings"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats"),
        ],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin:close")],
    ])

def specialists_keyboard(show_all: bool = False) -> InlineKeyboardMarkup:
    specs = db.get_specialists(active_only=not show_all)
    buttons = []

    for spec in specs:
        status = "✅" if spec['is_active'] else "❌"
        photo = "📷" if spec.get('photo_file_id') else "📵"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {photo} {spec['name']}",
                callback_data=f"admin:spec:view:{spec['id']}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="➕ Добавить", callback_data="admin:spec:add"),
        InlineKeyboardButton(
            text="👁 Все" if not show_all else "✅ Активные",
            callback_data=f"admin:spec:list:{'0' if show_all else '1'}"
        ),
    ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def specialist_view_keyboard(spec_id: str) -> InlineKeyboardMarkup:
    spec = db.get_specialist(spec_id)
    toggle_text = "🔴 Выключить" if spec['is_active'] else "🟢 Включить"
    photo_text = "🖼 Изменить фото" if spec.get('photo_file_id') else "📷 Добавить фото"

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Имя", callback_data=f"admin:spec:edit:name:{spec_id}"),
            InlineKeyboardButton(text="📝 Описание", callback_data=f"admin:spec:edit:desc:{spec_id}"),
        ],
        [InlineKeyboardButton(text=photo_text, callback_data=f"admin:spec:edit:photo:{spec_id}")],
        [InlineKeyboardButton(text=toggle_text, callback_data=f"admin:spec:toggle:{spec_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"admin:spec:delete:{spec_id}")],
        [InlineKeyboardButton(text="◀️ К списку", callback_data="admin:specialists")],
    ])

def slots_keyboard() -> InlineKeyboardMarkup:
    slots = db.get_time_slots(active_only=False)
    buttons = []
    row = []

    for slot in slots:
        status = "✅" if slot['is_active'] else "❌"
        row.append(InlineKeyboardButton(
            text=f"{status} {slot['time']}",
            callback_data=f"admin:slot:toggle:{slot['id']}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="➕ Добавить слот", callback_data="admin:slot:add")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def bookings_filter_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Сегодня", callback_data="admin:bookings:today"),
            InlineKeyboardButton(text="📆 Завтра", callback_data="admin:bookings:tomorrow"),
        ],
        [
            InlineKeyboardButton(text="📅 Неделя", callback_data="admin:bookings:week"),
            InlineKeyboardButton(text="📋 Все", callback_data="admin:bookings:all"),
        ],
        [InlineKeyboardButton(text="❌ Отменённые", callback_data="admin:bookings:cancelled")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")],
    ])

def booking_view_keyboard(booking_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status == 'confirmed':
        buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin:booking:cancel:{booking_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ К записям", callback_data="admin:bookings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def confirm_delete_keyboard(spec_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"admin:spec:confirm_delete:{spec_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin:spec:view:{spec_id}"),
        ]
    ])

def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel_action")]
    ])

def skip_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="admin:spec:skip_photo")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel_action")]
    ])

# ═══════════════════════════════════════════════════════════
# Main Admin Panel
# ═══════════════════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    stats = db.get_stats()

    await message.answer(
        "🔐 <b>АДМИН-ПАНЕЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Специалистов: <b>{stats['active_specialists']}</b>\n"
        f"📅 Сегодня: <b>{stats['today_bookings']}</b>\n"
        f"📈 Предстоящих: <b>{stats['upcoming_bookings']}</b>\n"
        f"📊 Всего: <b>{stats['total_bookings']}</b>",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin:main")
async def admin_main(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    await state.clear()
    stats = db.get_stats()

    await callback.message.edit_text(
        "🔐 <b>АДМИН-ПАНЕЛЬ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Специалистов: <b>{stats['active_specialists']}</b>\n"
        f"📅 Сегодня: <b>{stats['today_bookings']}</b>\n"
        f"📈 Предстоящих: <b>{stats['upcoming_bookings']}</b>\n"
        f"📊 Всего: <b>{stats['total_bookings']}</b>",
        reply_markup=admin_main_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin:close")
async def admin_close(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.delete()

@router.callback_query(F.data == "admin:cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await admin_main(callback, state)

# ═══════════════════════════════════════════════════════════
# SPECIALISTS MANAGEMENT
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:specialists")
async def list_specialists(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "👥 <b>СПЕЦИАЛИСТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📷 — есть фото\n"
        "📵 — нет фото",
        reply_markup=specialists_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:spec:list:"))
async def list_specialists_filtered(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    show_all = callback.data.split(":")[-1] == "1"
    await callback.message.edit_reply_markup(reply_markup=specialists_keyboard(show_all))

@router.callback_query(F.data.startswith("admin:spec:view:"))
async def view_specialist(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    spec_id = callback.data.split(":")[-1]
    spec = db.get_specialist(spec_id)

    if not spec:
        await callback.answer("Специалист не найден", show_alert=True)
        return

    status = "🟢 Активен" if spec['is_active'] else "🔴 Выключен"
    photo_status = "✅ Загружено" if spec.get('photo_file_id') else "❌ Нет фото"

    await callback.message.edit_text(
        f"👤 <b>{spec['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 ID: <code>{spec['id']}</code>\n"
        f"📊 Статус: {status}\n"
        f"🖼 Фото: {photo_status}\n\n"
        f"📝 <b>Описание:</b>\n{spec['description'] or '—'}",
        reply_markup=specialist_view_keyboard(spec_id),
        parse_mode="HTML"
    )

# ═══════════════════════════════════════════════════════════
# ADD SPECIALIST
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:spec:add")
async def add_specialist_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminState.add_specialist_id)
    await callback.message.edit_text(
        "➕ <b>НОВЫЙ СПЕЦИАЛИСТ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Шаг 1/4: Введите <b>ID</b>\n"
        "<i>(латиница, без пробелов)</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminState.add_specialist_id)
async def add_specialist_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    spec_id = message.text.strip().lower().replace(" ", "_")

    if db.get_specialist(spec_id):
        await message.answer("❌ Такой ID уже есть. Введите другой:")
        return

    await state.update_data(new_spec_id=spec_id)
    await state.set_state(AdminState.add_specialist_name)
    await message.answer(
        f"✅ ID: <code>{spec_id}</code>\n\n"
        "Шаг 2/4: Введите <b>имя</b>:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminState.add_specialist_name)
async def add_specialist_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.update_data(new_spec_name=message.text.strip())
    await state.set_state(AdminState.add_specialist_desc)
    await message.answer(
        "Шаг 3/4: Введите <b>описание</b>\n\n"
        "<i>Можно использовать эмодзи и переносы строк.\n"
        "Отправьте <b>-</b> чтобы пропустить.</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminState.add_specialist_desc)
async def add_specialist_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    desc = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(new_spec_desc=desc)
    await state.set_state(AdminState.add_specialist_photo)
    
    await message.answer(
        "Шаг 4/4: Отправьте <b>фото</b> специалиста\n\n"
        "<i>Или нажмите «Пропустить»</i>",
        reply_markup=skip_photo_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminState.add_specialist_photo, F.photo)
async def add_specialist_photo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    photo_file_id = message.photo[-1].file_id
    data = await state.get_data()

    db.add_specialist(
        data['new_spec_id'],
        data['new_spec_name'],
        data.get('new_spec_desc', ''),
        photo_file_id
    )
    await state.clear()

    await message.answer(
        f"✅ <b>Специалист добавлен!</b>\n\n"
        f"👤 {data['new_spec_name']}\n"
        f"🖼 Фото загружено",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 К специалистам", callback_data="admin:specialists")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="admin:main")],
        ]),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin:spec:skip_photo")
async def skip_photo(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    data = await state.get_data()
    
    db.add_specialist(
        data['new_spec_id'],
        data['new_spec_name'],
        data.get('new_spec_desc', '')
    )
    await state.clear()

    await callback.message.edit_text(
        f"✅ <b>Специалист добавлен!</b>\n\n"
        f"👤 {data['new_spec_name']}\n"
        f"🖼 Без фото",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👥 К специалистам", callback_data="admin:specialists")],
            [InlineKeyboardButton(text="🏠 Главная", callback_data="admin:main")],
        ]),
        parse_mode="HTML"
    )

# ═══════════════════════════════════════════════════════════
# EDIT SPECIALIST
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:spec:edit:name:"))
async def edit_name_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    spec_id = callback.data.split(":")[-1]
    spec = db.get_specialist(spec_id)
    
    await state.update_data(edit_spec_id=spec_id)
    await state.set_state(AdminState.edit_specialist_name)

    await callback.message.edit_text(
        f"✏️ <b>РЕДАКТИРОВАНИЕ ИМЕНИ</b>\n\n"
        f"Текущее: <b>{spec['name']}</b>\n\n"
        f"Введите новое имя:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminState.edit_specialist_name)
async def edit_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    db.update_specialist(data['edit_spec_id'], name=message.text.strip())
    await state.clear()

    await message.answer(
        "✅ Имя обновлено!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К специалисту", callback_data=f"admin:spec:view:{data['edit_spec_id']}")],
        ])
    )

@router.callback_query(F.data.startswith("admin:spec:edit:desc:"))
async def edit_desc_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    spec_id = callback.data.split(":")[-1]
    spec = db.get_specialist(spec_id)
    
    await state.update_data(edit_spec_id=spec_id)
    await state.set_state(AdminState.edit_specialist_desc)

    await callback.message.edit_text(
        f"📝 <b>РЕДАКТИРОВАНИЕ ОПИСАНИЯ</b>\n\n"
        f"Текущее:\n{spec['description'] or '—'}\n\n"
        f"Введите новое (<b>-</b> чтобы очистить):",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminState.edit_specialist_desc)
async def edit_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    desc = "" if message.text.strip() == "-" else message.text.strip()
    db.update_specialist(data['edit_spec_id'], description=desc)
    await state.clear()

    await message.answer(
        "✅ Описание обновлено!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К специалисту", callback_data=f"admin:spec:view:{data['edit_spec_id']}")],
        ])
    )

@router.callback_query(F.data.startswith("admin:spec:edit:photo:"))
async def edit_photo_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    spec_id = callback.data.split(":")[-1]
    await state.update_data(edit_spec_id=spec_id)
    await state.set_state(AdminState.edit_specialist_photo)

    await callback.message.edit_text(
        "🖼 <b>ЗАГРУЗКА ФОТО</b>\n\n"
        "Отправьте новое фото специалиста:",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminState.edit_specialist_photo, F.photo)
async def edit_photo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    photo_file_id = message.photo[-1].file_id
    db.update_specialist_photo(data['edit_spec_id'], photo_file_id)
    await state.clear()

    await message.answer(
        "✅ Фото обновлено!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ К специалисту", callback_data=f"admin:spec:view:{data['edit_spec_id']}")],
        ])
    )

# ═══════════════════════════════════════════════════════════
# TOGGLE & DELETE SPECIALIST
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("admin:spec:toggle:"))
async def toggle_specialist(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    spec_id = callback.data.split(":")[-1]
    db.toggle_specialist(spec_id)
    spec = db.get_specialist(spec_id)
    status = "включён ✅" if spec['is_active'] else "выключен 🔴"
    await callback.answer(f"Специалист {status}")
    await view_specialist(callback)

@router.callback_query(F.data.startswith("admin:spec:delete:"))
async def delete_confirm(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    spec_id = callback.data.split(":")[-1]
    spec = db.get_specialist(spec_id)

    await callback.message.edit_text(
        f"⚠️ <b>УДАЛЕНИЕ</b>\n\n"
        f"Удалить <b>{spec['name']}</b>?\n"
        f"Это действие нельзя отменить!",
        reply_markup=confirm_delete_keyboard(spec_id),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:spec:confirm_delete:"))
async def delete_specialist(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    spec_id = callback.data.split(":")[-1]
    db.delete_specialist(spec_id)
    await callback.answer("✅ Удалено")
    await list_specialists(callback)

# ═══════════════════════════════════════════════════════════
# TIME SLOTS
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:slots")
async def list_slots(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "🕐 <b>ВРЕМЕННЫЕ СЛОТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Нажмите чтобы вкл/выкл:",
        reply_markup=slots_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:slot:toggle:"))
async def toggle_slot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    slot_id = int(callback.data.split(":")[-1])
    db.toggle_time_slot(slot_id)
    await callback.message.edit_reply_markup(reply_markup=slots_keyboard())
    await callback.answer("✅ Обновлено")

@router.callback_query(F.data == "admin:slot:add")
async def add_slot_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminState.add_time_slot)
    await callback.message.edit_text(
        "➕ <b>НОВЫЙ СЛОТ</b>\n\n"
        "Введите время <b>ЧЧ:ММ</b>\n"
        "<i>(например: 13:00)</i>",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )

@router.message(AdminState.add_time_slot)
async def add_slot(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    time_str = message.text.strip()

    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("❌ Формат: ЧЧ:ММ (например: 14:30)")
        return

    if db.add_time_slot(time_str):
        await state.clear()
        await message.answer(
            f"✅ Слот <b>{time_str}</b> добавлен!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🕐 К слотам", callback_data="admin:slots")],
            ]),
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Такой слот уже есть")

# ═══════════════════════════════════════════════════════════
# BOOKINGS
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:bookings")
async def bookings_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "📋 <b>ЗАПИСИ</b>\n\n"
        "Выберите период:",
        reply_markup=bookings_filter_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:bookings:"))
async def list_bookings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    filter_type = callback.data.split(":")[-1]

    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    week_end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    if filter_type == "today":
        bookings = db.get_bookings(date_from=today, date_to=today)
        title = "📅 СЕГОДНЯ"
    elif filter_type == "tomorrow":
        bookings = db.get_bookings(date_from=tomorrow, date_to=tomorrow)
        title = "📆 ЗАВТРА"
    elif filter_type == "week":
        bookings = db.get_bookings(date_from=today, date_to=week_end)
        title = "📅 НЕДЕЛЯ"
    elif filter_type == "cancelled":
        bookings = db.get_bookings(status='cancelled')
        title = "❌ ОТМЕНЁННЫЕ"
    else:
        bookings = db.get_bookings(date_from=today)
        title = "📋 ВСЕ"

    if not bookings:
        text = f"<b>{title}</b>\n\nЗаписей нет"
    else:
        text = f"<b>{title}</b>\n\n"
        for b in bookings[:10]:
            date = datetime.strptime(b['date'], "%Y-%m-%d").strftime("%d.%m")
            icon = "🚨" if b.get('booking_type', '').startswith('urgent') else "📅"
            text += f"{icon} <b>{date} {b['time']}</b> — {b['specialist_name']}\n"
            text += f"    👤 {b['client_name']}\n"

    buttons = []
    if bookings:
        for b in bookings[:3]:
            buttons.append([InlineKeyboardButton(
                text=f"📋 {b['client_name'][:20]}",
                callback_data=f"admin:booking:view:{b['id']}"
            )])

    buttons.append([InlineKeyboardButton(text="🔄 Обновить", callback_data=f"admin:bookings:{filter_type}")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin:bookings")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@router.callback_query(F.data.startswith("admin:booking:view:"))
async def view_booking(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    booking_id = int(callback.data.split(":")[-1])
    b = db.get_booking(booking_id)

    if not b:
        await callback.answer("Не найдено", show_alert=True)
        return

    date = datetime.strptime(b['date'], "%Y-%m-%d").strftime("%d.%m.%Y")
    status_text = "✅ Подтверждена" if b['status'] == 'confirmed' else "❌ Отменена"
    
    type_text = {
        'urgent_15': '🚨 Срочно (15 мин)',
        'urgent_60': '⏰ В течение часа',
        'scheduled': '📅 По записи'
    }.get(b.get('booking_type', 'scheduled'), '📅 По записи')

    await callback.message.edit_text(
        f"📋 <b>ЗАПИСЬ #{b['id']}</b>\n\n"
        f"📌 Тип: {type_text}\n"
        f"👤 Специалист: <b>{b['specialist_name']}</b>\n"
        f"📅 Дата: {date}\n"
        f"🕐 Время: {b['time']}\n\n"
        f"👤 Клиент: <b>{b['client_name']}</b>\n"
        f"📱 Телефон: <code>{b['client_phone']}</code>\n"
        f"🆔 @{b['client_username'] or '—'}\n\n"
        f"📊 Статус: {status_text}",
        reply_markup=booking_view_keyboard(booking_id, b['status']),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin:booking:cancel:"))
async def cancel_booking(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    booking_id = int(callback.data.split(":")[-1])
    db.cancel_booking(booking_id)
    await callback.answer("✅ Отменено")
    await view_booking(callback)

# ═══════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════

@router.callback_query(F.data == "admin:stats")
async def show_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    stats = db.get_stats()

    await callback.message.edit_text(
        "📊 <b>СТАТИСТИКА</b>\n\n"
        f"👥 Специалистов: <b>{stats['active_specialists']}</b>\n\n"
        f"📅 Сегодня: <b>{stats['today_bookings']}</b>\n"
        f"📈 Предстоящих: <b>{stats['upcoming_bookings']}</b>\n"
        f"📊 Всего: <b>{stats['total_bookings']}</b>\n"
        f"❌ Отменённых: <b>{stats['cancelled_bookings']}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:stats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin:main")],
        ]),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()
