import asyncio
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import init_db
from handlers import router


async def main():
    init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    print("РобоСклад запущен. Открой Telegram и напиши боту /start")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
