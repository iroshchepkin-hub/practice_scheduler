
import logging
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from keyboards import main_menu
from aiogram import F

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    text = (f"👋 Привет, {message.from_user.first_name} ! Это бот для записи на занятия курса 'Эффективные продажи'.")
    await message.answer(text, reply_markup=main_menu())


@router.callback_query(F.data == "help")
async def help_callback(callback: types.CallbackQuery):
    logger.info(f"🔍 [ПОМОЩЬ] Получен callback_query. callback_data='{callback.data}', user_id={callback.from_user.id}, username={callback.from_user.username}")
    await callback.answer()
    await callback.message.answer("По всем вопросам, в том числе и для отмены записи, обращайтесь к @alyasokolova ")

@router.message(Command("chatid"))
async def cmd_chatid(message: types.Message):
    chat_id = message.chat.id
    await message.answer(f"Chat ID: <code>{chat_id}</code>", parse_mode="HTML")