import os
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, 
    InputMediaDocument, LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import CommandStart, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tg_bot.database.models import User, Category, FreeCatalog, Access, Settings, DeepLink, BotText
from tg_bot.keyboards.inline import (
    get_categories_kb, get_upsell_kb, get_free_categories_kb, 
    get_free_items_kb, get_deeplink_kb, get_info_kb, get_consultation_kb,
    get_cancel_form_kb
)
from tg_bot.services.bitrix import send_lead_to_bitrix

# =====================================================================
# FSM СОСТОЯНИЯ ДЛЯ ФОРМ
# =====================================================================
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class OrderSelectForm(StatesGroup):
    name = State()
    phone = State()
    request = State()

class ConsultForm(StatesGroup):
    name = State()
    phone = State()
    question = State()

start_router = Router()

# Тексты по умолчанию
DEFAULT_TEXTS = {
    "start": {"desc": "Приветствие (/start)", "text": "🎁 Бесплатные каталоги уже ждут вас 👇\n🔒 Полный каталог внутри"},
    "free_cats": {"desc": "Раздел 'Бесплатные каталоги'", "text": "🎁 <b>Бесплатные каталоги готовы</b>\n\nНиже вы можете выбрать комнату и скачать нужные файлы ⬇️"},
    "paid_single": {"desc": "Раздел 'По одной комнате'", "text": "🏠 <b>Каталог по одной комнате</b>\n\nВнутри одной комнаты:\n✔️ Более 20+ каталогов\n✔️ Все основные категории мебели\n✔️ Освещение и дополнительные элементы\n\n🛋 <i>Выберите комнату для покупки:</i>"},
    "paid_full": {"desc": "Раздел 'Вся квартира'", "text": "💎 <b>Полный комплект “Вся квартира”</b>\n\n✔️ Более 120+ каталогов\n✔️ Все комнаты\n✔️ Весь ассортимент в одном доступе\n✔️ НАВСЕГДА С ПОПОЛНЕНИЕМ"},
    "upsell": {"desc": "Допродажа (после покупки)", "text": "🎉 <b>Доступ открыт! Лови ссылку 👆</b>\n\nВы можете изучать каталоги и выбирать понравившиеся позиции.\nЕсли вы уже присмотрели конкретный товар, я могу сделать персональный подбор.\n\n⸻\n🛠 <b>Персональный подбор — {price} ₽ за 1 товар</b>\n\n<b>В услугу входит:</b>\n✔️ Связь с фабрикой\n✔️ Проверка наличия\n✔️ Расчёт итоговой стоимости “под ключ”\n\n<i>Оплата за подбор засчитывается в заказ.</i>"},
    "inv_desc_single": {"desc": "Чек: Описание 1 комнаты", "text": "Полная база проверенных фабрик и контактов."},
    "inv_desc_full": {"desc": "Чек: Описание всей квартиры", "text": "Полный комплект всех каталогов: гостиная, спальня, кухня и другие зоны. Навсегда."},
    "info": {"desc": "Раздел информации", "text": "<b>Информация о сервисе</b>\n\nЗдесь вы можете ознакомиться с правилами предоставления услуг или обратиться к нашему менеджеру."},
    "contact": {"desc": "Раздел 'Связаться со мной'", "text": "<b>Не знаете, с чего начать?</b>\n\nЯ работаю напрямую с фабриками в Китае.\n\nЕсли хотите узнать условия работы — нажмите кнопку ниже 👇"},
    "terms": {"desc": "Пользовательское соглашение", "text": "📜 <b>Пользовательское соглашение</b>\n\n1. Общие положения..."}
}

async def get_text(session: AsyncSession, key: str, **kwargs) -> str:
    obj = await session.get(BotText, key)
    if not obj:
        default = DEFAULT_TEXTS.get(key)
        if default:
            obj = BotText(key=key, description=default["desc"], text=default["text"])
            session.add(obj); await session.flush()
        else: return ""
    text = obj.text
    if kwargs:
        try: text = text.format(**kwargs)
        except: pass
    return text

