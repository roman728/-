from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from database import (
    get_all_items,
    get_low_items,
    change_quantity,
    get_history,
    get_item,
)
from keyboards import main_menu, items_keyboard, back_keyboard

router = Router()


class OperationState(StatesGroup):
    waiting_amount = State()


def status_icon(quantity: int, min_quantity: int) -> str:
    if quantity <= min_quantity:
        return "🔴"
    if quantity <= min_quantity * 2:
        return "🟡"
    return "🟢"


def stock_text() -> str:
    items = get_all_items()

    text = "🔧 РобоСклад\n\n📦 Расходники для роботов:\n\n"

    for item_id, name, unit, quantity, min_quantity in items:
        icon = status_icon(quantity, min_quantity)
        text += (
            f"{icon} {name}\n"
            f"Остаток: {quantity} {unit}\n"
            f"Минимум: {min_quantity} {unit}\n\n"
        )

    return text


@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🔧 РобоСклад\n\n"
        "Прототип для учёта расходников роботизированного участка.\n\n"
        "Выберите действие:",
        reply_markup=main_menu(),
    )
    await message.answer(stock_text(), reply_markup=back_keyboard())


@router.message(F.text == "📦 Остатки")
async def show_stock(message: Message):
    await message.answer(stock_text(), reply_markup=back_keyboard())


@router.message(F.text == "⚠ Заканчивается")
async def show_low(message: Message):
    items = get_low_items()

    if not items:
        await message.answer("✅ Всё в норме. Критичных остатков нет.", reply_markup=back_keyboard())
        return

    text = "⚠ Требуется пополнение:\n\n"

    for item_id, name, unit, quantity, min_quantity in items:
        text += (
            f"🔴 {name}\n"
            f"Осталось: {quantity} {unit}\n"
            f"Минимум: {min_quantity} {unit}\n\n"
        )

    await message.answer(text, reply_markup=back_keyboard())


@router.message(F.text == "➖ Списать")
async def writeoff_start(message: Message):
    await message.answer(
        "➖ Что списать?",
        reply_markup=items_keyboard("writeoff"),
    )


@router.message(F.text == "➕ Пополнить")
async def add_start(message: Message):
    await message.answer(
        "➕ Что пополнить?",
        reply_markup=items_keyboard("add"),
    )


@router.callback_query(F.data.startswith("writeoff:"))
async def choose_writeoff(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    item = get_item(item_id)

    if not item:
        await callback.message.answer("Расходник не найден.")
        await callback.answer()
        return

    _, name, unit, quantity, min_quantity = item

    await state.update_data(item_id=item_id, action="writeoff")
    await state.set_state(OperationState.waiting_amount)

    await callback.message.answer(
        f"➖ Списание\n\n"
        f"Расходник: {name}\n"
        f"Сейчас в остатке: {quantity} {unit}\n\n"
        f"Введите количество цифрой:",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("add:"))
async def choose_add(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    item = get_item(item_id)

    if not item:
        await callback.message.answer("Расходник не найден.")
        await callback.answer()
        return

    _, name, unit, quantity, min_quantity = item

    await state.update_data(item_id=item_id, action="add")
    await state.set_state(OperationState.waiting_amount)

    await callback.message.answer(
        f"➕ Пополнение\n\n"
        f"Расходник: {name}\n"
        f"Сейчас в остатке: {quantity} {unit}\n\n"
        f"Введите количество цифрой:",
    )
    await callback.answer()


@router.message(OperationState.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.strip())

        if amount <= 0:
            await message.answer("Количество должно быть больше нуля.")
            return

    except ValueError:
        await message.answer("Введите только число. Например: 3")
        return

    data = await state.get_data()
    item_id = data["item_id"]
    action = data["action"]

    if action == "writeoff":
        success, result = change_quantity(item_id, -amount, "Списание")
        title = "✅ Списание выполнено"
    else:
        success, result = change_quantity(item_id, amount, "Пополнение")
        title = "✅ Пополнение выполнено"

    await state.clear()

    if not success:
        await message.answer(f"❌ {result}", reply_markup=main_menu())
        return

    await message.answer(
        f"{title}\n\n"
        f"Расходник: {result['name']}\n"
        f"Количество: {result['amount']} {result['unit']}\n\n"
        f"Было: {result['before']} {result['unit']}\n"
        f"Стало: {result['after']} {result['unit']}",
        reply_markup=main_menu(),
    )

    if result["after"] <= result["min_quantity"]:
        await message.answer(
            f"⚠ Внимание\n\n"
            f"{result['name']} заканчивается.\n"
            f"Осталось: {result['after']} {result['unit']}\n"
            f"Минимум: {result['min_quantity']} {result['unit']}"
        )


@router.message(F.text == "📜 История")
async def show_history(message: Message):
    rows = get_history()

    if not rows:
        await message.answer("История пока пустая.", reply_markup=back_keyboard())
        return

    text = "📜 Последние операции:\n\n"

    for item_name, action, amount, before_qty, after_qty, created_at in rows:
        text += (
            f"{created_at}\n"
            f"{action}: {item_name}\n"
            f"Количество: {amount}\n"
            f"Было: {before_qty} → Стало: {after_qty}\n"
            f"────────────\n"
        )

    await message.answer(text, reply_markup=back_keyboard())


@router.callback_query(F.data == "back:main")
async def back_main(callback: CallbackQuery):
    await callback.message.answer(
        "🔧 РобоСклад\n\nВыберите действие:",
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.message()
async def unknown_message(message: Message):
    await message.answer(
        "Выберите действие кнопкой ниже.",
        reply_markup=main_menu(),
    )
