import logging

logger = logging.getLogger(__name__)

async def get_yandex_download_link(file_id: str = "default_free_catalog") -> str:
    """ЗАГЛУШКА: Получение ссылки на скачивание с Я.Диска"""
    logger.info(f"[YANDEX MOCK] Запрошена ссылка для файла {file_id}")
    return "https://disk.yandex.ru/i/mock_link_to_pdf_file"