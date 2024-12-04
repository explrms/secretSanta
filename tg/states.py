from aiogram.fsm.state import StatesGroup, State


class CreateBoxState(StatesGroup):
    waiting_for_name = State()
    waiting_for_final_reg_date = State()
    waiting_for_max_gift_price = State()
    waiting_for_gift_date = State()


class FillGiftsState(StatesGroup):
    waiting_for_gift_url = State()
    waiting_for_gift_confirmation = State()


class SurveyState(StatesGroup):
    waiting_for_answer = State()
    finished = State()


class SendAnonymousMessageFromSanta(StatesGroup):
    waiting_for_message = State()


class SendAnonymousMessageFromReceiver(StatesGroup):
    waiting_for_message = State()
