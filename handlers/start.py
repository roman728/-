from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from database import (
    get_active_session,
    get_user_by_telegram_id,
)
from keyboards import (
    engineer_main_keyboard,
    operator_main_keyboard,
    operator_start_keyboard,
)


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user = get_user_by_telegram_id(message.from_user.id)

    if user is None:
        await message.answer(
            "⛔ У вас пока нет доступа к Robot Journal.\n\n"
            f"Ваш Telegram ID: {message.from_user.id}\n\n"
            "Передайте этот ID администратору."
        )
        return

    if not user["is_active"]:
        await message.answer(
            "⛔ Ваш доступ к боту отключён."
        )
        return

    # Главный оператор
    if user["role"] == "operator":
        active_session = get_active_session(user["id"])

        if active_session is not None:
            await message.answer(
                f"Здравствуйте, {user['full_name']}!\n\n"
                "У вас уже есть активная смена.",
                reply_markup=operator_main_keyboard(),
            )
        else:
            await message.answer(
                f"Здравствуйте, {user['full_name']}!\n\n"
                "Нажмите кнопку, чтобы начать смену.",
                reply_markup=operator_start_keyboard(),
            )

        return

    # Инженер
    if user["role"] == "engineer":
        await message.answer(
            f"Здравствуйте, {user['full_name']}!\n\n"
            "Ваша роль: 👨‍🔧 Инженер",
            reply_markup=engineer_main_keyboard(),
        )
        return

    # Администратор получает доступ к демонстрации
    # полного рабочего цикла оператора.
    if user["role"] == "admin":
        active_session = get_active_session(user["id"])

        if active_session is not None:
            await message.answer(
                f"Здравствуйте, {user['full_name']}!\n\n"
                "Ваша роль: ⚙️ Администратор\n"
                "У вас уже есть активная смена.",
                reply_markup=operator_main_keyboard(),
            )
        else:
            await message.answer(
                f"Здравствуйте, {user['full_name']}!\n\n"
                "Ваша роль: ⚙️ Администратор\n\n"
                "Нажмите кнопку, чтобы начать демонстрацию.",
                reply_markup=operator_start_keyboard(),
            )

        return

    await message.answer(
        "Не удалось определить вашу роль."
    )
