import os
import logging
import aiohttp

logger = logging.getLogger(__name__)

async def send_lead_to_bitrix(user_id: int, username: str, full_name: str, action_desc: str, phone: str = None) -> bool:
    """
    Отправляет Лид в Битрикс24.
    action_desc - суть заявки (какой файл скачал, или текст вопроса).
    phone - телефон (если заполнялась форма).
    """
    webhook_url = os.getenv("BITRIX_WEBHOOK_URL")
    
    # Если вебхук не настроен, просто пишем в консоль (чтобы бот не падал)
    if not webhook_url or "your-domain" in webhook_url:
        logger.warning(f"[BITRIX MOCK] Лид не отправлен (нет URL). {full_name} | {action_desc} | {phone}")
        return False

    # Формируем URL для вызова метода добавления лида
    url = f"{webhook_url}crm.lead.add.json"
    
    # Ссылка на Telegram для менеджера
    tg_link = f"https://t.me/{username}" if username else f"TG ID: {user_id}"
    
    # Формируем поля карточки Лида
    fields = {
        "TITLE": f"TG Бот: {action_desc[:40]}...", # Название лида
        "NAME": full_name,                         # Имя
        "COMMENTS": f"<b>Детали:</b> {action_desc}<br><b>Связь:</b> {tg_link}",
        "SOURCE_ID": "WEB",                        # Источник
    }
    
    # Если клиент оставил телефон, добавляем его в системное поле
    if phone:
        fields["PHONE"] =[{"VALUE": phone, "VALUE_TYPE": "WORK"}]

    payload = {
        "fields": fields,
        "params": {"REGISTER_SONET_EVENT": "Y"} # Уведомить менеджеров о новом лиде
    }

    try:
        # Делаем асинхронный POST-запрос к Битриксу
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Лид успешно создан в Битрикс! ID: {data.get('result')}")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Ошибка Битрикс24: {error_text}")
                    return False
    except Exception as e:
        logger.error(f"❌ Ошибка сети при отправке в Битрикс: {e}")
        return False