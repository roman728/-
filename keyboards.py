from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_all_items


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Остатки")],
            [KeyboardButton(text="➖ Списать"), KeyboardButton(text="➕ Пополнить")],
            [KeyboardButton(text="⚠ Заканчивается"), KeyboardButton(text="📜 История")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def items_keyboard(prefix: str):
    rows = []

    for item_id, name, unit, quantity, min_quantity in get_all_items():
        rows.append([
            InlineKeyboardButton(
                text=f"{name} — {quantity} {unit}",
                callback_data=f"{prefix}:{item_id}",
            )
        ])

    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back:main")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ В главное меню", callback_data="back:main")]
        ]
    )
