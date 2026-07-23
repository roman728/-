from aiogram import Bot, F, Router
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
)
from aiogram.types import Message

from database import (
    finish_session,
    get_active_session,
    get_active_users_by_role,
    get_shift_report_data,
    get_user_by_telegram_id,
    start_session,
)
from keyboards import (
    operator_main_keyboard,
    operator_start_keyboard,
)
from services import build_shift_report


router = Router()


@router.message(F.text == "▶️ Начать смену")
async def start_work_session_handler(message: Message) -> None:
    user = get_user_by_telegram_id(message.from_user.id)

    if user is None or user["role"] != "operator":
        await message.answer(
            "⛔ Эта команда доступна только оператору."
        )
        return

    session_id = start_session(user["id"])

    await message.answer(
        "✅ Смена начата.\n\n"
        f"Оператор: {user['full_name']}\n"
        f"Номер смены в системе: {session_id}",
        reply_markup=operator_main_keyboard(),
    )


@router.message(F.text == "🏁 Завершить смену")
async def finish_work_session_handler(
    message: Message,
    bot: Bot,
) -> None:
    user = get_user_by_telegram_id(message.from_user.id)

    if user is None or user["role"] != "operator":
        await message.answer(
            "⛔ Эта команда доступна только оператору."
        )
        return

    active_session = get_active_session(user["id"])

    if active_session is None:
        await message.answer(
            "У вас нет активной смены.",
            reply_markup=operator_start_keyboard(),
        )
        return

    finished_session = finish_session(user["id"])

    if finished_session is None:
        await message.answer(
            "Не удалось завершить смену."
        )
        return

    report_data = get_shift_report_data(
        finished_session["id"]
    )
    report_text = build_shift_report(report_data)

    # Показываем отчёт оператору.
    await message.answer(
        report_text,
        reply_markup=operator_start_keyboard(),
    )

    # Отправляем отчёт всем активным инженерам.
    engineers = get_active_users_by_role("engineer")
    delivered_to = []

    for engineer in engineers:
        try:
            await bot.send_message(
                chat_id=engineer["telegram_id"],
                text=report_text,
            )
            delivered_to.append(engineer["full_name"])

        except (
            TelegramForbiddenError,
            TelegramBadRequest,
        ):
            # Например, инженер ещё не нажал /start
            # или заблокировал бота.
            continue

    if delivered_to:
        await message.answer(
            "✅ Отчёт автоматически отправлен инженеру:\n"
            + ", ".join(delivered_to)
        )
    else:
        await message.answer(
            "⚠️ Отчёт сформирован, но отправить его "
            "инженеру не удалось.\n\n"
            "Инженер должен открыть этого бота "
            "и один раз нажать /start."
        )
