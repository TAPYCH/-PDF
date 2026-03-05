from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Ссылка на твоего ВТОРОГО бота (для обращений)
SUPPORT_BOT_URL = "https://t.me/bayer_obraschenia_bot"

# --- ПОЛЬЗОВАТЕЛЬСКИЕ КЛАВИАТУРЫ ---

def get_categories_kb(categories: list) -> InlineKeyboardMarkup:
    """Список категорий для покупки"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.add(InlineKeyboardButton(text=f"💳 {cat.name}", callback_data=f"buy_cat:{cat.id}"))
    builder.adjust(2)
    return builder.as_markup()

def get_free_categories_kb(categories: list) -> InlineKeyboardMarkup:
    """Список категорий для бесплатного просмотра"""
    builder = InlineKeyboardBuilder()
    for cat in categories:
        builder.add(InlineKeyboardButton(text=f"📂 {cat.name}", callback_data=f"free_cat:{cat.id}"))
    builder.adjust(2)
    return builder.as_markup()

def get_free_items_kb(free_catalogs: list) -> InlineKeyboardMarkup:
    """Список конкретных бесплатных файлов внутри категории"""
    builder = InlineKeyboardBuilder()
    for f in free_catalogs:
        builder.row(InlineKeyboardButton(text=f"🎁 {f.name}", callback_data=f"get_free:{f.id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к комнатам", callback_data="back_to_free_cats"))
    return builder.as_markup()

def get_deeplink_kb(free_id: int, free_name: str, cat_id: int, cat_name: str, price_single: int, price_full: int) -> InlineKeyboardMarkup:
    """Клавиатура для тех, кто пришел по персональной ссылке из Reels"""
    builder = InlineKeyboardBuilder()
    
    # 1. Кнопка скачивания того, за чем пришли
    builder.row(InlineKeyboardButton(text=f"🎁 Скачать бесплатно: {free_name}", callback_data=f"get_free:{free_id}"))
    
    # 2. Кнопка покупки всей комнаты (родительской категории)
    builder.row(InlineKeyboardButton(text=f"🏠 Полный каталог «{cat_name}» — {price_single}₽", callback_data=f"buy_cat:{cat_id}"))
    
    # 3. Кнопка купить всё
    builder.row(InlineKeyboardButton(text=f"💎 Все каталоги квартиры — {price_full}₽", callback_data="buy_full"))
    
    return builder.as_markup()

# --- ОБНОВЛЕННЫЕ КНОПКИ ПЕРЕХОДА ВО ВТОРОГО БОТА ---

def get_upsell_kb() -> InlineKeyboardMarkup:
    """Кнопка после покупки -> Ведет в личку ко второму боту с параметром start"""
    builder = InlineKeyboardBuilder()
    # ?start=podbor поможет менеджеру понять, что клиент пришел за подбором
    builder.row(InlineKeyboardButton(text="🟢 Заказать подбор (Чат с менеджером)", url=f"{SUPPORT_BOT_URL}?start=podbor"))
    return builder.as_markup()

def get_consultation_kb() -> InlineKeyboardMarkup:
    """Кнопка 'Связаться со мной' -> Ведет в личку ко второму боту"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💬 Написать менеджеру", url=f"{SUPPORT_BOT_URL}?start=consult"))
    return builder.as_markup()

def get_info_kb() -> InlineKeyboardMarkup:
    """Кнопка поддержки в разделе Инфо"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📜 Пользовательское соглашение", callback_data="show_terms"))
    builder.row(InlineKeyboardButton(text="💬 Написать в поддержку", url=SUPPORT_BOT_URL))
    return builder.as_markup()

# --- АДМИНСКИЕ КЛАВИАТУРЫ (ИСПРАВЛЕНЫ) ---

def get_admin_main_kb() -> InlineKeyboardMarkup:
    """Главное меню админки - каждая кнопка на отдельной строке"""
    builder = InlineKeyboardBuilder()
    
    # Каждая кнопка на отдельной строке через row
    builder.row(InlineKeyboardButton(text="📂 Залить файлы в подкатегорию", callback_data="adm_upload_files"))
    builder.row(InlineKeyboardButton(text="➕ Категория (платная)", callback_data="adm_add_cat"))
    builder.row(InlineKeyboardButton(text="🎁 Новая подкатегория", callback_data="adm_add_free"))
    builder.row(InlineKeyboardButton(text="🔗 Создать ссылку (Reels)", callback_data="adm_add_link"))
    builder.row(InlineKeyboardButton(text="📝 Тексты бота", callback_data="adm_texts"))
    builder.row(InlineKeyboardButton(text="👁 Просмотр ссылок", callback_data="adm_view_links"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить ссылку", callback_data="adm_del_link"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить категорию", callback_data="adm_del_cat_list"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить подкатегорию", callback_data="adm_del_free_list"))
    builder.row(InlineKeyboardButton(text="⚙️ Настройки цен", callback_data="adm_settings"))
    
    return builder.as_markup()

def get_admin_texts_kb(texts: list) -> InlineKeyboardMarkup:
    """Клавиатура для редактирования текстов бота - каждая кнопка на отдельной строке"""
    builder = InlineKeyboardBuilder()
    for t in texts:
        builder.row(InlineKeyboardButton(text=f"📝 {t.description}", callback_data=f"edit_text:{t.key}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="adm_cancel"))
    return builder.as_markup()

def get_settings_kb() -> InlineKeyboardMarkup:
    """Меню настроек цен и ссылок - каждая кнопка на отдельной строке"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💰 Изменить цену 1 комнаты", callback_data="set_price_single"))
    builder.row(InlineKeyboardButton(text="💰 Изменить цену 'Всей квартиры'", callback_data="set_price_full"))
    builder.row(InlineKeyboardButton(text="💰 Изменить цену 'Подбора'", callback_data="set_price_select"))
    builder.row(InlineKeyboardButton(text="🔗 Ссылка на 'Всю квартиру'", callback_data="set_link_full"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="adm_cancel"))
    return builder.as_markup()

def get_admin_del_cats_kb(items: list, is_free: bool = False) -> InlineKeyboardMarkup:
    """Универсальная клавиатура для удаления категорий или бесплатных файлов - каждая кнопка на отдельной строке"""
    builder = InlineKeyboardBuilder()
    prefix = "adm_delfree" if is_free else "adm_del_confirm"
    
    for item in items:
        if is_free:
            name = f"❌ {item.category.name}: {item.name}"
        else:
            name = f"❌ {item.name}"
        builder.row(InlineKeyboardButton(text=name, callback_data=f"{prefix}:{item.id}"))
    
    builder.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="adm_cancel"))
    return builder.as_markup()

# НОВОЕ: Кнопка отмены для форм
def get_cancel_form_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены для форм ввода"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить заполнение", callback_data="cancel_form"))
    return builder.as_markup()