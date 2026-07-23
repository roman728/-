import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import create_tables
from handlers import (
    engineer_router,
    operator_router,
    start_router,
    station_router,
)


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден в файле .env"
        )

    logging.basicConfig(level=logging.INFO)

    create_tables()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(engineer_router)
    dp.include_router(operator_router)
    dp.include_router(station_router)

    print("Robot Journal запущен")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
