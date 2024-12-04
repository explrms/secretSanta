import datetime
import random
import secrets

import requests
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Box, User, UserRoom, Gift
from tg.handlers.survey import QUESTIONS
from tg.loader import bot
from tg.states import CreateBoxState, FillGiftsState, SurveyState, SendAnonymousMessageFromSanta, \
    SendAnonymousMessageFromReceiver

messages_router = Router(name="Роутер для переписок")


@messages_router.callback_query(F.data.startswith("send_santa_message:"))
async def send_santa_message(call: types.CallbackQuery, state: FSMContext, db: AsyncSession):
    """Отправка анонимного сообщения"""
    box = await db.execute(select(UserRoom).filter_by(box_id=int(call.data.split(':')[1]), user_id=call.from_user.id))
    box = box.scalars().first()

    await state.update_data(send_to=box.receiver.id, box_id=box.box_id)
    await call.message.edit_text(f"📤Напиши сообщение своему подопечному, а я перешлю его анонимно. "
                                 f"Старайся не выдать себя при общении, чтобы не испортить сюрприз!\n"
                                 f"Если передумал писать, напиши /stop.")
    await state.set_state(SendAnonymousMessageFromSanta.waiting_for_message)


@messages_router.message(SendAnonymousMessageFromSanta.waiting_for_message)
async def send_message_to_receiver(message: types.Message, state: FSMContext, db: AsyncSession):
    if not message.text:
        return await message.answer(f"❌В твоем сообщении нет текста. Напиши что-нибудь другое.")
    state_data = await state.get_data()
    box = await db.execute(select(Box).filter_by(id=int(state_data["box_id"])))
    box = box.scalars().first()


    kb = [[
        types.InlineKeyboardButton(text="✉️Ответить Санте", callback_data=f"send_to_santa:{box.id}")
    ]]
    try:
        await bot.send_message(chat_id=state_data["send_to"],
                               text=f"🎅Хо-хо-хо. Тебе сообщение от Тайного Санты из коробки {box.name}:\n\n"
                                    f"<i>{message.text}</i>",
                               reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
        await message.answer(f"✅Твое сообщение успешно доставлено!")
    except Exception as _ex:
        await message.answer(f"❌Не получилось доставить сообщение. Неужели получатель заблокировал бота?")


@messages_router.callback_query(F.data.startswith("send_to_santa:"))
async def send_santa_message(call: types.CallbackQuery, state: FSMContext, db: AsyncSession):
    """Отправка анонимного сообщения"""
    box = await db.execute(select(UserRoom).filter_by(box_id=int(call.data.split(':')[1]), user_gift_to_id=call.from_user.id))
    box = box.scalars().first()

    await state.update_data(send_to=box.user_id, box_id=box.box_id)
    await call.message.edit_text(f"📤Напиши сообщение своему Санте, а я перешлю его.")
    await state.set_state(SendAnonymousMessageFromReceiver.waiting_for_message)


@messages_router.message(SendAnonymousMessageFromReceiver.waiting_for_message)
async def send_message_to_receiver(message: types.Message, state: FSMContext, db: AsyncSession):
    if not message.text:
        return await message.answer(f"❌В твоем сообщении нет текста. Напиши что-нибудь другое.")
    state_data = await state.get_data()
    box = await db.execute(select(Box).filter_by(id=int(state_data["box_id"])))
    box = box.scalars().first()
    user_room = await db.execute(select(UserRoom).filter_by(box_id=box.id, user_id=int(state_data["send_to"])))
    user_room = user_room.scalars().first()

    kb = [[
        types.InlineKeyboardButton(text="✉️Ответить анонимно", callback_data=f"send_santa_message:{box.id}")
    ], [
        types.InlineKeyboardButton(text="🧑‍🎄Профиль подопечного", callback_data=f"receiver_card:{box.id}")
    ]]
    try:
        await bot.send_message(chat_id=state_data["send_to"],
                               text=f"🎅Хо-хо-хо. Тебе сообщение от твоего подопечного {user_room.receiver.full_name} "
                                    f"из коробки {box.name}:\n\n"
                                    f"<i>{message.text}</i>",
                               reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
        await message.answer(f"✅Твое сообщение успешно доставлено!")
    except Exception as _ex:
        await message.answer(f"❌Не получилось доставить сообщение. Неужели Санта заблокировал бота?")