async def get_settings(session: AsyncSession) -> Settings:
    settings = (await session.execute(select(Settings).where(Settings.id == 1))).scalar_one_or_none()
    if not settings:
        settings = Settings(id=1); session.add(settings); await session.flush()
    return settings

def get_main_menu(settings: Settings) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🔹 Бесплатные каталоги")],
        [KeyboardButton(text=f"🔹 Полный каталог по комнате — {settings.price_single} ₽")],
        [KeyboardButton(text=f"🔹 Каталог “Вся квартира” — {settings.price_full} ₽")],
        [KeyboardButton(text="💬 Связаться со мной"), KeyboardButton(text="📥 Мои покупки")],
        [KeyboardButton(text="ℹ️ Подробнее (Оферта и Поддержка)")]
    ], resize_keyboard=True)

# --- ГЛАВНЫЙ ВХОД И ПЕРСОНАЛИЗАЦИЯ ---
@start_router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, command: CommandObject):
    user_id = message.from_user.id
    user_stmt = select(User).where(User.user_id == user_id)
    if not (await session.execute(user_stmt)).scalar_one_or_none():
        session.add(User(user_id=user_id, username=message.from_user.username, full_name=message.from_user.full_name))
        await session.commit()
    
    settings = await get_settings(session)
    kb_main = get_main_menu(settings)

    if command.args:
        slug = command.args
        stmt = select(DeepLink).where(DeepLink.slug == slug).options(
            selectinload(DeepLink.free_catalog).selectinload(FreeCatalog.category)
        )
        link_obj = (await session.execute(stmt)).scalar_one_or_none()
        
        if link_obj and link_obj.free_catalog:
            free_cat = link_obj.free_catalog
            parent_cat = free_cat.category
            full_text = (f"👋 <b>Рада видеть вас!</b>\n\n{link_obj.custom_text}\n\n"
                         "🎁 Можно бесплатно скачать этот каталог\n🔒 Или открыть расширенный каталог\n"
                         "💎 Либо забрать все каталоги по квартире\n\n<b>Выберите вариант ниже 👇</b>")
            custom_kb = get_deeplink_kb(free_id=free_cat.id, free_name=free_cat.name, cat_id=parent_cat.id, cat_name=parent_cat.name, price_single=settings.price_single, price_full=settings.price_full)
            await message.answer(full_text, reply_markup=custom_kb)
            await message.answer("🔽 Или воспользуйтесь главным меню:", reply_markup=kb_main)
            return

    text = await get_text(session, "start")
    await message.answer(text, reply_markup=kb_main)

# --- ИНФОРМАЦИЯ И СВЯЗЬ ---
@start_router.message(F.text == "ℹ️ Подробнее (Оферта и Поддержка)")
async def show_info(message: Message, session: AsyncSession):
    text = await get_text(session, "info"); await message.answer(text, reply_markup=get_info_kb())

@start_router.callback_query(F.data == "show_terms")
async def show_terms(callback: CallbackQuery, session: AsyncSession):
    terms_text = await get_text(session, "terms"); await callback.message.answer(terms_text); await callback.answer()

@start_router.message(F.text == "💬 Связаться со мной")
async def contact_me_start(message: Message, session: AsyncSession):
    text = await get_text(session, "contact"); await message.answer(text, reply_markup=get_consultation_kb())

# --- БЕСПЛАТНЫЕ КАТАЛОГИ ---
@start_router.message(F.text == "🔹 Бесплатные каталоги")
@start_router.callback_query(F.data == "back_to_free_cats")
async def show_free_cats(event, session: AsyncSession):
    stmt = select(Category).join(FreeCatalog).distinct()
    cats = (await session.execute(stmt)).scalars().all()
    if not cats:
        msg = "Бесплатных каталогов пока нет."; return await event.answer(msg) if isinstance(event, Message) else await event.message.edit_text(msg)
    settings = await get_settings(session)
    text = await get_text(session, "free_cats", price_single=settings.price_single, price_full=settings.price_full)
    kb = get_free_categories_kb(cats)
    if isinstance(event, Message): await event.answer(text, reply_markup=kb)
    else: await event.message.edit_text(text, reply_markup=kb)

