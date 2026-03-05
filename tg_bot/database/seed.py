from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tg_bot.database.models import Category, FreeCatalog

# Твоя структура данных
INITIAL_DATA = [
    
]

async def seed_database(session: AsyncSession):
    """Функция заполняет БД начальными данными, если их нет"""
    print("🔄 Проверка и заполнение структуры каталогов...")
    
    for item in INITIAL_DATA:
        # 1. Проверяем, есть ли категория
        stmt = select(Category).where(Category.name == item["name"])
        cat = (await session.execute(stmt)).scalar_one_or_none()
        
        if not cat:
            # Создаем категорию
            cat = Category(name=item["name"], link_paid=item["link"])
            session.add(cat)
            await session.flush() # Чтобы получить ID категории
            print(f"✅ Создана категория: {item['name']}")
        
        # 2. Проверяем подкатегории
        for sub_name in item["subs"]:
            stmt_sub = select(FreeCatalog).where(
                FreeCatalog.category_id == cat.id, 
                FreeCatalog.name == sub_name
            )
            sub = (await session.execute(stmt_sub)).scalar_one_or_none()
            
            if not sub:
                # Создаем пустую подкатегорию (файлы добавишь через админку)
                new_sub = FreeCatalog(category_id=cat.id, name=sub_name)
                session.add(new_sub)
                print(f"   ➕ Добавлена подкатегория: {sub_name}")
    
    await session.commit()
    print("🏁 База данных успешно обновлена!")