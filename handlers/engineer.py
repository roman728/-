from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import (
    get_frame_report_data,
    get_user_by_telegram_id,
)
from services import build_frame_report
from states import EngineerStates


router = Router()


@router.message(F.text.regexp(r"^.*Отчёт по раме$"))
async def request_frame_number_handler(
    message: Message,
    state: FSMContext,
) -> None:
    user = get_user_by_telegram_id(message.from_user.id)

    if user is None or user["role"] not in {
        "engineer",
        "admin",
    }:
        await message.answer(
            "⛔ Эта функция доступна только инженеру."
        )
        return

    await state.clear()
    await state.set_state(
        EngineerStates.waiting_for_frame_number
    )

    await message.answer(
        "📋 Введите номер рамы:"
    )


@router.message(
    EngineerStates.waiting_for_frame_number
)
async def show_frame_report_handler(
    message: Message,
    state: FSMContext,
) -> None:
    user = get_user_by_telegram_id(message.from_user.id)

    if user is None or user["role"] not in {
        "engineer",
        "admin",
    }:
        await state.clear()
        await message.answer("⛔ Нет доступа.")
        return

    frame_number = (message.text or "").strip()

    if frame_number.startswith("№"):
        frame_number = frame_number[1:].strip()

    if not frame_number:
        await message.answer(
            "Введите номер рамы:"
        )
        return

    frame = get_frame_report_data(frame_number)

    if frame is None:
        await message.answer(
            f"❌ Рама №{frame_number} не найдена.\n\n"
            "Проверьте номер и введите его ещё раз."
        )
        return

    await state.clear()

    await message.answer(
        build_frame_report(frame)
    )
