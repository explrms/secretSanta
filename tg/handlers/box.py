import datetime
import random
import secrets

import requests
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Box, User, UserRoom, Gift
from tg.handlers.survey import QUESTIONS
from tg.loader import bot
from tg.states import CreateBoxState, FillGiftsState, SurveyState

box_router = Router(name="Роутер для управления коробками")


@box_router.callback_query(F.data == "create_box")
@box_router.message(Command("create_box"))
async def start_create_box(call: types.CallbackQuery, state: FSMContext):
    """
    Начало создания коробки.
    """
    await state.set_state(CreateBoxState.waiting_for_name)
    await call.message.edit_text("🎉 Давайте создадим новую коробку!\n\nВведите название коробки:")


@box_router.message(CreateBoxState.waiting_for_name)
async def set_box_name(message: types.Message, state: FSMContext):
    """
    Сохранение названия коробки.
    """
    box_name = message.text
    await state.update_data(name=box_name)
    await state.set_state(CreateBoxState.waiting_for_final_reg_date)
    await message.answer("📅 Укажите дату окончания регистрации (в формате ДД.ММ.ГГГГ):")


@box_router.message(CreateBoxState.waiting_for_final_reg_date)
async def set_final_reg_date(message: types.Message, state: FSMContext):
    """
    Сохранение даты окончания регистрации.
    """
    try:
        final_reg_date = message.text
        await state.update_data(final_reg_date=final_reg_date)
        await state.set_state(CreateBoxState.waiting_for_max_gift_price)
        await message.answer("💰 Укажите максимальную сумму подарка (в рублях):")
    except ValueError:
        await message.answer("❌ Неверный формат даты. Попробуйте снова (ДД.ММ.ГГГГ):")


@box_router.message(CreateBoxState.waiting_for_max_gift_price)
async def set_max_gift_price(message: types.Message, state: FSMContext):
    """
    Сохранение максимальной суммы подарка.
    """
    try:
        max_price = float(message.text)
        await state.update_data(max_gift_price=max_price)
        await state.set_state(CreateBoxState.waiting_for_gift_date)
        await message.answer("🎁 Укажите дату вручения подарков (в формате ДД.ММ.ГГГГ):")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число для максимальной суммы подарка.")


@box_router.message(CreateBoxState.waiting_for_gift_date)
async def set_gift_date(message: types.Message, state: FSMContext, db: AsyncSession, user: User):
    """
    Сохранение даты вручения подарков и создание коробки.
    """
    try:
        gift_date = message.text
        data = await state.get_data()

        # Генерация уникального кода для вступления в коробку
        join_code = secrets.token_urlsafe(8)

        # Создание записи коробки в БД
        new_box = Box(
            name=data["name"],
            join_code=join_code,
            final_reg_date=datetime.datetime.strptime(data["final_reg_date"], "%d.%m.%Y"),
            max_gift_price=data["max_gift_price"],
            gift_date=datetime.datetime.strptime(gift_date, "%d.%m.%Y"),
            admin_id=user.id,
        )
        db.add(new_box)
        await db.commit()

        await state.clear()

        await message.answer(
            f"🎉 Коробка '{data['name']}' успешно создана!\n"
            f"🔑 Cсылка для вступления: <code>https://t.me/secret_s_a_n_t_a_bot?start={join_code}</code>\n"
            f"📅 Регистрация до: {data['final_reg_date']}\n"
            f"💰 Максимальная сумма подарка: {data['max_gift_price']} руб.\n"
            f"🎁 Дата вручения: {gift_date}\n\n"
            f"Вы можете поделиться ссылкой для приглашения участников."
        )
    except ValueError:
        await message.answer("❌ Неверный формат даты. Попробуйте снова (ДД.ММ.ГГГГ):")


@box_router.callback_query(F.data == "my_boxes")
async def my_boxes_root(call: types.CallbackQuery, db: AsyncSession, user: User):
    text = f"👇Выберите одну из ваших коробок:"
    kb = []
    for box in user.rooms:
        kb.append([
            types.InlineKeyboardButton(text=f"{box.name}", callback_data=f"select_box:{box.id}")
        ])
    kb.append([
        types.InlineKeyboardButton(text="🔙Назад в меню", callback_data="main_menu")
    ])

    await call.message.edit_text(text=text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))


