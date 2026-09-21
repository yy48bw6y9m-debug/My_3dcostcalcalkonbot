import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8668317945:AAGnp69pgaiZRvCUlnFxdUAvxf1S1RsKBh0"

FILAMENT_PRESETS = {
    "pla": {"name": "PLA", "default_price": 1400.0},
    "petg": {"name": "PETG", "default_price": 1300.0},
    "abs": {"name": "ABS", "default_price": 1200.0},
    "tpu": {"name": "TPU / Flex", "default_price": 2800.0},
    "nylon": {"name": "PA / Carbon", "default_price": 4500.0}
}

CONFIG = {
    "power_w": 150.0,              # Мощность принтера (Вт)
    "electricity_rate": 3.8,       # Тариф (руб/кВт⋅ч)
    "printer_cost": 68000.0,       # Стоимость принтера (руб)
    "lifespan_hours": 3500.0,      # Ресурс (часов)
    "defect_rate_percent": 5.0,    # Запас на брак/поддержки (%)
    "operator_rate_hour": 0.0    # Стоимость часа ручного труда (руб)
}

class StepCalc(StatesGroup):
    choosing_plastic = State()
    entering_price = State()
    entering_weight = State()
    entering_time = State()
    entering_postproc = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_plastics_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"{v['name']}", callback_data=f"mat_{k}")]
        for k, v in FILAMENT_PRESETS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_price_kb(default_price: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Оставить стандартную: {int(default_price)} ₽/кг", callback_data="price_default")]
        ]
    )

def calculate(weight_g: float, hours: float, post_mins: float, plastic_name: str, spool_price: float) -> str:
    plastic_cost = (weight_g / 1000.0) * spool_price * (1.0 + CONFIG["defect_rate_percent"] / 100.0)
    kwh = (CONFIG["power_w"] / 1000.0) * hours
    elec_cost = kwh * CONFIG["electricity_rate"]
    deprec_cost = (CONFIG["printer_cost"] / CONFIG["lifespan_hours"]) * hours
    labor_cost = (post_mins / 60.0) * CONFIG["operator_rate_hour"]
    total_cost = plastic_cost + elec_cost + deprec_cost + labor_cost

    return (
        f"📋 <b>Расчет для:</b> <code>{plastic_name}</code> (катушка: {int(spool_price)} ₽/кг)\n"
        f"⏱ <b>Параметры:</b> {weight_g:.1f} г | {hours:.1f} ч | {int(post_mins)} мин обработки\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧵 <b>Пластик (+{int(CONFIG['defect_rate_percent'])}% брак):</b> {plastic_cost:.2f} ₽\n"
        f"⚡ <b>Электричество ({kwh:.2f} кВт⋅ч):</b> {elec_cost:.2f} ₽\n"
        f"⚙️ <b>Амортизация принтера:</b> {deprec_cost:.2f} ₽\n"
        f"🛠 <b>Постобработка:</b> {labor_cost:.2f} ₽\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Себестоимость:</b> <b>{total_cost:.2f} ₽</b>\n\n"
        f"🏷 <b>Цены продажи:</b>\n"
        f"• Наценка 100% (x2.0): <b>{total_cost * 2:.2f} ₽</b>\n"
        f"• Наценка 150% (x2.5): <b>{total_cost * 2.5:.2f} ₽</b>\n"
        f"• Наценка 200% (x3.0): <b>{total_cost * 3:.2f} ₽</b>"
    )

# 1. СТАРТ И НАСТРОЙКИ
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 <b>Калькулятор себестоимости 3D-печати</b>\n\n"
        "• Для пошагового расчета отправьте: /calc\n"
        "• Быстрый расчет строкой: <code>вес время</code> (например: <code>120 4.5</code>)",
        parse_mode="HTML"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    await message.answer(
        f"⚙️ <b>Текущие параметры:</b>\n"
        f"• Тариф на свет: {CONFIG['electricity_rate']} ₽/кВт⋅ч\n"
        f"• Мощность принтера: {CONFIG['power_w']} Вт\n"
        f"• Стоимость принтера: {CONFIG['printer_cost']} ₽\n"
        f"• Ресурс принтера: {CONFIG['lifespan_hours']} ч"
    )

