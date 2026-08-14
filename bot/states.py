from aiogram.fsm.state import State, StatesGroup


class BuyStars(StatesGroup):
    choose_recipient = State()
    enter_friend_username = State()
    choose_amount = State()
    enter_custom_amount = State()
    confirm = State()


class AdminPrice(StatesGroup):
    enter_sale_price = State()
    enter_cost_price = State()


class AdminSpecial(StatesGroup):
    enter_user = State()
    choose_mode = State()
    enter_value = State()