@start_router.callback_query(F.data.startswith("free_cat:"))
async def show_free_items(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split(":")[1])
    frees = (await session.execute(select(FreeCatalog).where(FreeCatalog.category_id == cat_id))).scalars().all()
    if not frees: return await callback.answer("Здесь пока нет файлов.", show_alert=True)
    await callback.message.edit_text("🎁 <b>Выберите подборку:</b>", reply_markup=get_free_items_kb(frees))

@start_router.callback_query(F.data.startswith("get_free:"))
async def give_free_files(callback: CallbackQuery, session: AsyncSession):
    free_id = int(callback.data.split(":")[1])
    free_cat = (await session.execute(select(FreeCatalog).where(FreeCatalog.id == free_id).options(selectinload(FreeCatalog.files)))).scalar_one_or_none()
    if not free_cat or not free_cat.files: return await callback.answer("Файлы не найдены.", show_alert=True)
    
    caption = f"🎁 <b>Ваш бесплатный каталог: {free_cat.name}</b>\n\nПриятного просмотра!"
    if len(free_cat.files) == 1: await callback.message.answer_document(document=free_cat.files[0].file_id, caption=caption)
    else:
        await callback.message.answer(caption)
        await callback.message.answer_media_group(media=[InputMediaDocument(media=f.file_id) for f in free_cat.files[:10]])
    await callback.answer()

# --- ПОКУПКА ---
@start_router.message(F.text.startswith("🔹 Полный каталог по комнате"))
async def show_paid_rooms(message: Message, session: AsyncSession):
    cats = (await session.execute(select(Category))).scalars().all()
    text = await get_text(session, "paid_single"); await message.answer(text, reply_markup=get_categories_kb(cats))

@start_router.callback_query(F.data.startswith("buy_cat:"))
async def send_invoice_single(callback: CallbackQuery, session: AsyncSession):
    cat_id = int(callback.data.split(":")[1])
    cat = await session.get(Category, cat_id)
    settings = await get_settings(session)
    desc = await get_text(session, "inv_desc_single")
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id, title=f"Каталог: {cat.name}", description=desc, payload=f"buy_cat:{cat.id}",
        provider_token=os.getenv("PAYMENT_TOKEN"), currency="RUB", prices=[LabeledPrice(label="К оплате", amount=settings.price_single * 100)]
    ); await callback.answer()

@start_router.message(F.text.startswith("🔹 Каталог “Вся квартира”"))
@start_router.callback_query(F.data == "buy_full")
async def send_invoice_full(event, session: AsyncSession):
    settings = await get_settings(session)
    message = event if isinstance(event, Message) else event.message
    text = await get_text(session, "paid_full"); desc = await get_text(session, "inv_desc_full")
    if isinstance(event, Message): await message.answer(text)
    await message.bot.send_invoice(
        chat_id=message.chat.id, title="Каталог «Вся квартира»", description=desc, payload="buy_full",
        provider_token=os.getenv("PAYMENT_TOKEN"), currency="RUB", prices=[LabeledPrice(label="К оплате", amount=settings.price_full * 100)]
    )
    if isinstance(event, CallbackQuery): await event.answer()

