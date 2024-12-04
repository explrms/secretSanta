import os

from dotenv import load_dotenv

load_dotenv()

FAST_API_VERSION = "0.1.0"

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_DB = os.getenv("REDIS_DB")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))
THREAD_ID = int(os.getenv("THREAD_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
