from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import User, UserRoom, Gift
from tg.states import FillGiftsState, SurveyState

survey_router = Router(name="Анкета")

# Список вопросов анкеты
QUESTIONS = [
    {"key": "free_time", "question": "1/9 🚵‍♂️Как ты предпочитаешь проводить свободное время? (может хобби?)"},
    {"key": "relaxation", "question": "2/9 ⛱️Какой твой любимый способ расслабиться после напряженного дня"},
    {"key": "favorite_color", "question": "3/9 🌈Какой твой любимый цвет?"},
    {"key": "gift_type",
     "question": "4/9 💡Предпочитаешь ли ты практичные подарки или что-то более оригинальное/креативное?"},
    {"key": "gift_preference",
     "question": "5/9 🤔Есть ли у тебя предпочтения по типу подарков: что-то для дома, для работы, для отдыха?"},
    {"key": "allergies",
     "question": "6/9 🤢Есть ли у тебя какие-то аллергии или ограничения, о которых стоит знать? (если да, то какие?)"},
    {"key": "favorites", "question": "7/9 🦉Какие фильмы/персонажи/музыканты тебе нравятся?"},
    {"key": "pleasures",
     "question": "8/9 ⛷️Что тебе приносит наибольшее удовольствие: активный отдых, чтение, спорт или что-то другое?"},
    {"key": "gift_wishes", "question": "9/9 ✏️Твои личные пожелания к подарку?"},
]


@survey_router.message(SurveyState.waiting_for_answer)
async def handle_survey_answer(message: types.Message, state: FSMContext, db: AsyncSession, user: User):
    """
    Обработка ответа на текущий вопрос.
    """
    user_data = await state.get_data()
    question_index = user_data.get("question_index", 0)
    answers = user_data.get("answers", {})

    # Сохранение ответа на текущий вопрос
    question_key = QUESTIONS[question_index]["key"]
    answers[question_key] = message.text

    # Переход к следующему вопросу
    question_index += 1
    if question_index < len(QUESTIONS):
        next_question = QUESTIONS[question_index]["question"]
        await state.update_data(question_index=question_index, answers=answers)
        await message.answer(next_question)
    else:
        # Анкета завершена
        await state.set_state(SurveyState.finished)
        await state.update_data(answers=answers)

        user_room = await db.execute(select(UserRoom).filter_by(user_id=user.id, box_id=int(user_data.get("box_id"))))
        user_room = user_room.scalars().first()
        user_room.profile = answers
        db.add(user_room)
        await db.commit()

        result_text = "🎉 Спасибо за ответы!\n\n"

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")]
            ]
        )
        await message.answer(result_text, reply_markup=kb)

        user_box_gifts = await db.execute(select(Gift).filter_by(box_id=int(user_data.get("box_id")), user_id=user_room.user_id))
        user_box_gifts = user_box_gifts.scalars().all()
        if len(user_box_gifts) == 0:
            await message.answer("💡Давай заполним подарки, которые ты хотел бы получить. Ты сможешь внести сразу "
                                 "несколько вариантов подарков. Для каждого подарка можно указать, хотел бы ты "
                                 "получить именно этот предмет по ссылке или просто что-нибудь похожее.\n"
                                 "Если у твоего Санты будет несколько вариантов с отметкой \"Именно это\" - он должен "
                                 "будет выбрать один из этих вариантов. Так подарок станет сюрпризом.\n\n"
                                 "Учти, что заполнение желаемых подарков для этой коробки будет доступно тебе только "
                                 "пока коробка открыта для новых участников. Если ты не хочешь заполнять подарки, "
                                 "напиши /stop")
            box_id = int(user_data.get("box_id"))
            await state.update_data(box_id=box_id)
            await state.set_state(FillGiftsState.waiting_for_gift_url)
            await message.answer("🎁 Пожалуйста, отправь ссылку на подарок с любого маркетплейса.")
