from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, UserSettings, Content, Subscription
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
            referral_id = int(command.args) if command.args else None
            user = await User.create(db, id=event.from_user.id, username=event.from_user.username,
                                     referral_id=referral_id)
            await db.refresh(user)
            user_settings, created = await UserSettings.get_or_create(db, user_id=user.id)
        elif user.username != event.from_user.username:
            await User.update(db, id=user.id, data={"username": event.from_user.username})

        user_id = event.from_user.id
    elif isinstance(event, types.CallbackQuery):
        # Обработка нажатия на inline-кнопку
        user_id = event.from_user.id
    else:
        raise Exception("Обработка других типов событий не поддерживается")

    if not user.confirm_agreement:
        first_hello_text = await Content.get_by_kwargs(db, key="first_hello_text")
        message_with_hello_text = await event.answer(first_hello_text.content)
        await state.update_data(hello_message_id=message_with_hello_text.message_id)

        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="✅Прочитал и согласен", callback_data="user_agreement_confirm"
            )]
        ])
        agreement_content = await Content.get_by_kwargs(db, key="agreement_content")

        return await event.answer(agreement_content.content,
                                  reply_markup=kb,
                                  disable_web_page_preview=True)

    if not user.confirm_subscription:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(
                text="✅Прочитал и согласен", callback_data="confirm_subscription_confirm"
            )]
        ])
        confirm_subscription = await Content.get_by_kwargs(db, key="confirm_subscription")

        return await event.message.answer(confirm_subscription.content,
                                          reply_markup=kb,
                                          disable_web_page_preview=True)

    # Получаем активную подписку, если она есть
    active_subscription = await Subscription.get_active_subscription(db, user_id=user_id)

    kb = []

    if active_subscription:
        kb.append([types.InlineKeyboardButton(text="▶️Моя подписка", callback_data='my_subscription')])
        if any([user.tbank_customer_key, user.rebill_id]):
            kb.append(
                [types.InlineKeyboardButton(text="❌Отменить автопродление", callback_data='disable_autopayments')])
    else:
        kb.append([types.InlineKeyboardButton(text="💸Купить подписку", callback_data='buy_subscription')])

    kb.append([types.InlineKeyboardButton(text="ℹ️Информация", callback_data='info')])
    # kb.append([types.InlineKeyboardButton(text="👥Реферальная система", callback_data='referral_system')])
    kb.append([types.InlineKeyboardButton(text="🛟Тех. поддержка", callback_data='tech_support')])

    start_command_text = await Content.get_by_kwargs(db, key="start_command_text")
    kb_markup = types.InlineKeyboardMarkup(inline_keyboard=kb)

    if isinstance(event, types.Message):
        await event.answer(text=start_command_text.content, reply_markup=kb_markup)
    elif isinstance(event, types.CallbackQuery):
        await event.message.edit_text(text=start_command_text.content, reply_markup=kb_markup)
        await event.answer()


@register_router.callback_query(F.data == 'user_agreement_confirm')
async def user_agreement_confirm(call: types.CallbackQuery, user: User, db: AsyncSession, state: FSMContext):
    user.confirm_agreement = True
    db.add(user)
    await db.commit()
    await call.message.delete()
    await start_command(
        call,
        user,
        db,
        state
    )


@register_router.callback_query(F.data == 'confirm_subscription_confirm')
async def confirm_subscription_confirm(call: types.CallbackQuery, user: User, db: AsyncSession, state: FSMContext):
    user.confirm_subscription = True
    db.add(user)
    await db.commit()
    data = await state.get_data()
    await bot.delete_message(chat_id=call.message.chat.id,
                             message_id=data["hello_message_id"])
    await state.clear()
    await start_command(
        call,
        user,
        db,
        state
    )
