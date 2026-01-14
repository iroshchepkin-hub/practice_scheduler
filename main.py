
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers.start import router as start_router
from handlers.booking import router as booking_router
from handlers.mybookings import router as my_bookings_router
# from middleware.chat_member import ChatMembershipMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


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

    # dp.message.middleware(ChatMembershipMiddleware())
    # dp.callback_query.middleware(ChatMembershipMiddleware())

    logger.info(f"✅ Бот создан. Токен: {config.BOT_TOKEN[:10]}...")
    logger.info("📱 Бот запускается...")


    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())