@box_router.callback_query(F.data.startswith("select_box:"))
async def select_box_root(call: types.CallbackQuery, db: AsyncSession, user: User):
    box = await db.execute(select(Box).filter_by(id=int(call.data.split(':')[1])))
    box = box.scalars().first()
    box_text = (f"ℹ️Информация о коробке {box.name}:\n\n"
                f"⌛️<b>Окончание регистрации участников:</b> {datetime.datetime.strftime(box.final_reg_date, "%d.%m.%Y")}\n"
                f"🤑<b>Максимальная сумма подарка:</b> {box.max_gift_price}₽\n"
                f"🎁<b>Вручение:</b> {datetime.datetime.strftime(box.gift_date, "%d.%m.%Y")}")

    user_room = await db.execute(select(UserRoom).filter_by(user_id=user.id, box_id=box.id))
    user_room = user_room.scalars().first()
    kb = []
    if not user_room.receiver:
        box_text += "\n\n🕰️Вам еще не назначен подопечный для вручения подарка, ожидайте распределения."
        shuffled = False
        if user_room.profile == {}:
            kb.append([
                types.InlineKeyboardButton(text="✨Заполнить пожелания", callback_data=f"fill_wishes:{box.id}")
            ])
        else:
            kb.append([
                types.InlineKeyboardButton(text="✨Изменить пожелания", callback_data=f"fill_wishes:{box.id}")
            ])

        user_box_gifts = await db.execute(select(Gift).filter_by(box_id=box.id, user_id=user_room.user_id))
        user_box_gifts = user_box_gifts.scalars().all()
        if len(user_box_gifts) == 0:
            kb.append([
                types.InlineKeyboardButton(text="🎁Заполнить подарки", callback_data=f"fill_gifts:{box.id}")
            ])
        else:
            kb.append([
                types.InlineKeyboardButton(text="🎁Список подарков", callback_data=f"list_gifts:{box.id}")
            ])
    else:
        box_text += ("\n\n✅Вам назначен подопечный для вручения подарка. Вы можете ознакомиться с его пожеланиями или "
                     "пообщаться через кнопку ниже.")
        kb.append([
            types.InlineKeyboardButton(text="🧑‍🎄Мой подопечный", callback_data=f"receiver_card:{box.id}")
        ])
        kb.append([
            types.InlineKeyboardButton(text="✉️Написать моему Санте", callback_data=f"send_to_santa:{box.id}")
        ])
        shuffled = True

    if box.admin_id == call.from_user.id:
        box_text += ("\n\n👑Информация для администратора:\n"
                     "👥Участники:\n")
        user_rooms = await db.execute(select(UserRoom).filter_by(box_id=box.id))
        user_rooms = user_rooms.scalars().all()
        for user in user_rooms:
            if user.profile == {}:
                emoji_status = "❌"
            else:
                emoji_status = "✅"
            box_text += f"\n→ {user.user.full_name} (@{user.user.username}) {emoji_status}"
        box_text += "\n✅Заполнил пожелания, ❌Не заполнил пожелания"

        if not shuffled:
            kb.append([
                types.InlineKeyboardButton(text="🎲Провести жеребьёвку", callback_data=f"shuffle_box:{box.id}")
            ])

        kb.append([
            types.InlineKeyboardButton(text="🗑️Удалить коробку", callback_data=f'delete_box:{box.id}')
        ])

    kb.append([
        types.InlineKeyboardButton(text="🔙Назад в список коробок", callback_data='my_boxes')
    ])
    await call.message.edit_text(box_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))


