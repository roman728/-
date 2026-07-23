from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def operator_start_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="▶️ Начать смену"),
            ],
        ],
        resize_keyboard=True,
    )


def operator_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🏭 Станция 1"),
                KeyboardButton(text="🏭 Станция 2"),
            ],
            [
                KeyboardButton(text="🏭 Станция 3"),
            ],
            [
                KeyboardButton(text="📊 Состояние участка"),
            ],
            [
                KeyboardButton(text="🏁 Завершить смену"),
            ],
        ],
        resize_keyboard=True,
    )


def station_free_keyboard(
    station_number: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Загрузили раму",
                    callback_data=f"frame:load:{station_number}",
                )
            ]
        ]
    )


def station_loaded_keyboard(
    station_number: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="▶️ Начало сварки",
                    callback_data=f"frame:start:{station_number}",
                )
            ]
        ]
    )


def station_welding_keyboard(
    station_number: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏹ Окончание сварки",
                    callback_data=f"frame:finish:{station_number}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ Снять незавершённую раму",
                    callback_data=f"frame:remove:{station_number}",
                )
            ],
        ]
    )


def station_waiting_unload_keyboard(
    station_number: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Выгрузили раму",
                    callback_data=f"frame:unload:{station_number}",
                )
            ]
        ]
    )


def confirm_incomplete_removal_keyboard(
    station_number: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, снять",
                    callback_data=(
                        f"frame:remove_confirm:{station_number}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=(
                        f"frame:remove_cancel:{station_number}"
                    ),
                )
            ],
        ]
    )

def engineer_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Состояние участка"),
            ],
            [
                KeyboardButton(text="📋 Отчёт по раме"),
            ],
        ],
        resize_keyboard=True,
    )
