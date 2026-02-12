
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from states import BookingStates
from gsheets import gsheets
from keyboards import (
    tariffs_keyboard,
    weeks_keyboard,
    slots_keyboard,
    confirm_keyboard,
    main_menu,
    trainings_keyboard
)

router = Router()
logger = logging.getLogger(__name__)



# ========== НАЧАЛО ПРОЦЕССА ЗАПИСИ ==========

@router.callback_query(F.data == "book_practice")
async def start_booking(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса записи - показываем тарифы"""
    await callback.answer()

    logger.info(f"Начало записи для пользователя {callback.from_user.id}")

    # Получаем доступные тарифы из Google Sheets
    tariffs = gsheets.get_available_tariffs()
    logger.info(f"Получены тарифы: {tariffs}")

    if not tariffs:
        await callback.message.edit_text(
            "❌ Нет доступных тарифов для записи.\n"
            "Попробуйте позже или обратитесь к администратору.",
            reply_markup=main_menu()
        )
        return

    # Сохранение тарифов в состояние
    await state.update_data(tariffs=tariffs)
    await state.set_state(BookingStates.choose_tariff)

    await callback.message.edit_text(
        "📋 Выберите тариф:",
        reply_markup=tariffs_keyboard(tariffs)
    )


# ========== ВЫБОР ТАРИФА ==========


@router.callback_query(F.data.startswith("tariff:"))
async def choose_tariff(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора тарифа"""
    await callback.answer()

    tariff = callback.data.split(":")[1]
    logger.info(f"Пользователь {callback.from_user.id} выбрал тариф: {tariff}")

    weeks = gsheets.get_available_weeks(tariff)

    if not weeks:
        await callback.message.edit_text(
            f"❌ Нет доступных слотов для тарифа '{tariff}'.\n"
            "Попробуйте на следующей неделе!",
            reply_markup=main_menu()
        )
        await state.clear()
        return

    current_week = weeks[0]

    # ПРОВЕРКА: если неделя = 0
    if current_week <= 0:
        await callback.message.edit_text(
            f"❌ На текущей неделе нет практик.\n",
            reply_markup=main_menu()
        )
        await state.clear()
        return

    await state.update_data(tariff=tariff, week=current_week)
    await state.set_state(BookingStates.choose_slot)

    user_id = callback.from_user.id
    slots = gsheets.get_available_slots_for_user(tariff, current_week, user_id)

    if not slots:
        if not gsheets.can_user_book_this_week(user_id, current_week):
            # Пользователь уже записан на эту неделю
            await callback.message.edit_text(
                f"❌ Вы уже записаны на практику на неделе {int(current_week)}!",
                reply_markup=main_menu()
            )
        else:
            # Нет свободных слотов
            await callback.message.edit_text(
                f"❌ На неделе {int(current_week)} для тарифа '{tariff}' нет свободных слотов.\n"
                "Попробуйте на следующей неделе!",
                reply_markup=main_menu()
            )

        await state.clear()
        return

    slots_text = "\n".join([
        f"{i}. {slot['date']} {slot['time']} ({slot['available']}/{slot['max_seats']} мест)"
        for i, slot in enumerate(slots, 1)
    ])

    await callback.message.edit_text(
        f"📅 Тариф: <b>{tariff}</b>\n"
        f"🗓️ Неделя: <b>{int(current_week)}</b>\n\n"
        f"🕐 Выберите удобное время:\n\n{slots_text}",
        reply_markup=slots_keyboard(slots, tariff, current_week),
        parse_mode="HTML"
    )


# ========== ВЫБОР СЛОТА ==========

@router.callback_query(BookingStates.choose_slot, F.data.startswith("slot:"))
async def choose_slot(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора конкретного слота"""
    await callback.answer()

    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.message.edit_text("❌ Ошибка данных")
        return

    tariff = parts[1]
    week = float(parts[2])
    row_index = int(parts[3])  # Номер строки в таблице

    logger.info(f"Пользователь {callback.from_user.id} выбрал слот: строка {row_index}")

    # Сохраняем всё в состояние
    await state.update_data(
        tariff=tariff,
        week=week,
        row_index=row_index
    )
    await state.set_state(BookingStates.confirm_booking)

    # Получаем детали слота для подтверждения
    slots = gsheets.get_available_slots(tariff, week)
    selected_slot = next((s for s in slots if s['row_index'] == row_index), None)

    if not selected_slot:
        await callback.message.edit_text("❌ Этот слот больше не доступен")
        await state.clear()
        return

    await callback.message.edit_text(
        "📝 <b>Подтвердите запись:</b>\n\n"
        f"Неделя: <b>{int(week)}</b>\n"
        f"Дата: <b>{selected_slot['date']}</b>\n"
        f"Время: <b>{selected_slot['time']}</b>\n"
        "Записать вас на эту практику?",
        reply_markup=confirm_keyboard(tariff, week, row_index),
        parse_mode="HTML"
    )


# ========== КНОПКИ "НАЗАД" ==========

@router.callback_query(F.data == "menu:back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await callback.answer()
    await state.clear()

    await callback.message.edit_text(
        "🔙 Возврат в главное меню",
        reply_markup=main_menu()
    )


@router.callback_query(F.data == "menu:back_to_tariffs")
async def back_to_tariffs(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору тарифа"""
    await callback.answer()

    # Получаем сохранённые тарифы из состояния
    data = await state.get_data()
    tariffs = data.get('tariffs', [])

    if not tariffs:
        tariffs = gsheets.get_available_tariffs()

    await state.set_state(BookingStates.choose_tariff)

    await callback.message.edit_text(
        "📋 Выберите тариф:",
        reply_markup=tariffs_keyboard(tariffs)
    )


@router.callback_query(F.data == "menu:main")
async def back_to_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await callback.answer()
    await state.clear()

    await callback.message.edit_text(
        f"👋 Привет, {callback.from_user.first_name} ! Это бот для записи на занятия курса 'Эффективные продажи'.",
        reply_markup=main_menu()
    )


@router.callback_query(F.data.startswith("confirm:"))
async def confirm_booking(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    parts = callback.data.split(":")
    tariff = parts[1]
    week = float(parts[2])
    row_index = int(parts[3])

    user = callback.from_user
    full_name = user.full_name
    username = user.username or ""

    if gsheets.book_slot(row_index, user.id, full_name, username):
        await callback.message.edit_text(
            f"✅ <b>Вы записаны!</b>\n\n"
            f"Неделя: <b>{int(week)}</b>\n"
            f"Тариф: <b>{tariff}</b>\n\n"
            f"Нажмите '📋 Мои записи', чтобы увидеть все ваши записи.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
    else:
        await callback.message.edit_text(
            "❌ <b>Не удалось завершить запись.</b>\n\n"
            "Возможные причины:\n"
            "• Вы уже записаны на эту дату\n"
            "• Все места заняты\n"
            "• Ошибка подключения к таблице",
            parse_mode="HTML",
            reply_markup=main_menu()
        )

    await state.clear()


@router.callback_query(F.data == "menu:cancel_booking")
async def cancel_booking(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в меню"""
    await callback.answer()

    await callback.message.edit_text(
        f"👋 Привет, {callback.from_user.first_name} ! Это бот для записи на занятия курса 'Эффективные продажи'.",
        reply_markup=main_menu()
    )

    await state.clear()


# ========== ЗАПИСЬ НА ТРЕНИНГ  ==========

@router.callback_query(F.data == "book_training")
async def show_trainings(callback: types.CallbackQuery):
    """Показать доступные тренинги"""
    await callback.answer()

    user = callback.from_user
    logger.info(f"Пользователь {user.id} смотрит тренинги")

    # Проверяем неделю из B4
    training_week = gsheets.get_training_week_number()

    if training_week <= 0:
        await callback.message.edit_text(
            f"❌ На текущей неделе нет тренингов.\n",
            reply_markup=main_menu()
        )
        return

    # Проверяем, может ли пользователь вообще записаться (ДО получения списка)
    if not gsheets.can_user_book_this_week(user.id, training_week, check_only_practice=False):
        await callback.message.edit_text(
            f"❌ Вы уже записаны на тренинг или практику на неделе {int(training_week)}!",
            reply_markup=main_menu()
        )
        return

    # Получаем тренинги (без проверки user_id, т.к. уже проверили выше)
    trainings = gsheets.get_available_trainings()

    if not trainings:
        await callback.message.edit_text(
            f"❌ Нет доступных тренингов для записи на неделе {int(training_week)}.\n",
            reply_markup=main_menu()
        )
        return

    await callback.message.edit_text(
        f"🎓 <b>Доступные тренинги (неделя {int(training_week)}):</b>\n\n"
        "Нажмите на тренинг для записи:",
        reply_markup=trainings_keyboard(trainings),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("training:"))
async def book_training(callback: types.CallbackQuery):
    """Записаться на тренинг сразу"""
    await callback.answer()

    row_index = int(callback.data.split(":")[1])
    user = callback.from_user

    logger.info(f"Пользователь {user.id} записывается на тренинг: строка {row_index}")

    # Записываем сразу
    success = gsheets.book_training(row_index, user.id, user.full_name, user.username or "")

    if success:
        # Получаем детали тренинга для сообщения
        training = gsheets.get_training_details(row_index)
        if training:
            message = (
                f"🎓 <b>Вы записаны на тренинг!</b>\n\n"
                f"Неделя: <b>{int(gsheets.get_training_week_number())}</b>\n"
                f"Дата: <b>{training['date']}</b>\n"
                f"Время: <b>{training['time']}</b>\n"
            )
        else:
            message = "✅ Вы записаны на тренинг!"
    else:
        message = (
            "❌ <b>Не удалось записаться.</b>\n\n"
            "Возможные причины:\n"
            "• Вы уже записаны на этот тренинг\n"
            "• Все места заняты\n"
            "• Нельзя записываться на эту неделю"
        )

    await callback.message.edit_text(
        message,
        parse_mode="HTML",
        reply_markup=main_menu()
    )