@box_router.callback_query(F.data.startswith("fill_wishes:"))
async def fill_wishes(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer(f"🎙️Пожалуйста, ответьте на несколько вопросов, чтобы Ваш санта мог подарить вам лучший "
                              f"подарок. Помните, что заполнить пожелания для этой коробки можно только пока коробка "
                              f"открыта для новых участников!")
    await state.set_state(SurveyState.waiting_for_answer)
    await state.update_data(question_index=0, answers={}, box_id=int(call.data.split(":")[1]))
    question = QUESTIONS[0]["question"]
    return await call.message.answer(f"{question}")


@box_router.callback_query(F.data.startswith("shuffle_box:"))
async def shuffle_box_handler(call: types.CallbackQuery, db: AsyncSession, user: User):
    """
    Хэндлер для выполнения шафла участников комнаты.
    """
    box_id = int(call.data.split(':')[1])

    # Получение всех записей UserRoom для указанной комнаты
    user_rooms_query = await db.execute(
        select(UserRoom).filter_by(box_id=box_id)
    )
    user_rooms = user_rooms_query.scalars().all()

    if len(user_rooms) < 2:
        await call.message.edit_text(
            "❌ Недостаточно участников для жеребьевки. Минимум 2 участника.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"select_box:{box_id}")]]
            ),
        )
        return
    for user in user_rooms:
        if user.profile == {}:
            await call.message.edit_text(
                "❌ Не все участники заполнили свои пожелания.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data=f"select_box:{box_id}")]]
                ),
            )
            return

    # Перемешиваем участников случайным образом
    user_ids = [user_room.user_id for user_room in user_rooms]

    # Обеспечиваем, что никто не дарит подарок сам себе
    is_valid_shuffle = False
    while not is_valid_shuffle:
        random.shuffle(user_ids)
        is_valid_shuffle = all(
            user_room.user_id != user_ids[(i + 1) % len(user_ids)]  # Проверка на "не сам себе"
            for i, user_room in enumerate(user_rooms)
        )

    # Назначение подопечных (receiver) для каждого участника
    for i, user_room in enumerate(user_rooms):
        user_room.user_gift_to_id = user_ids[(i + 1) % len(user_ids)]  # Следующий участник в списке

    # Сохранение изменений в базе данных
    await db.commit()

    kb = []
    kb.append([
        types.InlineKeyboardButton(text="🧑‍🎄Мой подопечный", callback_data=f"receiver_card:{box_id}")
    ])

    for user in user_ids:
        await bot.send_message(chat_id=user,
                               text=f"🧑‍🎄Тебе назначен подопечный на Тайного Санту. Скорее открывай его профиль "
                                    f"и готовься дарить подарок!",
                               reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

    # Уведомление об успешной жеребьевке
    await call.message.edit_text(
        "🎲 Жеребьевка завершена! Всем участникам назначены подопечные для вручения подарков.",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Вернуться к коробке", callback_data=f"select_box:{box_id}")]]
        ),
    )


@box_router.callback_query(F.data.startswith("fill_gifts:"))
async def start_fill_gifts(call: types.CallbackQuery, state: FSMContext):
    """
    Начало заполнения списка подарков.
    """
    await call.message.edit_text("💡Давай заполним подарки, которые ты хотел бы получить. Ты сможешь внести сразу "
                                 "несколько вариантов подарков. Для каждого подарка можно указать, хотел бы ты "
                                 "получить именно этот предмет по ссылке или просто что-нибудь похожее.\n"
                                 "Если у твоего Санты будет несколько вариантов с отметкой \"Именно это\" - он должен "
                                 "будет выбрать один из этих вариантов. Так подарок станет сюрпризом.\n\n"
                                 "Учти, что заполнение желаемых подарков для этой коробки будет доступно тебе только "
                                 "пока коробка открыта для новых участников. Если ты передумал заполнять подарки, "
                                 "напиши /stop")
    box_id = int(call.data.split(":")[1])
    await state.update_data(box_id=box_id)
    await state.set_state(FillGiftsState.waiting_for_gift_url)
    await call.message.answer("🎁 Пожалуйста, отправь ссылку на подарок с любого маркетплейса.")


@box_router.message(FillGiftsState.waiting_for_gift_url)
async def set_gift_url(message: types.Message, state: FSMContext):
    """
    Сохранение ссылки на подарок и переход к подтверждению.
    """
    gift_url = message.text
    response = requests.get(f'https://clck.ru/--',
                            params={
                                'url': f'{gift_url}'})
    if response.status_code == 200:
        link = response.text
    else:
        return await message.answer(f"Кажется вы отправили недействительную ссылку.")

    await state.update_data(gift_url=link)
    await state.set_state(FillGiftsState.waiting_for_gift_confirmation)

    # Отправка сообщения с inline-кнопками
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🎯 Именно это", callback_data="gift_is_exact:1"),
            types.InlineKeyboardButton(text="🎲 Что-то похожее", callback_data="gift_is_exact:0")
        ]
    ])
    await message.answer("🎁 Вы хотите получить именно этот подарок или что-то похожее?", reply_markup=kb)


@box_router.callback_query(F.data.startswith("gift_is_exact:"))
async def set_gift_confirmation(call: types.CallbackQuery, state: FSMContext, db: AsyncSession, user: User):
    """
    Сохранение подтверждения, добавление подарка в базу данных и запрос на новый подарок.
    """
    is_exact = bool(int(call.data.split(":")[1]))
    data = await state.get_data()

    # Создание подарка в базе данных
    new_gift = Gift(
        box_id=data["box_id"],
        user_id=user.id,
        gift_url=data["gift_url"],
        is_exact=is_exact,
    )
    db.add(new_gift)
    await db.commit()

    # Запрос следующего действия
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🎁 Добавить еще один подарок", callback_data="add_another_gift"),
            types.InlineKeyboardButton(text="🚪 Завершить добавление", callback_data="exit_gift_filling")
        ]
    ])
    await call.message.edit_text(
        "🎉 Ваш подарок успешно добавлен! Хотите добавить еще один или завершить?",
        reply_markup=kb
    )


