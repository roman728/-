import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import (
    ADMIN_TELEGRAM_ID,
    BOT_TOKEN,
    ENGINEER_TELEGRAM_ID,
    OPERATOR_EGOR_ID,
    OPERATOR_IGOR_ID,
    OPERATOR_YAROSLAV_ID,
)
from database import (
    create_tables,
    seed_initial_users,
)
from handlers import (
    engineer_router,
    operator_router,
    start_router,
    station_router,
)


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден. Проверьте файл .env "
            "или переменные Railway."
        )

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    # Создание таблиц базы данных.
    create_tables()

    # Добавление администратора, инженера и операторов
    # из переменных окружения Railway.
    seed_initial_users(
        admin_telegram_id=ADMIN_TELEGRAM_ID,
        engineer_telegram_id=ENGINEER_TELEGRAM_ID,
        operator_egor_id=OPERATOR_EGOR_ID,
        operator_yaroslav_id=OPERATOR_YAROSLAV_ID,
        operator_igor_id=OPERATOR_IGOR_ID,
    )

    bot = Bot(token=BOT_TOKEN)
    dispatcher = Dispatcher()

    dispatcher.include_router(start_router)
    dispatcher.include_router(engineer_router)
    dispatcher.include_router(operator_router)
    dispatcher.include_router(station_router)

    print("Robot Journal запущен")

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
