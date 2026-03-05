import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tg_bot.database.models import Category, FreeCatalog, FreeFile, Settings, DeepLink, BotText
from tg_bot.keyboards.inline import get_admin_main_kb, get_settings_kb, get_admin_del_cats_kb, get_admin_texts_kb

admin_router = Router()

class AdminStates(StatesGroup):
    add_cat_name = State()
    add_cat_link_paid = State()
    
    add_free_select_cat = State()
    add_free_name = State()
    add_free_files = State()
    
    # Загрузка в существующие
    upload_sel_cat = State()
    upload_sel_sub = State()
    upload_files = State()
    
    # Персонализация (Deep Links)
    add_link_slug = State()
    add_link_text = State()
    add_link_cat_select = State()
    add_link_free_select = State()
    
    # Настройки
    set_price_single = State()
    set_price_full = State()
    set_price_select = State()
    set_link_full = State()
    
    # Редактирование текстов
    edit_text_input = State()

async def get_settings(session: AsyncSession) -> Settings:
    settings = (await session.execute(select(Settings).where(Settings.id == 1))).scalar_one_or_none()
    if not settings:
        settings = Settings(id=1)
        session.add(settings)
        await session.flush()
    return settings

@admin_router.message(Command("admin"))
async def admin_start(message: Message):
    admin_ids = os.getenv("ADMIN_IDS", "").split(",")
    if str(message.from_user.id) not in admin_ids:
        return
    await message.answer("🛠 <b>Панель управления</b>", reply_markup=get_admin_main_kb())

@admin_router.callback_query(F.data == "adm_cancel")
async def adm_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛠 <b>Панель управления</b>", reply_markup=get_admin_main_kb())

