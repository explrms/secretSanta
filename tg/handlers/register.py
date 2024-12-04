from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, Box, UserRoom
from tg.handlers.survey import QUESTIONS
from tg.states import SurveyState
from tg.loader import bot

register_router = Router(name="Роутер регистрации и главного меню")


@register_router.callback_query(F.data == "main_menu")
@register_router.message(Command("start"))
async def start_command(event: types.Message | types.CallbackQuery,
                        user: User,
                        db: AsyncSession,
                        state: FSMContext,
                        command: CommandObject = None,
                        ):
    """
    Входная точка для работы с ботом.
    :param state:
    :param db: Объект сессии
    :param event: Сообщение
    :param command: Объект команды. Может содержать аргументы
    :param user: Объект пользователя из базы
    :return:
    """
    if isinstance(event, types.Message):
        # Обработка команды /start
        if not user:
            user = User(
                id=event.from_user.id,
                username=event.from_user.username,
                full_name=event.from_user.full_name,
            )
            db.add(user)
            await db.commit()
            user = await db.execute(select(User).filter_by(id=event.from_user.id))
            user = user.scalars().first()
        elif user.username != event.from_user.username:
            user.username = event.from_user.username
            db.add(user)
            await db.commit()
            user = await db.execute(select(User).filter_by(id=event.from_user.id))
            user = user.scalars().first()

        user_id = event.from_user.id
    elif isinstance(event, types.CallbackQuery):
        # Обработка нажатия на inline-кнопку
        user_id = event.from_user.id
    else:
        raise Exception("Обработка других типов событий не поддерживается")

    kb = []

    hello_text = "🎄Добро пожаловать в бота Тайный Санта 2025!\n\n"
    if len(user.rooms) == 0:
        hello_text += ("🫙Вы пока не состоите ни в одной коробке. Создайте её или используйте ссылку-приглашение "
                       "от администратора.")
    else:
        hello_text += f"🌟Вы состоите в следующих коробках:\n"
        for room in user.rooms:
            hello_text += f"⭐︎ {room.name}\n"
        kb.append([
            types.InlineKeyboardButton(text="🎁Мои коробки", callback_data="my_boxes")
        ])

    kb.append([
        types.InlineKeyboardButton(text="🎉Создать коробку", callback_data="create_box")
    ])
    if command and command.args:
        # Если поймали аргументы, значит это идентификатор коробки
        box = await db.execute(select(Box).filter_by(join_code=str(command.args)))
        box = box.scalars().first()
        if box:
            user_room = await db.execute(select(UserRoom).filter_by(box_id=box.id))
            user_room = user_room.scalars().first()
            if user_room and user_room.receiver:
                return await event.answer(f"❌Эта коробка закрыта для новых участников. Ты не можешь "
                                          f"к ней присоединиться!")
            # Проверяем есть ли пользователь в коробке
            user_room = await db.execute(select(UserRoom).filter_by(user_id=user.id, box_id=box.id))
            if user_room.scalars().first():
                return await event.answer(f"🫷Притормози, ты уже состоишь в этой коробке как участник. "
                                          f"Если хочешь посмотреть "
                                          f"информацию о ней, напиши /start.")

            # Create a UserRoom instance
            user_room = UserRoom(user_id=user.id, box_id=box.id, profile={})
            # Add the UserRoom instance to the session
            db.add(user_room)
            # Commit the transaction
            await db.commit()
            await event.answer(
                f"🎁Вы успешно вступили в коробку <strong>{box.name}</strong>. Пожалуйста, ответьте на несколько "
                f"вопросов, чтобы Ваш санта мог подарить вам лучший подарок!")
            await state.set_state(SurveyState.waiting_for_answer)
            await state.update_data(question_index=0, answers={}, box_id=box.id)
            question = QUESTIONS[0]["question"]
            return await event.answer(f"{question}")

    if isinstance(event, types.Message):
        await event.answer(text=hello_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
    elif isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text=hello_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb))
        await event.answer()