@box_router.callback_query(F.data == "add_another_gift")
async def add_another_gift(call: types.CallbackQuery, state: FSMContext):
    """
    Возвращение пользователя к добавлению новой ссылки на подарок.
    """
    await state.set_state(FillGiftsState.waiting_for_gift_url)
    await call.message.edit_text("🎁 Пожалуйста, отправьте ссылку на следующий подарок.")


@box_router.callback_query(F.data == "exit_gift_filling")
async def exit_gift_filling(call: types.CallbackQuery, state: FSMContext):
    """
    Выход из состояния заполнения подарков.
    """
    await state.clear()
    await call.message.edit_text(
        "🚪 Вы завершили добавление подарков. Вы можете вернуться к коробке из меню по команде /start."
    )


@box_router.callback_query(F.data.startswith("list_gifts:"))
async def list_gifts(call: types.CallbackQuery, db: AsyncSession, user: User):
    box_id = int(call.data.split(':')[1])
    stmt = await db.execute(select(Gift).filter_by(box_id=box_id, user_id=call.from_user.id))
    gifts = stmt.scalars().all()
    kb = []
    for number, gift in enumerate(gifts):
        kb.append([
            types.InlineKeyboardButton(text=f"{number+1}. {gift.gift_url}", url=gift.gift_url),
            types.InlineKeyboardButton(text=f"🗑️", callback_data=f"delete_gift:{gift.id}"),
        ])
    kb.append([
        types.InlineKeyboardButton(text="🎁Добавить подарки", callback_data=f"fill_gifts:{box_id}")
    ])
    kb.append([
        types.InlineKeyboardButton(text="🔙Вернуться в коробку", callback_data=f"select_box:{box_id}")
    ])

    await call.message.edit_text(text="✏️В этом меню можно удалить ненужные подарки или добавить новые:",
                                 reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))


@box_router.callback_query(F.data.startswith("delete_gift:"))
async def delete_gift(call: types.CallbackQuery, db: AsyncSession):
    gift_id = int(call.data.split(':')[1])
    stmt = await db.execute(select(Gift).filter_by(id=gift_id))
    gift = stmt.scalars().first()
    box_id = gift.box_id
    if gift.user_id == call.from_user.id:
        await db.execute(delete(Gift).filter_by(id=gift.id))
        await db.commit()
        kb = [[
            types.InlineKeyboardButton(text="🔙Назад в список подарков", callback_data=f"list_gifts:{box_id}")
        ]]

        await call.message.edit_text(text=f"✅Подарок успешно удалён!",
                                     reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

@box_router.callback_query(F.data.startswith("delete_box:"))
async def delete_box_root(call: types.CallbackQuery, db: AsyncSession):
    box_id = int(call.data.split(':')[1])
    stmt = await db.execute(select(Box).filter_by(id=box_id))
    box = stmt.scalars().first()
    if not box.admin_id == call.from_user.id:
        return await call.answer(f"⛔️Вы не имеете доступа к удалению этой коробки!")
    kb = [
        [types.InlineKeyboardButton(text="Да, я уверен(а)", callback_data=f"delete_box_confirm:{box_id}")],
        [types.InlineKeyboardButton(text="Нет, отменить!", callback_data=f"select_box:{box_id}")],
        [types.InlineKeyboardButton(text="О боже, нет!", callback_data=f"select_box:{box_id}")],
    ]
    random.shuffle(kb)
    await call.message.edit_text(text=f"⁉️Вы подтверждаете удаление коробки <b>{box.name}</b>?",
                                 reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))


@box_router.callback_query(F.data.startswith("delete_box_confirm:"))
async def delete_box_confirm(call: types.CallbackQuery, db: AsyncSession):
    box_id = int(call.data.split(':')[1])
    await db.execute(delete(UserRoom).filter_by(box_id=box_id))
    await db.execute(delete(Gift).filter_by(box_id=box_id))
    await db.execute(delete(Box).filter_by(id=box_id))
    await db.commit()
    kb = [[
        types.InlineKeyboardButton(text="🔙Назад в меню", callback_data="main_menu")
    ]]

    await call.message.edit_text(text=f"✅Коробка успешно удалена!",
                                 reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))

