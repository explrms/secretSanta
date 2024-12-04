from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from config import BOT_TOKEN, REDIS_HOST, REDIS_PORT, REDIS_DB

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = RedisStorage.from_url(
    f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}", state_ttl=1200)
dp = Dispatcher(bot=bot, storage=storage)
