from aiogram.fsm.state import State, StatesGroup


class CreateVPSStates(StatesGroup):
    choose_location = State()
    choose_tariff = State()
    choose_system = State()
    choose_period = State()
    choose_options = State()
    choose_count = State()
    confirm = State()
    enter_custom_period = State()


class TopUpStates(StatesGroup):
    enter_amount = State()


class ReinstallStates(StatesGroup):
    choose_system = State()
    confirm = State()


class CloneStates(StatesGroup):
    choose_targets = State()
    confirm = State()
