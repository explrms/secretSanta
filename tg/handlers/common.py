from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

common_router = Router(name="Общий роутер")


@common_router.message(Command("get_chat"))
async def get_chat(message: types.Message):
    await message.reply(f"<b>ID чата:</b> {message.chat.id}\n"
                        f"<b>ID топика:</b> {message.message_thread_id}\n"
                        f"<b>Ваш ID:</b> {message.from_user.id}")


@common_router.message(Command("stop"))
async def get_chat(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply(f"❌Действие отменено. Главное меню доступно по команде /start.")


@common_router.message(Command("raise"))
async def raise_exception(message: types.Message):
    result = 10 / 0
    await message.answer(str(result))
