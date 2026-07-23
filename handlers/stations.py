from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import (
    finish_welding,
    get_active_frame_by_station,
    get_active_session,
    get_user_by_telegram_id,
    load_frame,
    remove_incomplete_frame,
    start_welding,
    unload_frame,
)
from keyboards import (
    confirm_incomplete_removal_keyboard,
    station_free_keyboard,
    station_loaded_keyboard,
    station_waiting_unload_keyboard,
    station_welding_keyboard,
)
from states import FrameStates


router = Router()


async def send_station_state(
    message: Message,
    station_number: int,
) -> None:
    frame = get_active_frame_by_station(station_number)

    if frame is None:
        await message.answer(
            f"🏭 Станция {station_number}\n\n"
            "Станция свободна.",
            reply_markup=station_free_keyboard(station_number),
        )
        return

    frame_number = frame["frame_number"]
    status = frame["status"]

    if status == "loaded":
        await message.answer(
            f"🏭 Станция {station_number}\n\n"
            f"Рама №{frame_number}\n"
            "Статус: 📦 загружена\n\n"
            "Следующее действие:",
            reply_markup=station_loaded_keyboard(station_number),
        )
        return

    if status == "welding":
        await message.answer(
            f"🏭 Станция {station_number}\n\n"
            f"Рама №{frame_number}\n"
            "Статус: 🔥 идёт сварка",
            reply_markup=station_welding_keyboard(station_number),
        )
        return

    if status == "waiting_unload":
        await message.answer(
            f"🏭 Станция {station_number}\n\n"
            f"Рама №{frame_number}\n"
            "Статус: ⏳ сварка окончена\n"
            "Ожидает выгрузку.",
            reply_markup=station_waiting_unload_keyboard(
                station_number
            ),
        )


@router.message(F.text.regexp(r"^.*Станция [123]$"))
async def open_station_handler(
    message: Message,
    state: FSMContext,
) -> None:
    user = get_user_by_telegram_id(message.from_user.id)

    if user is None or user["role"] != "operator":
        await message.answer(
            "⛔ Эта команда доступна только оператору."
        )
        return

    session = get_active_session(user["id"])

    if session is None:
        await message.answer(
            "Сначала нажмите «▶️ Начать смену»."
        )
        return

    await state.clear()

    station_number = int(
        message.text.rsplit(" ", 1)[-1]
    )

    await send_station_state(
        message=message,
        station_number=station_number,
    )


@router.message(F.text == "📊 Состояние участка")
async def area_status_handler(message: Message) -> None:
    user = get_user_by_telegram_id(message.from_user.id)

    if user is None or user["role"] not in {
        "operator",
        "engineer",
        "admin",
    }:
        await message.answer(
            "⛔ У вас нет доступа к этой функции."
        )
        return

    if user["role"] == "operator":
        session = get_active_session(user["id"])

        if session is None:
            await message.answer(
                "Сначала нажмите «▶️ Начать смену»."
            )
            return

    status_names = {
        "loaded": "📦 Загружена",
        "welding": "🔥 Идёт сварка",
        "waiting_unload": "⏳ Ожидает выгрузку",
    }

    lines = [
        "📊 СОСТОЯНИЕ УЧАСТКА",
        "",
    ]

    for station_number in (1, 2, 3):
        frame = get_active_frame_by_station(
            station_number
        )

        if frame is None:
            lines.append(
                f"🏭 Станция {station_number}\n"
                "Свободна"
            )
        else:
            status_text = status_names.get(
                frame["status"],
                frame["status"],
            )

            lines.append(
                f"🏭 Станция {station_number}\n"
                f"Рама №{frame['frame_number']}\n"
                f"{status_text}"
            )

        if station_number != 3:
            lines.append("────────────")

    await message.answer("\n".join(lines))


