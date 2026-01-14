
from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    """Состояния процесса бронирования"""
    choose_tariff = State()      # Выбор тарифа
    choose_slot = State()        # Выбор времени (убрали choose_week)
    confirm_booking = State()    # Подтверждение