# --- ПЛАТЕЖИ ---
@start_router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@start_router.message(F.successful_payment)
async def process_successful_payment(message: Message, session: AsyncSession):
    payload = message.successful_payment.invoice_payload
    settings = await get_settings(session)
    
    if payload.startswith("buy_cat:"):
        cat_id = int(payload.split(":")[1])
        cat = await session.get(Category, cat_id)
        session.add(Access(user_id=message.from_user.id, category_id=cat.id, catalog_type="single"))
        await message.answer(f"✅ Оплата прошла!\n🔗 <b>Ваш каталог «{cat.name}»:</b>\n{cat.link_paid}")
    elif payload == "buy_full":
        session.add(Access(user_id=message.from_user.id, catalog_type="full_collection"))
        await message.answer(f"✅ Оплата прошла!\n🔗 <b>Все каталоги здесь:</b>\n{settings.link_full}")
    elif payload == "buy_select":
        return await message.answer("✅ Оплата получена!")

    await session.commit()
    upsell_raw = await get_text(session, "upsell")
    upsell_text = upsell_raw.replace("{price}", str(settings.price_select))
    await message.answer(upsell_text, reply_markup=get_upsell_kb())

# --- МОИ ПОКУПКИ ---
@start_router.message(F.text == "📥 Мои покупки")
async def my_purchases(message: Message, session: AsyncSession):
    accesses = (await session.execute(select(Access).where(Access.user_id == message.from_user.id))).scalars().all()
    if not accesses: return await message.answer("У вас пока нет покупок.")
    if any(a.catalog_type == 'full_collection' for a in accesses):
        settings = await get_settings(session)
        return await message.answer(f"🌟 <b>У вас оплачен ПОЛНЫЙ ДОСТУП!</b>\n🔗 Ссылка: {settings.link_full}", disable_web_page_preview=True)
    text = "<b>Ваши покупки:</b>\n\n"
    for acc in accesses:
        if acc.category_id:
            cat = await session.get(Category, acc.category_id)
            if cat: text += f"✅ {cat.name}: <a href='{cat.link_paid}'>Открыть</a>\n"
    await message.answer(text, disable_web_page_preview=True)

# --- FSM ФОРМЫ (СОХРАНЕНО) ---
@start_router.callback_query(F.data == "cancel_form")
async def cancel_user_form(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.clear()
    settings = await get_settings(session)
    await callback.message.edit_text("❌ Действие отменено.", reply_markup=get_main_menu(settings))
    await callback.answer()

@start_router.callback_query(F.data == "form_order_select")
async def process_form_select(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderSelectForm.name)
    text = "📝 <b>Оформление заявки на подбор</b>\n\nКак к вам обращаться?"
    await callback.message.edit_text(text, reply_markup=get_cancel_form_kb())

@start_router.message(OrderSelectForm.name)
async def form_select_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text); await state.set_state(OrderSelectForm.phone)
    await message.answer("📱 Ваш номер телефона:", reply_markup=get_cancel_form_kb())

@start_router.message(OrderSelectForm.phone)
async def form_select_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text); await state.set_state(OrderSelectForm.request)
    await message.answer("🔗 Что нужно найти?", reply_markup=get_cancel_form_kb())

@start_router.message(OrderSelectForm.request)
async def form_select_finish(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await send_lead_to_bitrix(message.from_user.id, message.from_user.username, data.get('name'), f"🔥 ЗАЯВКА: {message.text}", data.get('phone'))
    await message.answer("✅ Заявка отправлена!"); await state.clear()

@start_router.callback_query(F.data == "form_consultation")
async def process_form_consult(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ConsultForm.name)
    await callback.message.edit_text("💬 <b>Консультация</b>\n\nКак к вам обращаться?", reply_markup=get_cancel_form_kb())

@start_router.message(ConsultForm.name)
async def form_consult_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text); await state.set_state(ConsultForm.phone)
    await message.answer("📱 Ваш номер телефона:", reply_markup=get_cancel_form_kb())

@start_router.message(ConsultForm.phone)
async def form_consult_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text); await state.set_state(ConsultForm.question)
    await message.answer("❓ Ваш вопрос:", reply_markup=get_cancel_form_kb())

@start_router.message(ConsultForm.question)
async def form_consult_finish(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await send_lead_to_bitrix(message.from_user.id, message.from_user.username, data.get('name'), f"💬 ВОПРОС: {message.text}", data.get('phone'))
    await message.answer("✅ Вопрос отправлен!"); await state.clear()