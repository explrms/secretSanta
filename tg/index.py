import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import Update, ErrorEvent, BufferedInputFile
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import ADMIN_CHAT_ID, ERRORS_THREAD_ID
from tg.handlers.support import support_router
from tg.loader import bot, dp
from db.db_config import get_db
from db.models import User
from tg.handlers.common import common_router
from tg.handlers.info import info_router
from tg.handlers.neuro import neuro_router
from tg.handlers.register import register_router
from tg.handlers.subscription import subscription_router
from tg.middlewares import LoggingMiddleware

# FastAPI-роутер для приёма входящих от телеграм запросов
bot_router = APIRouter(prefix="/bot", tags=["Telegram"])

# Подключение логгера к диспатчеру
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())
# Подключения роутов бота к диспатчеру
dp.include_router(common_router)
dp.include_router(register_router)
dp.include_router(subscription_router)
dp.include_router(info_router)
dp.include_router(support_router)
dp.include_router(neuro_router)


@bot_router.post("/webhook")
async def bot_webhook(update: dict,
                      db: AsyncSession = Depends(get_db)):
    """
    Обработчик вебхука от телеграма
    """
    user = None
    update_object: Update = Update.model_validate(update, context={"bot": bot})
    if from_id := (update.get("message", {}).get("from", {}).get("id", None)
                   or update.get("callback_query", {}).get("from", {}).get("id", None)):
        user = await User.get_by_kwargs(db, id=int(from_id))

    await dp.feed_update(bot,
                         update_object,
                         db=db,
                         user=user)
    return {"status": "ok"}


@dp.errors()
async def error_handler(exception: ErrorEvent, state: FSMContext):
    data = await state.get_data()
    # Логирование ошибки
    logging.exception(f"Exception: {exception}")

    if exception.update.callback_query:
        chat_id = exception.update.callback_query.message.chat.id
        message_thread_id = exception.update.callback_query.message.message_thread_id
    else:
        message_thread_id = exception.update.message.message_thread_id
        chat_id = exception.update.message.chat.id
    # Запись данных об ошибке в файл
    with open("error.txt", "w") as file:
        # Write the variable to the file
        file.write(str(exception) + "\n\n" + str(data))

    # Отправка файла с логом ошибки в указанный чат
    try:
        with open('error.txt', 'rb') as f:
            # Создаем объект InputFile для передачи в send_document()
            await bot.send_document(
                chat_id=ADMIN_CHAT_ID,
                document=BufferedInputFile(f.read(), "error.txt"),
                caption="Мне очень стыдно, но произошла ошибка, подробности в файле.",
                message_thread_id=ERRORS_THREAD_ID
            )
        await bot.send_message(chat_id=chat_id,
                               message_thread_id=message_thread_id,
                               text=f"Кажется что-то пошло не так, попробуйте повторить позже.")
        await state.clear()
    except Exception as e:
        logging.error(f"Failed to send error log: {e}")