# === РЕДАКТОР ТЕКСТОВ ===
@admin_router.callback_query(F.data == "adm_texts")
async def adm_texts_list(callback: CallbackQuery, session: AsyncSession):
    texts = (await session.execute(select(BotText))).scalars().all()
    if not texts:
        return await callback.answer("Тексты еще не инициализированы. Нажмите /start в боте 1 раз.", show_alert=True)
    
    # Создаем клавиатуру с кнопками по одной в ряд
    buttons = []
    for text in texts:
        buttons.append([InlineKeyboardButton(text=f"📝 {text.description}", callback_data=f"edit_text:{text.key}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="adm_cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text("📝 <b>Выберите текст для редактирования:</b>", reply_markup=kb)

@admin_router.callback_query(F.data.startswith("edit_text:"))
async def adm_texts_edit(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    key = callback.data.split(":")[1]
    text_obj = await session.get(BotText, key)
    
    if not text_obj:
        return await callback.answer("Текст не найден", show_alert=True)
    
    await state.update_data(text_key=key)
    await state.set_state(AdminStates.edit_text_input)
    
    msg = (f"📝 <b>Редактирование:</b> {text_obj.description}\n\n"
           f"<b>Текущий текст:</b>\n{text_obj.text}\n\n"
           f"👇 <i>Отправьте новый текст (поддерживает HTML-теги):</i>")
    await callback.message.edit_text(msg)

@admin_router.message(AdminStates.edit_text_input)
async def adm_texts_save(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    text_obj = await session.get(BotText, data['text_key'])
    
    if text_obj:
        text_obj.text = message.html_text  # Сохраняем с HTML форматированием
        await session.commit()
        await message.answer("✅ Текст успешно обновлен!", reply_markup=get_admin_main_kb())
    else:
        await message.answer("❌ Ошибка: текст не найден", reply_markup=get_admin_main_kb())
    
    await state.clear()

# === ЗАГРУЗКА ФАЙЛОВ В СУЩЕСТВУЮЩИЕ ===
@admin_router.callback_query(F.data == "adm_upload_files")
async def adm_up_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    cats = (await session.execute(select(Category))).scalars().all()
    if not cats:
        return await callback.answer("Категорий нет", show_alert=True)
    
    # Создаем клавиатуру с кнопками по одной в ряд
    buttons = []
    for c in cats:
        buttons.append([InlineKeyboardButton(text=f"📂 {c.name}", callback_data=f"up_c:{c.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="adm_cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text("📂 Выберите категорию, где лежит подкатегория:", reply_markup=kb)
    await state.set_state(AdminStates.upload_sel_cat)

@admin_router.callback_query(AdminStates.upload_sel_cat, F.data.startswith("up_c:"))
async def adm_up_sel_cat(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    cat_id = int(callback.data.split(":")[1])
    subs = (await session.execute(select(FreeCatalog).where(FreeCatalog.category_id == cat_id))).scalars().all()
    
    if not subs:
        return await callback.answer("В этой категории нет подкатегорий", show_alert=True)
    
    # Создаем клавиатуру с кнопками по одной в ряд
    buttons = []
    for s in subs:
        buttons.append([InlineKeyboardButton(text=f"📁 {s.name}", callback_data=f"up_s:{s.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="adm_cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text("📂 Выберите подкатегорию для загрузки файлов:", reply_markup=kb)
    await state.set_state(AdminStates.upload_sel_sub)

@admin_router.callback_query(AdminStates.upload_sel_sub, F.data.startswith("up_s:"))
async def adm_up_sel_sub(callback: CallbackQuery, state: FSMContext):
    sub_id = int(callback.data.split(":")[1])
    await state.update_data(sub_id=sub_id, files=[])
    await state.set_state(AdminStates.upload_files)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить загрузку", callback_data="up_finish")]
    ])
    await callback.message.edit_text("📎 Присылайте PDF-файлы по очереди. Как закончите — жмите кнопку.", reply_markup=kb)

@admin_router.message(AdminStates.upload_files, F.document)
async def adm_up_receive(message: Message, state: FSMContext):
    data = await state.get_data()
    files = data.get('files', [])
    files.append(message.document.file_id)
    await state.update_data(files=files)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить загрузку", callback_data="up_finish")]
    ])
    await message.answer(f"📥 Файл принят! (Всего: {len(files)})", reply_markup=kb)

@admin_router.callback_query(AdminStates.upload_files, F.data == "up_finish")
async def adm_up_finish(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    files = data.get('files', [])
    if not files:
        return await callback.answer("Вы ничего не загрузили!", show_alert=True)
    
    sub_id = data['sub_id']
    for f_id in files:
        session.add(FreeFile(free_catalog_id=sub_id, file_id=f_id))
    
    await session.commit()
    await callback.message.edit_text(f"✅ Успешно добавлено {len(files)} файлов!", reply_markup=get_admin_main_kb())
    await state.clear()

# --- СОЗДАНИЕ ССЫЛКИ ДЛЯ REELS ---
@admin_router.callback_query(F.data == "adm_add_link")
async def adm_link_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_link_slug)
    await callback.message.answer("🔗 Введите 'Slug' (хвостик ссылки, например: <code>divan</code>):")
    await callback.answer()

@admin_router.message(AdminStates.add_link_slug)
async def adm_link_slug(message: Message, state: FSMContext, session: AsyncSession):
    res = await session.execute(select(DeepLink).where(DeepLink.slug == message.text))
    if res.scalar_one_or_none():
        return await message.answer("❌ Такой Slug уже занят. Придумайте другой:")
    
    await state.update_data(slug=message.text)
    await state.set_state(AdminStates.add_link_text)
    await message.answer("📝 Введите приветственный текст:")

@admin_router.message(AdminStates.add_link_text)
async def adm_link_text(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(text=message.text)
    cats = (await session.execute(select(Category))).scalars().all()
    if not cats:
        return await message.answer("❌ Нет категорий.")
    
    # Создаем клавиатуру с кнопками по одной в ряд
    buttons = []
    for c in cats:
        buttons.append([InlineKeyboardButton(text=f"📂 {c.name}", callback_data=f"lnk_c:{c.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="adm_cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer("📂 В какой категории лежит нужный бесплатный файл?", reply_markup=kb)
    await state.set_state(AdminStates.add_link_cat_select)

@admin_router.callback_query(AdminStates.add_link_cat_select, F.data.startswith("lnk_c:"))
async def adm_link_sel_cat(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    cat_id = int(callback.data.split(":")[1])
    frees = (await session.execute(select(FreeCatalog).where(FreeCatalog.category_id == cat_id))).scalars().all()
    if not frees:
        return await callback.answer("Здесь нет файлов", show_alert=True)
    
    # Создаем клавиатуру с кнопками по одной в ряд
    buttons = []
    for f in frees:
        buttons.append([InlineKeyboardButton(text=f"📄 {f.name}", callback_data=f"lnk_f:{f.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="adm_cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text("📄 Выберите конкретный файл:", reply_markup=kb)
    await state.set_state(AdminStates.add_link_free_select)

@admin_router.callback_query(AdminStates.add_link_free_select, F.data.startswith("lnk_f:"))
async def adm_link_final(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    free_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    bot_info = await callback.bot.get_me()
    
    session.add(DeepLink(slug=data['slug'], custom_text=data['text'], free_catalog_id=free_id))
    await session.commit()
    
    full_url = f"https://t.me/{bot_info.username}?start={data['slug']}"
    await callback.message.edit_text(
        f"✅ <b>Персональная ссылка создана!</b>\n\n"
        f"🔗 URL: <code>{full_url}</code>\n\n"
        f"Логика перехода:\n"
        f"1. Приветствие\n"
        f"2. Кнопка «Скачать {data['slug']}»\n"
        f"3. Кнопка «Купить категорию»\n"
        f"4. Кнопка «Купить всё»",
        reply_markup=get_admin_main_kb()
    )
    await state.clear()

# --- ДОБАВЛЕНИЕ КАТЕГОРИИ ---
@admin_router.callback_query(F.data == "adm_add_cat")
async def adm_add_cat(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_cat_name)
    await callback.message.answer("📝 Введите название категории:")

@admin_router.message(AdminStates.add_cat_name)
async def adm_cat_step2(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.add_cat_link_paid)
    await message.answer("🔗 Вставьте ссылку на ПЛАТНЫЙ каталог:")

@admin_router.message(AdminStates.add_cat_link_paid)
async def adm_cat_final(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    session.add(Category(name=data['name'], link_paid=message.text))
    await session.commit()
    await message.answer("✅ Категория создана!", reply_markup=get_admin_main_kb())
    await state.clear()

# --- ДОБАВЛЕНИЕ БЕСПЛАТНЫХ КАТАЛОГОВ (НОВЫХ) ---
@admin_router.callback_query(F.data == "adm_add_free")
async def adm_add_free_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    cats = (await session.execute(select(Category))).scalars().all()
    if not cats:
        return await callback.answer("Нет категорий", show_alert=True)
    
    # Создаем клавиатуру с кнопками по одной в ряд
    buttons = []
    for c in cats:
        buttons.append([InlineKeyboardButton(text=f"📂 {c.name}", callback_data=f"adm_sel_cat:{c.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="adm_cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text("📁 Выберите Категорию:", reply_markup=kb)
    await state.set_state(AdminStates.add_free_select_cat)

@admin_router.callback_query(AdminStates.add_free_select_cat, F.data.startswith("adm_sel_cat:"))
async def adm_free_step2(callback: CallbackQuery, state: FSMContext):
    await state.update_data(cat_id=int(callback.data.split(":")[1]))
    await state.set_state(AdminStates.add_free_name)
    await callback.message.edit_text("📝 Название подкатегории:")

@admin_router.message(AdminStates.add_free_name)
async def adm_free_step3(message: Message, state: FSMContext):
    await state.update_data(name=message.text, files=[])
    await state.set_state(AdminStates.add_free_files)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить", callback_data="adm_free_finish")]
    ])
    await message.answer("📎 Пришлите PDF файлы:", reply_markup=kb)

@admin_router.message(AdminStates.add_free_files, F.document)
async def adm_free_receive_file(message: Message, state: FSMContext):
    data = await state.get_data()
    files = data.get('files', [])
    files.append(message.document.file_id)
    await state.update_data(files=files)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Завершить", callback_data="adm_free_finish")]
    ])
    await message.answer(f"📥 Принят (Всего: {len(files)})", reply_markup=kb)

@admin_router.callback_query(AdminStates.add_free_files, F.data == "adm_free_finish")
async def adm_free_finish(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    files = data.get('files', [])
    
    # Создаем бесплатный каталог даже если нет файлов
    free_cat = FreeCatalog(category_id=data['cat_id'], name=data['name'])
    session.add(free_cat)
    await session.flush()
    
    for f_id in files:
        session.add(FreeFile(free_catalog_id=free_cat.id, file_id=f_id))
    
    await session.commit()
    await callback.message.edit_text("✅ Готово!", reply_markup=get_admin_main_kb())
    await state.clear()

# --- НАСТРОЙКИ ---
@admin_router.callback_query(F.data == "adm_settings")
async def adm_settings(callback: CallbackQuery, session: AsyncSession):
    s = await get_settings(session)
    text = (f"⚙️ <b>Настройки:</b>\n"
            f"1 комната: {s.price_single}₽\n"
            f"Квартира: {s.price_full}₽\n"
            f"Подбор: {s.price_select}₽\n"
            f"Ссылка: {s.link_full}")
    await callback.message.edit_text(text, reply_markup=get_settings_kb(), disable_web_page_preview=True)

@admin_router.callback_query(F.data.in_({"set_price_single", "set_price_full", "set_price_select", "set_link_full"}))
async def adm_set_param(callback: CallbackQuery, state: FSMContext):
    action = callback.data
    states = {
        "set_price_single": AdminStates.set_price_single,
        "set_price_full": AdminStates.set_price_full,
        "set_price_select": AdminStates.set_price_select,
        "set_link_full": AdminStates.set_link_full
    }
    await state.set_state(states[action])
    await callback.message.answer("Новое значение:")

@admin_router.message(AdminStates.set_price_single)
async def save_ps(m: Message, state: FSMContext, session: AsyncSession):
    settings = await get_settings(session)
    settings.price_single = int(m.text)
    await session.commit()
    await m.answer("✅ Сохранено!", reply_markup=get_admin_main_kb())
    await state.clear()

@admin_router.message(AdminStates.set_price_full)
async def save_pf(m: Message, state: FSMContext, session: AsyncSession):
    settings = await get_settings(session)
    settings.price_full = int(m.text)
    await session.commit()
    await m.answer("✅ Сохранено!", reply_markup=get_admin_main_kb())
    await state.clear()

@admin_router.message(AdminStates.set_price_select)
async def save_pselect(m: Message, state: FSMContext, session: AsyncSession):
    settings = await get_settings(session)
    settings.price_select = int(m.text)
    await session.commit()
    await m.answer("✅ Сохранено!", reply_markup=get_admin_main_kb())
    await state.clear()

@admin_router.message(AdminStates.set_link_full)
async def save_lf(m: Message, state: FSMContext, session: AsyncSession):
    settings = await get_settings(session)
    settings.link_full = m.text
    await session.commit()
    await m.answer("✅ Сохранено!", reply_markup=get_admin_main_kb())
    await state.clear()

# --- УДАЛЕНИЕ ---
@admin_router.callback_query(F.data == "adm_del_cat_list")
async def adm_del_cats(callback: CallbackQuery, session: AsyncSession):
    cats = (await session.execute(select(Category))).scalars().all()
    await callback.message.edit_text("🗑 <b>Выберите категорию для удаления:</b>", reply_markup=get_admin_del_cats_kb(cats))

@admin_router.callback_query(F.data.startswith("adm_del_confirm:"))
async def process_del_cat(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    cat_id = int(callback.data.split(":")[1])
    cat = await session.get(Category, cat_id)
    if cat:
        await session.delete(cat)
        await session.commit()
        await callback.answer("✅ Категория удалена", show_alert=True)
    else:
        await callback.answer("❌ Категория не найдена", show_alert=True)
    await adm_cancel(callback, state)

@admin_router.callback_query(F.data == "adm_del_free_list")
async def adm_del_frees(callback: CallbackQuery, session: AsyncSession):
    frees = (await session.execute(
        select(FreeCatalog).options(selectinload(FreeCatalog.category))
    )).scalars().all()
    await callback.message.edit_text("🗑 <b>Выберите бесплатный каталог для удаления:</b>", reply_markup=get_admin_del_cats_kb(frees, is_free=True))

@admin_router.callback_query(F.data.startswith("adm_delfree:"))
async def process_del_free(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    free_id = int(callback.data.split(":")[1])
    free = await session.get(FreeCatalog, free_id)
    if free:
        await session.delete(free)
        await session.commit()
        await callback.answer("✅ Бесплатный каталог удален", show_alert=True)
    else:
        await callback.answer("❌ Каталог не найден", show_alert=True)
    await adm_cancel(callback, state)

# --- ДОПОЛНИТЕЛЬНЫЙ ФУНКЦИОНАЛ ---

# Просмотр всех deep link ссылок
@admin_router.callback_query(F.data == "adm_view_links")
async def adm_view_links(callback: CallbackQuery, session: AsyncSession):
    links = (await session.execute(
        select(DeepLink).options(selectinload(DeepLink.free_catalog))
    )).scalars().all()
    
    if not links:
        return await callback.answer("Нет созданных ссылок", show_alert=True)
    
    text = "🔗 <b>Созданные ссылки:</b>\n\n"
    for link in links:
        catalog_name = link.free_catalog.name if link.free_catalog else "Не указан"
        text += f"• /start {link.slug} → {catalog_name}\n"
    
    # Создаем клавиатуру с кнопками по одной в ряд
    buttons = []
    for link in links:
        buttons.append([InlineKeyboardButton(text=f"🔗 /start {link.slug}", callback_data=f"view_link:{link.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text(text, reply_markup=kb)

# Удаление deep link ссылки
@admin_router.callback_query(F.data == "adm_del_link")
async def adm_del_link_start(callback: CallbackQuery, session: AsyncSession):
    links = (await session.execute(select(DeepLink))).scalars().all()
    
    if not links:
        return await callback.answer("Нет ссылок для удаления", show_alert=True)
    
    # Создаем клавиатуру с кнопками по одной в ряд
    buttons = []
    for link in links:
        buttons.append([InlineKeyboardButton(text=f"❌ /start {link.slug}", callback_data=f"del_link:{link.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Отмена", callback_data="adm_cancel")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback.message.edit_text("🗑 <b>Выберите ссылку для удаления:</b>", reply_markup=kb)

@admin_router.callback_query(F.data.startswith("del_link:"))
async def adm_del_link_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    link_id = int(callback.data.split(":")[1])
    link = await session.get(DeepLink, link_id)
    
    if link:
        await session.delete(link)
        await session.commit()
        await callback.answer("✅ Ссылка удалена", show_alert=True)
    else:
        await callback.answer("❌ Ссылка не найдена", show_alert=True)
    
    await adm_cancel(callback, state)