# 2. ПОШАГОВЫЙ РАСЧЕТ (/calc)
@dp.message(Command("calc"))
async def start_calc(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("1️⃣ Выберите тип пластика:", reply_markup=get_plastics_kb())
    await state.set_state(StepCalc.choosing_plastic)

@dp.callback_query(StepCalc.choosing_plastic, F.data.startswith("mat_"))
async def plastic_chosen(callback: CallbackQuery, state: FSMContext):
    mat_key = callback.data.replace("mat_", "")
    mat_info = FILAMENT_PRESETS[mat_key]
    await state.update_data(plastic_name=mat_info["name"], default_price=mat_info["default_price"])
    
    await callback.message.edit_text(
        f"Выбран пластик: <b>{mat_info['name']}</b>.\n\n"
        f"2️⃣ <b>Какая цена катушки за 1 кг (в рублях)?</b>\n"
        f"Напишите сумму в чат (например: <code>950</code>) или нажмите кнопку ниже:",
        reply_markup=get_price_kb(mat_info["default_price"]),
        parse_mode="HTML"
    )
    await state.set_state(StepCalc.entering_price)

# Вариант А: нажали кнопку цены по умолчанию
@dp.callback_query(StepCalc.entering_price, F.data == "price_default")
async def price_default_chosen(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    spool_price = data["default_price"]
    await state.update_data(spool_price=spool_price)
    await callback.message.edit_text(
        f"Цена катушки принята: <b>{int(spool_price)} ₽/кг</b>.\n\n"
        f"3️⃣ Введите <b>вес детали в граммах</b> (с поддержками):",
        parse_mode="HTML"
    )
    await state.set_state(StepCalc.entering_weight)

# Вариант Б: написали свою цену катушки вручную
@dp.message(StepCalc.entering_price, F.text)
async def price_entered_manually(message: Message, state: FSMContext):
    clean_text = message.text.replace(",", ".").strip()
    try:
        val = float(clean_text)
        if val <= 0:
            raise ValueError
        await state.update_data(spool_price=val)
        await message.answer(
            f"Цена катушки принята: <b>{int(val)} ₽/кг</b>.\n\n"
            f"3️⃣ Введите <b>вес детали в граммах</b> (с поддержками):",
            parse_mode="HTML"
        )
        await state.set_state(StepCalc.entering_weight)
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите цену числом (например: <code>950</code> или <code>1600</code>):")

@dp.message(StepCalc.entering_weight, F.text)
async def weight_entered(message: Message, state: FSMContext):
    clean_text = message.text.replace(",", ".").strip()
    try:
        val = float(clean_text)
        if val <= 0:
            raise ValueError
        await state.update_data(weight=val)
        await message.answer("4️⃣ Введите <b>время печати в часах</b> (например: <code>3.5</code>):", parse_mode="HTML")
        await state.set_state(StepCalc.entering_time)
    except ValueError:
        await message.answer("⚠️ Введите вес числом больше 0 (например: <code>85</code>):")

@dp.message(StepCalc.entering_time, F.text)
async def time_entered(message: Message, state: FSMContext):
    clean_text = message.text.replace(",", ".").strip()
    try:
        val = float(clean_text)
        if val <= 0:
            raise ValueError
        await state.update_data(hours=val)
        await message.answer("5️⃣ Введите время на <b>постобработку в минутах</b> (если нет — напишите <code>0</code>):", parse_mode="HTML")
        await state.set_state(StepCalc.entering_postproc)
    except ValueError:
        await message.answer("⚠️ Введите время в часах (например: <code>4.5</code>):")

@dp.message(StepCalc.entering_postproc, F.text)
async def postproc_entered(message: Message, state: FSMContext):
    clean_text = message.text.replace(",", ".").strip()
    try:
        val = float(clean_text)
        if val < 0:
            raise ValueError
        data = await state.get_data()
        await state.clear()
        
        res = calculate(
            weight_g=data["weight"],
            hours=data["hours"],
            post_mins=val,
            plastic_name=data["plastic_name"],
            spool_price=data["spool_price"]
        )
        await message.answer(res, parse_mode="HTML")
    except ValueError:
        await message.answer("⚠️ Введите количество минут от 0 и выше:")

# 3. БЫСТРЫЙ ВВОД В ОДНУ СТРОКУ (только если не в режиме пошагового ввода)
@dp.message(F.text.regexp(r"^\s*(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)(?:\s+(\d+(?:[.,]\d+)?))?\s*$"))
async def quick_input(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return
    parts = message.text.replace(",", ".").split()
    weight = float(parts[0])
    hours = float(parts[1])
    post = float(parts[2]) if len(parts) > 2 else 0.0
    res = calculate(
        weight_g=weight,
        hours=hours,
        post_mins=post,
        plastic_name="PLA",
        spool_price=FILAMENT_PRESETS["pla"]["default_price"]
    )
    await message.answer(res, parse_mode="HTML")

# Сервер для Render
async def handle_ping(request):
    return web.Response(text="OK")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
