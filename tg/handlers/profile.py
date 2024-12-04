import copy
import datetime
import random

from aiogram import Router, types, F
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Box, UserRoom, User

profile_router = Router(name="Роутер для просмотра профилей")


@profile_router.callback_query(F.data.startswith("receiver_card:"))
async def show_receiver_profile(call: types.CallbackQuery, db: AsyncSession):
    """
    Показать профиль подопечного в указанной коробке.
    """
    box_id = int(call.data.split(":")[1])

    # Получаем информацию о подопечном
    user_room_query = await db.execute(
        select(UserRoom).filter_by(user_id=call.from_user.id, box_id=box_id)
    )
    user_room = user_room_query.scalars().first()

    if not user_room or not user_room.receiver:
        await call.message.edit_text(
            "❌ Профиль подопечного недоступен.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"select_box:{box_id}")]]
            ),
        )
        return

    receiver = user_room.receiver
    receiver_profile = user_room.profile

    # Основная информация о подопечном
    text = (f"🧑‍🎄 <b>Профиль подопечного</b>\n\n"
            f"👤 <b>Имя:</b> {receiver.full_name}\n"
            f"📅 <b>Дата регистрации:</b> {receiver.date_reg.strftime('%d.%m.%Y')}\n"
            f"📧 <b>Username:</b> @{receiver.username if receiver.username else 'не указан'}\n\n"
            f"❗️Не пиши человеку лично, это выдаст тебя и Тайного Санты не получится! Лучше воспользуйся анонимным "
            f"чатом в боте.")

    kb = []

    # Кнопка "О пользователе" с результатами анкеты
    if receiver_profile:
        kb.append([types.InlineKeyboardButton(text="📄 О пользователе", callback_data=f"user_profile:{box_id}")])

    # Кнопка "Желаемые подарки", если такие указаны
    if len(receiver.gifts) > 0:
        kb.append([types.InlineKeyboardButton(text="🎁 Желаемые подарки", callback_data=f"user_gift_wishes:{box_id}")])

    kb.append([types.InlineKeyboardButton(text="🎭Анонимное сообщение", callback_data=f"send_santa_message:{box_id}")])

    # Кнопка "Назад"
    kb.append([types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"select_box:{box_id}")])

    await call.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))


@profile_router.callback_query(F.data.startswith("user_profile:"))
async def show_user_profile(call: types.CallbackQuery, db: AsyncSession):
    """
    Показать результаты анкеты подопечного.
    """
    box_id = int(call.data.split(":")[1])

    # Получаем профиль подопечного
    user_room_query = await db.execute(
        select(UserRoom).filter_by(user_id=call.from_user.id, box_id=box_id)
    )
    user_room = user_room_query.scalars().first()

    user_room_query = await db.execute(
        select(UserRoom).filter_by(user_id=user_room.receiver.id, box_id=box_id)
    )
    user_room = user_room_query.scalars().first()

    if not user_room or not user_room.profile:
        await call.message.edit_text(
            "❌ Профиль пользователя отсутствует.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"receiver_card:{box_id}")]]
            ),
        )
        return

    profile = user_room.profile
    text = "📄 <b>Анкета подопечного</b>\n\n"
    questions = {
        "free_time": "🚵‍♂️ Свободное время:",
        "relaxation": "⛱️ Способ расслабления:",
        "favorite_color": "🌈 Любимый цвет:",
        "gift_type": "💡 Практичные или креативные подарки:",
        "gift_preference": "🤔 Предпочтения по подаркам:",
        "allergies": "🤢 Аллергии или ограничения:",
        "favorites": "🦉 Любимые фильмы/персонажи/музыканты:",
        "pleasures": "⛷️ Что приносит удовольствие:",
        "gift_wishes": "✏️ Пожелания к подарку:",
    }

    for key, question in questions.items():
        if key in profile:
            text += f"<b>{question}</b> {profile[key]}\n"

    await call.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"receiver_card:{box_id}")]]
        ),
    )


@profile_router.callback_query(F.data.startswith("user_gift_wishes:"))
async def show_user_gift_wishes(call: types.CallbackQuery, db: AsyncSession):
    """
    Показать пожелания подопечного к подаркам.
    """
    box_id = int(call.data.split(":")[1])

    # Получаем профиль подопечного
    user_room_query = await db.execute(
        select(UserRoom).filter_by(user_id=call.from_user.id, box_id=box_id)
    )
    user_room = user_room_query.scalars().first()

    if len(user_room.receiver.gifts) == 0:
        await call.message.edit_text(
            "❌ Пожелания к подаркам отсутствуют.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"receiver_card:{box_id}")]]
            ),
        )
        return

    text = f"🎁 <b>Желаемые подарки</b>\n\n"
    gifts_object = []
    for gift in user_room.receiver.gifts:
        gifts_object.append({"url": gift.gift_url, "is_exact": gift.is_exact})
    random.shuffle(gifts_object)

    for gift in gifts_object:
        if gift["is_exact"]:
            gift_icon = "🎯"
        else:
            gift_icon = "🎲"
        text += f"🎁 {gift["url"]} — {gift_icon}\n"

    text += "\n🎯 - хочется получить именно это; 🎲 - хочется что-нибудь похожее"

    await call.message.edit_text(
        text,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"receiver_card:{box_id}")]]
        ),
        disable_web_page_preview=True
    )