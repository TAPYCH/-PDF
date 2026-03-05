from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from tg_bot.database.models import Base

async def init_db(db_url: str):
    """Создает таблицы в базе данных."""
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

def create_session_maker(db_url: str) -> async_sessionmaker[AsyncSession]:
    """Создает фабрику сессий."""
    engine = create_async_engine(db_url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)