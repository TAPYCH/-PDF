import datetime
from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    full_name: Mapped[str] = mapped_column(String, nullable=True)

class Settings(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    price_single: Mapped[int] = mapped_column(Integer, default=399)
    price_full: Mapped[int] = mapped_column(Integer, default=799)
    price_select: Mapped[int] = mapped_column(Integer, default=500)
    link_full: Mapped[str] = mapped_column(String, default="https://disk.yandex.ru/")

# Таблица для текстов
class BotText(Base):
    __tablename__ = "bot_texts"
    key: Mapped[str] = mapped_column(String, primary_key=True)  # Уникальный ключ
    description: Mapped[str] = mapped_column(String)            # Понятное описание для админа
    text: Mapped[str] = mapped_column(Text)                     # Сам текст

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    link_paid: Mapped[str] = mapped_column(String)
    
    free_catalogs: Mapped[list["FreeCatalog"]] = relationship(back_populates="category", cascade="all, delete-orphan")
    # Убираем прямую связь с deep_links, так как она идет через FreeCatalog

class FreeCatalog(Base):
    __tablename__ = "free_catalogs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String)
    
    category: Mapped["Category"] = relationship(back_populates="free_catalogs")
    files: Mapped[list["FreeFile"]] = relationship(back_populates="free_catalog", cascade="all, delete-orphan")
    deep_links: Mapped[list["DeepLink"]] = relationship(back_populates="free_catalog", cascade="all, delete-orphan")

class FreeFile(Base):
    __tablename__ = "free_files"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    free_catalog_id: Mapped[int] = mapped_column(ForeignKey("free_catalogs.id"))
    file_id: Mapped[str] = mapped_column(String)
    
    free_catalog: Mapped["FreeCatalog"] = relationship(back_populates="files")

class DeepLink(Base):
    __tablename__ = "deep_links"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String, unique=True)
    custom_text: Mapped[str] = mapped_column(Text)
    
    # Ссылаемся на конкретный БЕСПЛАТНЫЙ файл (например, Диваны)
    free_catalog_id: Mapped[int] = mapped_column(ForeignKey("free_catalogs.id"))
    
    free_catalog: Mapped["FreeCatalog"] = relationship(back_populates="deep_links")
    
    @property
    def category(self):
        """Свойство для получения категории через бесплатный каталог"""
        return self.free_catalog.category if self.free_catalog else None

class Access(Base):
    __tablename__ = "access"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id"), index=True)
    category_id: Mapped[int] = mapped_column(Integer, nullable=True)
    catalog_type: Mapped[str] = mapped_column(String)
    purchase_date: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)