
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from notifier import Notifier
import threading
from aiogram.filters import Command
from aiogram.types import Message
from aiogram import types
from aiogram import Router

from config import config
from handlers.start import router as start_router
from handlers.booking import router as booking_router
from handlers.mybookings import router as my_bookings_router
# from middleware.chat_member import ChatMembershipMiddleware

dp = Dispatcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

\
notify_router = Router()

@notify_router.message(Command("notify"))
async def cmd_notify(message: types.Message):
    """Ручной запуск уведомлений"""
    notifier = Notifier()
    await notifier.run()
    await message.answer("✅ Уведомления проверены и отправлены")

def run_notifier_in_thread():
    """Запускает notifier в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def task():
        logger = logging.getLogger(__name__)
        while True:
            try:
                logger.info("🔍 Notifier: checking for reminders...")
                notifier = Notifier()
                await notifier.run()
            except Exception as e:
                logger.error(f"❌ Notifier error: {e}")
            await asyncio.sleep(1800)

    loop.run_until_complete(task())



async def main():
    logger = logging.getLogger(__name__)
    logger.info("🚀 Запуск бота...")

    # хранилище состояний FSM
    storage = MemoryStorage()

    # диспетчер с хранилищем
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=storage)


    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(my_bookings_router)
    dp.include_router(notify_router)

    notifier_thread = threading.Thread(target=run_notifier_in_thread, daemon=True)
    notifier_thread.start()
    logger.info("✅ Фоновые уведомления запущены")


    # dp.message.middleware(ChatMembershipMiddleware())
    # dp.callback_query.middleware(ChatMembershipMiddleware())

    logger.info(f"✅ Бот создан. Токен: {config.BOT_TOKEN[:10]}...")
    logger.info("📱 Бот запускается...")


    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())