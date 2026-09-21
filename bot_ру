import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# 🔴 ВСТАВЬТЕ ВАШ ТОКЕН
BOT_TOKEN = "8668317945:AAGnp69pgaiZRvCUlnFxdUAvxf1S1RsKBh0"

FILAMENT_PRESETS = {
    "pla": {"name": "PLA", "price": 1400.0},
    "petg": {"name": "PETG", "price": 1300.0},
    "abs": {"name": "ABS", "price": 1200.0},
    "tpu": {"name": "TPU / Flex", "price": 2800.0},
    "nylon": {"name": "PA / Carbon", "price": 4500.0}
}

CONFIG = {
    "power_w": 150.0,
    "electricity_rate": 5.5,
    "printer_cost": 65000.0,
    "lifespan_hours": 3500.0,
    "defect_rate_percent": 5.0,
    "operator_rate_hour": 500.0
}

class StepCalc(StatesGroup):
    choosing_plastic = State()
    entering_weight = State()
    entering_time = State()
    entering_postproc = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def get_plastics_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"{v['name']} (~{int(v['price'])} ₽/кг)", callback_data=f"mat_{k}")]
        for k, v in FILAMENT_PRESETS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def calculate(weight_g: float, hours: float, post_mins: float, plastic_key: str = "pla") -> str:
    mat = FILAMENT_PRESETS.get(plastic_key, FILAMENT_PRESETS["pla"])
    plastic_cost = (weight_g / 1000.0) * mat["price"] * (1.0 + CONFIG["defect_rate_percent"] / 100.0)
    kwh = (CONFIG["power_w"] / 1000.0) * hours
    elec_cost = kwh * CONFIG["electricity_rate"]
    deprec_cost = (CONFIG["printer_cost"] / CONFIG["lifespan_hours"]) * hours
    labor_cost = (post_mins / 60.0) * CONFIG["operator_rate_hour"]
    total_cost = plastic_cost + elec_cost + deprec_cost + labor_cost

    return (
        f"📋 <b>Расчет для:</b> <code>{mat['name']}</code>\n"
        f"⏱ <b>Параметры:</b> {weight_g:.1f} г | {hours:.1f} ч | {int(post_mins)} мин обработки\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧵 <b>Пластик:</b> {plastic_cost:.2f} ₽\n"
        f"⚡ <b>Электричество:</b> {elec_cost:.2f} ₽\n"
        f"⚙️ <b>Амортизация:</b> {deprec_cost:.2f} ₽\n"
        f"🛠 <b>Постобработка:</b> {labor_cost:.2f} ₽\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Себестоимость:</b> <b>{total_cost:.2f} ₽</b>\n\n"
        f"🏷 <b>Цены продажи:</b>\n"
        f"• x2.0: <b>{total_cost * 2:.2f} ₽</b>\n"
        f"• x2.5: <b>{total_cost * 2.5:.2f} ₽</b>\n"
        f"• x3.0: <b>{total_cost * 3:.2f} ₽</b>"
    )

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 Калькулятор 3D-печати готов к работе!\n\nОтправьте <code>вес время</code> (например: <code>100 4.5</code>) или команду /calc", parse_mode="HTML")

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    await message.answer(f"⚙️ Тариф: {CONFIG['electricity_rate']} ₽ | Принтер: {CONFIG['printer_cost']} ₽ | Ресурс: {CONFIG['lifespan_hours']} ч")

@dp.message(Command("calc"))
async def start_calc(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите пластик:", reply_markup=get_plastics_kb())
    await state.set_state(StepCalc.choosing_plastic)

@dp.callback_query(F.data.startswith("mat_"), StepCalc.choosing_plastic)
async def plastic_chosen(callback: CallbackQuery, state: FSMContext):
    mat_key = callback.data.replace("mat_", "")
    await state.update_data(plastic=mat_key)
    await callback.message.edit_text(f"Выбран: <b>{FILAMENT_PRESETS[mat_key]['name']}</b>.\n\nВведите вес в граммах:", parse_mode="HTML")
    await state.set_state(StepCalc.entering_weight)

@dp.message(StepCalc.entering_weight)
async def weight_entered(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(weight=val)
        await message.answer("Введите время печати в часах:")
        await state.set_state(StepCalc.entering_time)
    except ValueError:
        await message.answer("Введите число:")

@dp.message(StepCalc.entering_time)
async def time_entered(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        await state.update_data(hours=val)
        await message.answer("Время постобработки в минутах (или 0):")
        await state.set_state(StepCalc.entering_postproc)
    except ValueError:
        await message.answer("Введите число:")

@dp.message(StepCalc.entering_postproc)
async def postproc_entered(message: Message, state: FSMContext):
    try:
        val = float(message.text.replace(",", "."))
        data = await state.get_data()
        await state.clear()
        res = calculate(data["weight"], data["hours"], val, data["plastic"])
        await message.answer(res, parse_mode="HTML")
    except ValueError:
        await message.answer("Введите число минут:")

@dp.message(F.text.regexp(r"^\s*(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)(?:\s+(\d+(?:[.,]\d+)?))?\s*$"))
async def quick_input(message: Message, state: FSMContext):
    await state.clear()
    parts = message.text.replace(",", ".").split()
    weight = float(parts[0])
    hours = float(parts[1])
    post = float(parts[2]) if len(parts) > 2 else 0.0
    res = calculate(weight, hours, post, "pla")
    await message.answer(res, parse_mode="HTML")

# Веб-сервер для бесплатного тарифа Render
async def handle_ping(request):
    return web.Response(text="Bot is running!")

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
