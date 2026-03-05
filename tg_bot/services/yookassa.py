import logging

logger = logging.getLogger(__name__)

async def create_payment_mock(amount: int, description: str, user_id: int) -> str:
    """ЗАГЛУШКА: Создание платежа в ЮKassa"""
    logger.info(f"[YOOKASSA MOCK] Создан платеж на {amount} руб. для юзера {user_id}. Описание: {description}")
    # Возвращаем "фейковую" ссылку на оплату.
    return "https://yoomoney.ru/mock_payment_page"