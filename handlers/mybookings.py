
import logging
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from gsheets import gsheets
from keyboards import main_menu

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "my_bookings")
async def show_my_bookings(callback: types.CallbackQuery):
    """Показать все записи пользователя"""
    logger.info(f"🔍 [МОИ ЗАПИСИ] Получен callback_query. callback_data='{callback.data}', user_id={callback.from_user.id}, username={callback.from_user.username}")
    await callback.answer()

    user = callback.from_user
    bookings = gsheets.get_user_bookings(
        user_id=user.id,
        username=user.username or "",
        full_name=user.full_name
    )

    if not bookings:
        await callback.message.edit_text(
            "📭 <b>У вас пока нет записей на практики.</b>\n\n"
            "Нажмите <b>📝 Записаться</b>, чтобы выбрать время.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        return

    # Группирвка по неделям
    weeks_dict = {}
    for booking in bookings:
        week = int(float(booking['week']))
        if week not in weeks_dict:
            weeks_dict[week] = []
        weeks_dict[week].append(booking)

    text = "📋 <b>Ваши записи:</b>\n\n"

    for week in sorted(weeks_dict.keys()):
        text += f"<b>Неделя {week}:</b>\n"
        for i, booking in enumerate(weeks_dict[week], 1):
            text += f"  {i}. {booking['date']} {booking['time']}\n"


    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu()
    )
