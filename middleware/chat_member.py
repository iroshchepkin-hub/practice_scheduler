#
# from aiogram import BaseMiddleware
# from aiogram.types import Message, CallbackQuery
# from typing import Callable, Dict, Any, Awaitable
# from config import config
#
#
# class ChatMembershipMiddleware(BaseMiddleware):
#     """Пользователь состоит в нужном чате"""
#
#     async def __call__(
#             self,
#             handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
#             event: Message | CallbackQuery,
#             data: Dict[str, Any]
#     ) -> Any:
#         bot = data['bot']
#
#         try:
#             # Проверяем членство в чате
#             chat_member = await bot.get_chat_member(
#                 chat_id=config.ALLOWED_CHAT_ID,
#                 user_id=event.from_user.id
#             )
#
#             # Если пользователь в чате (member, administrator, creator)
#             if chat_member.status in ['member', 'administrator', 'creator']:
#                 return await handler(event, data)
#             else:
#                 # Не в чате
#                 if isinstance(event, Message):
#                     await event.answer(
#                         "❌ <b>Доступ запрещён</b>\n\n",
#                         parse_mode="HTML",
#                         disable_web_page_preview=True
#                     )
#                 elif isinstance(event, CallbackQuery):
#                     await event.answer(
#                         "❌ Вы не участник чата",
#                         show_alert=True
#                     )
#                 return
#
#         except Exception as e:
#             error_msg = (
#                 "⚠️ <b>Не удалось проверить доступ</b>"
#             )
#
#             if isinstance(event, Message):
#                 await event.answer(error_msg, parse_mode="HTML")
#             elif isinstance(event, CallbackQuery):
#                 await event.message.answer(error_msg, parse_mode="HTML")
#
#             return