# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🧑‍🏫 Запись на практику", callback_data="book_practice")
    builder.button(text="🎓 Запись на тренинг", callback_data="book_training")
    builder.button(text="📋 Мои записи", callback_data="my_bookings")
    builder.button(text="ℹ️ Помощь", callback_data="help")
    builder.adjust(1)
    return builder.as_markup()


def tariffs_keyboard(tariffs: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа"""
    builder = InlineKeyboardBuilder()

    for tariff in tariffs:
        if tariff == "Тренинг":
            continue
        if tariff == "Базовый":
            button_text = "Практика базовый"
        elif tariff == "Основной":
            button_text = "Практика основной"
        else:
            button_text = tariff
        builder.button(text=button_text, callback_data=f"tariff:{tariff}")

    builder.button(text="🔙 Назад", callback_data="menu:back_to_main")
    builder.adjust(1)
    return builder.as_markup()


def weeks_keyboard(weeks: list, tariff: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for week in weeks:
        week_int = int(week)
        builder.button(
            text=f"Неделя {week_int}",
            callback_data=f"week:{tariff}:{week}"  # Добавь tariff
        )
    builder.button(text="🔙 Назад", callback_data="menu:back_to_tariffs")
    builder.adjust(1)
    return builder.as_markup()


def slots_keyboard(slots: list, tariff: str, week: float) -> InlineKeyboardMarkup:
    """Клавиатура выбора слота"""
    builder = InlineKeyboardBuilder()

    for slot in slots:
        text = f"{slot['date']} {slot['time']}"


        builder.button(
            text=text,
            callback_data=f"slot:{tariff}:{week}:{slot['row_index']}"
        )

    builder.button(text="🔙 Назад", callback_data=f"menu:back_to_tariffs")
    builder.adjust(1)
    return builder.as_markup()

def confirm_keyboard(tariff: str, week: float, row_index: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Да, записаться", callback_data=f"confirm:{tariff}:{week}:{row_index}")
    builder.button(text="❌ Нет, отменить", callback_data="menu:cancel_booking")

    builder.adjust(2)  # Две кнопки в ряд
    return builder.as_markup()

def trainings_keyboard(trainings: list) -> InlineKeyboardMarkup:
    """Клавиатура выбора тренинга"""
    builder = InlineKeyboardBuilder()

    for training in trainings:
        # training = {'date': '20 августа', 'time': '10:00', 'row_index': 2}
        button_text = f"{training['date']} {training['time']}"
        builder.button(
            text=button_text,
            callback_data=f"training:{training['row_index']}"
        )

    builder.button(text="🔙 Назад", callback_data="menu:back_to_main")
    builder.adjust(1)
    return builder.as_markup()