@router.callback_query(F.data.startswith("frame:"))
async def frame_action_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()

    user = get_user_by_telegram_id(
        callback.from_user.id
    )

    if user is None or user["role"] != "operator":
        await callback.message.answer(
            "⛔ Это действие доступно только оператору."
        )
        return

    session = get_active_session(user["id"])

    if session is None:
        await callback.message.answer(
            "Сначала начните смену."
        )
        return

    parts = callback.data.split(":")

    if len(parts) != 3:
        await callback.message.answer(
            "Некорректная команда."
        )
        return

    action = parts[1]
    station_number = int(parts[2])

    try:
        if action == "load":
            frame = get_active_frame_by_station(
                station_number
            )

            if frame is not None:
                await callback.message.answer(
                    "На этой станции уже находится рама."
                )
                return

            await state.set_state(
                FrameStates.waiting_for_frame_number
            )
            await state.update_data(
                station_number=station_number
            )

            await callback.message.answer(
                f"🏭 Станция {station_number}\n\n"
                "Введите номер рамы:"
            )
            return

        if action == "start":
            start_welding(
                station_number=station_number,
                operator_id=user["id"],
                session_id=session["id"],
            )

            await callback.message.answer(
                "✅ Начало сварки записано."
            )

        elif action == "finish":
            finish_welding(
                station_number=station_number,
                operator_id=user["id"],
                session_id=session["id"],
            )

            await callback.message.answer(
                "✅ Окончание сварки записано."
            )

        elif action == "unload":
            unload_frame(
                station_number=station_number,
                operator_id=user["id"],
                session_id=session["id"],
            )

            await callback.message.answer(
                "✅ Рама выгружена.\n"
                "Станция снова свободна."
            )

        elif action == "remove":
            frame = get_active_frame_by_station(
                station_number
            )

            if (
                frame is None
                or frame["status"] != "welding"
            ):
                await callback.message.answer(
                    "На станции нет рамы "
                    "в процессе сварки."
                )
                return

            await callback.message.answer(
                f"⚠️ Рама №{frame['frame_number']} "
                "ещё не доварена.\n\n"
                "Снять её со станции и передать "
                "на ручную доварку?",
                reply_markup=(
                    confirm_incomplete_removal_keyboard(
                        station_number
                    )
                ),
            )
            return

        elif action == "remove_confirm":
            remove_incomplete_frame(
                station_number=station_number,
                operator_id=user["id"],
                session_id=session["id"],
            )

            await callback.message.answer(
                "⚠️ Рама снята незавершённой.\n"
                "Она передана на ручную доварку.\n\n"
                "Станция снова свободна."
            )

        elif action == "remove_cancel":
            await callback.message.answer(
                "Снятие рамы отменено."
            )

        else:
            await callback.message.answer(
                "Неизвестное действие."
            )
            return

    except ValueError as error:
        await callback.message.answer(
            f"⚠️ {error}"
        )
        return

    await send_station_state(
        message=callback.message,
        station_number=station_number,
    )


@router.message(
    FrameStates.waiting_for_frame_number
)
async def frame_number_handler(
    message: Message,
    state: FSMContext,
) -> None:
    user = get_user_by_telegram_id(
        message.from_user.id
    )

    if user is None or user["role"] != "operator":
        await state.clear()
        await message.answer("⛔ Нет доступа.")
        return

    session = get_active_session(user["id"])

    if session is None:
        await state.clear()
        await message.answer(
            "Сначала начните смену."
        )
        return

    data = await state.get_data()
    station_number = data.get("station_number")

    if station_number is None:
        await state.clear()
        await message.answer(
            "Не удалось определить станцию."
        )
        return

    frame_number = (message.text or "").strip()

    try:
        load_frame(
            frame_number=frame_number,
            station_number=station_number,
            operator_id=user["id"],
            session_id=session["id"],
        )

    except ValueError as error:
        await message.answer(
            f"⚠️ {error}\n\n"
            "Введите номер рамы ещё раз:"
        )
        return

    await state.clear()

    await message.answer(
        f"✅ Рама №{frame_number} загружена "
        f"на станцию {station_number}."
    )

    await send_station_state(
        message=message,
        station_number=station_number,
    )
