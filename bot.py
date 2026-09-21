import os
import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

# Токен бота
BOT_TOKEN = "8668317945:AAGEWGh8BhD7OiD5jR2J-BL0vPq7zWDSAZE"

# Базовые параметры оборудования
CONFIG = {
    "power_w": 200.0,              # Средняя мощность принтера (Вт)
    "electricity_rate": 5.5,       # Тариф (руб/кВт⋅ч)
    "printer_cost": 68000.0,       # Стоимость принтера (руб)
    "lifespan_hours": 3500.0,      # Ресурс (часов)
    "defect_rate_percent": 5.0,    # Брак / продувка / кайма (%)
    "operator_rate_hour": 500.0    # Стоимость часа ручного труда (руб)
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def calculate(spool_price: float, weight_g: float, hours: float, post_mins: float = 0.0) -> str:
    # 1. Сырье с учетом брака
    plastic_cost = (weight_g / 1000.0) * spool_price * (1.0 + CONFIG["defect_rate_percent"] / 100.0)
    # 2. Электроэнергия
    kwh = (CONFIG["power_w"] / 1000.0) * hours
    elec_cost = kwh * CONFIG["electricity_rate"]
    # 3. Износ принтера
    deprec_cost = (CONFIG["printer_cost"] / CONFIG["lifespan_hours"]) * hours
    # 4. Ручная работа
    labor_cost = (post_mins / 60.0) * CONFIG["operator_rate_hour"]
    
    total_cost = plastic_cost + elec_cost + deprec_cost + labor_cost

    return (
        f"📊 <b>Результат расчета:</b>\n\n"
        f"• Катушка: <code>{int(spool_price)} ₽/кг</code>\n"
        f"• Вес: <code>{weight_g:.1f} г</code>\n"
        f"• Время печати: <code>{hours:.1f} ч</code>\n"
        f"• Постобработка: <code>{int(post_mins)} мин</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧵 Пластик (+{int(CONFIG['defect_rate_percent'])}% брак): <code>{plastic_cost:.2f} ₽</code>\n"
        f"⚡ Свет ({kwh:.2f} кВт⋅ч): <code>{elec_cost:.2f} ₽</code>\n"
        f"⚙️ Амортизация: <code>{deprec_cost:.2f} ₽</code>\n"
        f"🛠 Постобработка: <code>{labor_cost:.2f} ₽</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 <b>Себестоимость:</b> <b>{total_cost:.2f} ₽</b>\n\n"
        f"🏷 <b>Цены продажи с наценкой:</b>\n"
        f"• Наценка 100% (x2.0): <b>{total_cost * 2:.2f} ₽</b> <i>(прибыль {total_cost:.2f} ₽)</i>\n"
        f"• Наценка 150% (x2.5): <b>{total_cost * 2.5:.2f} ₽</b> <i>(прибыль {total_cost * 1.5:.2f} ₽)</i>\n"
        f"• Наценка 200% (x3.0): <b>{total_cost * 3:.2f} ₽</b> <i>(прибыль {total_cost * 2:.2f} ₽)</i>"
    )

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>Калькулятор себестоимости 3D-печати</b>\n\n"
        "Отправьте данные через пробел в формате:\n"
        "<code>цена_катушки вес время [постобработка]</code>\n\n"
        "<b>Примеры:</b>\n"
        "• <code>865 191 6</code> (катушка 865 ₽, 191 г, 6 часов)\n"
        "• <code>1200 85 3.5 15</code> (катушка 1200 ₽, 85 г, 3.5 ч, 15 мин обработка)\n\n"
        "⚙️ Параметры оборудования: /settings",
        parse_mode="HTML"
    )

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    await message.answer(
        f"⚙️ <b>Параметры принтера:</b>\n"
        f"• Свет: {CONFIG['electricity_rate']} ₽/кВт⋅ч\n"
        f"• Мощность: {CONFIG['power_w']} Вт\n"
        f"• Стоимость оборудования: {CONFIG['printer_cost']} ₽\n"
        f"• Ресурс: {CONFIG['lifespan_hours']} ч\n"
        f"• Ставка постобработки: {CONFIG['operator_rate_hour']} ₽/час"
    )

@dp.message(F.text)
async def handle_calc_text(message: Message):
    text = message.text.replace(",", ".").strip()
    parts = text.split()
    
    # Обрабатываем 3 или 4 числа: цена, вес, время, [постобработка]
    if len(parts) in (3, 4):
        try:
            spool_price = float(parts[0])
            weight_g = float(parts[1])
            hours = float(parts[2])
            post_mins = float(parts[3]) if len(parts) == 4 else 0.0

            if spool_price <= 0 or weight_g <= 0 or hours <= 0 or post_mins < 0:
                await message.answer("⚠️ Все значения должны быть больше нуля (постобработка от 0).")
                return

            res = calculate(spool_price, weight_g, hours, post_mins)
            await message.answer(res, parse_mode="HTML")
            return
        except ValueError:
            pass

    await message.answer(
        "⚠️ <b>Неверный формат ввода.</b>\n\n"
        "Отправьте 3 или 4 числа через пробел:\n"
        "<code>цена_катушки вес время [минуты_обработки]</code>\n\n"
        "<i>Пример:</i> <code>865 191 6</code>",
        parse_mode="HTML"
    )

# Простой эндпоинт для работы на Render
async def handle_ping(request):
    return web.Response(text="OK")

async def main():
    # Запуск фонового веб-сервера
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    # 🔴 Принудительный сброс чужих вебхуков и подвисших сообщений
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

