import asyncio
from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile

import os
import logging
from datetime import datetime

from Utils import get_API_key, get_today_date, count_water, count_calorie, get_food_info, plot_stat

TOKEN = get_API_key("api_tg.txt")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        logger.info(f"user_id={event.from_user.id} | "
                    f"username={event.from_user.username} | "
                    f"text={event.text}")
        return await handler(event, data)

dp.message.middleware(LoggingMiddleware())

users_data = {}
water_data = {}
train_data = {}
cal_data = {}

def reset_daily():
    today = get_today_date()
    for user_id in water_data:
        if water_data[user_id].get("date") != today:
            water_data[user_id] = {"today": 0, "history": [], "goal": water_data[user_id].get("goal", 2000), "date": today}
        if train_data[user_id].get("date") != today:
            train_data[user_id] = {"today": 0, "history": [], "goal": train_data[user_id].get("goal", 2000), "date": today}

class ProfileForm(StatesGroup):
    weight = State()
    height = State()
    age = State()
    sex = State()
    activity = State()
    city = State()
    calories = State()

class FoodForm(StatesGroup):
    food_name = State()
    food_cal = State()
    weight = State()

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Привет! Я трекер твоих новых привычек!")

@dp.message(Command("set_profile"))
async def start_profile(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Введите Ваш вес (в кг):")
    await state.set_state(ProfileForm.weight)

@dp.message(ProfileForm.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight <= 0 or weight > 300:
            await message.answer("Введите корректный вес (0-300 кг):")
            return
    except ValueError:
        await message.answer("Введите число:")
        return
    
    await state.update_data(weight=weight)
    
    await message.answer("Введите Ваш рост (в см):")
    await state.set_state(ProfileForm.height)

@dp.message(ProfileForm.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text)
        if height <= 0 or height > 250:
            await message.answer("Введите корректный рост (0-250 см):")
            return
    except ValueError:
        await message.answer("Введите число:")
        return
    
    await state.update_data(height=height)
    await message.answer("Введите Ваш возраст:")
    await state.set_state(ProfileForm.age)

@dp.message(ProfileForm.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0 or age > 120:
            await message.answer("Введите корректный возраст (1-120):")
            return
    except ValueError:
        await message.answer("Введите целое число:")
        return
    
    await state.update_data(age=age)
    await message.answer("Введите Ваш пол:")
    await state.set_state(ProfileForm.sex)

@dp.message(ProfileForm.sex)
async def process_sex(message: Message, state: FSMContext):
    sex = message.text.lower()
    if sex not in ["man", "female", "m", "f" "мужчина", "женщина", "мужской", "женский", "м", "ж", "муж", "жен"]:
        await message.answer("Введите корректный ответ (мужчина/женщина):")
        return
    elif sex in ["man", "мужчина", "мужской", "м", "муж"]:
        sex = "man"
    else:
        sex = "female"
    
    await state.update_data(sex=sex)
    await message.answer("Введите Ваш уровень активности (минуты физической активности в день):")
    await state.set_state(ProfileForm.activity)

@dp.message(ProfileForm.activity)
async def process_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        if activity < 0:
            await message.answer("Введите положительное число:")
            return
    except ValueError:
        await message.answer("Введите число минут:")
        return
    
    await state.update_data(activity=activity)
    await message.answer("Введите Ваш город:")
    await state.set_state(ProfileForm.city)

@dp.message(ProfileForm.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if not city:
        await message.answer("Введите название города:")
        return
    
    await state.update_data(city=city)
    await message.answer("Цель калорий (если нет — напиши 'пропустить'):")
    await state.set_state(ProfileForm.calories)

@dp.message(ProfileForm.calories)
async def process_calories(message: Message, state: FSMContext):
    calories = message.text.strip()
    data = await state.get_data()
    norm_calorie = count_calorie(data.get("sex"),
                                 data.get("weight"),
                                 data.get("height"),
                                 data.get("age"),
                                 data.get("activity"))
    
    if calories.lower() != "пропустить":
        try:
            calories_value = int(calories)
            persent_diff = 1 - min(norm_calorie, calories_value) / max(norm_calorie, calories_value)

            if calories_value <= 0:
                await message.answer("Введите положительное число или 'пропустить':")
                return
            elif persent_diff > 0.3:
                await message.answer(f"Указанное Вами число калорий отличается от нормы для Ваших параметров более, чем на 30%. Ваша норма: {round(norm_calorie)}. Измените Вашу цель")
                return
            await state.update_data(calories=calories_value)
        except ValueError:
            await message.answer("Введите число или 'пропустить':")
            return
    else:
        await state.update_data(calories=norm_calorie)
    
    data = await state.get_data()
    users_data[message.from_user.id] = data
    await state.clear()

    goal_water = count_water(data.get("weight"), 
                             data.get("activity"), 
                             data.get("city"))
    user_id = message.from_user.id
    if user_id not in water_data:
        water_data[user_id] = {
            "today": 0,
            "history": [],
            "goal": goal_water,
            "date": get_today_date()
        }
    else:
        water_data[user_id]["goal"] = goal_water

# === WATER
@dp.message(Command("log_water"))
async def start_log_water(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id
    
    if not command.args:
        await message.answer("Используй команду так:\n/log_water 300")
        return

    try:
        amount = int(command.args)
    except ValueError:
        await message.answer("Количество воды должно быть числом (в мл)")
        return
    
    if user_id not in water_data:
        water_data[user_id] = {"today": amount,
                               "history": [{"amount": amount, "time": datetime.now().isoformat()}],
                               "goal": 2000,
                               "date": get_today_date()}
    else:
        if water_data[user_id].get("date") != get_today_date():
            water_data[user_id] = {"today": amount,
                                   "history": [{"amount": amount, "time": datetime.now().isoformat()}],
                                   "goal": water_data[user_id].get("goal", 2000),
                                   "date": get_today_date()}
        else:
            water_data[user_id]["today"] += amount
            water_data[user_id]["history"].append({"amount": amount, "time": datetime.now().isoformat()})
    
    water_today = water_data[user_id]["today"]
    water_goal = round(water_data[user_id]["goal"])
    water_percent = (water_today / water_goal * 100)
    
    await state.clear()
    
    if water_today >= water_goal:
        response = (f"Ты выпил уже {amount} мл воды\n"
                    f"Цель достигнута: {water_today}/{water_goal} мл!\n")
    else:
        response = (f"Добавлено {amount} мл воды\n\n"
                    f"Сегодня: {water_today}/{water_goal} мл\n"
                    f"Осталось: {100 - water_percent:.0f}% или {water_goal - water_today} мл")
    
    if len(water_data[user_id]['history']) >= 2:
        plt_path = plot_stat(user_id, 
                            [mass['amount'] for mass in water_data[user_id]['history']],
                            [mass['time'] for mass in water_data[user_id]['history']])

        await message.answer_photo(photo=FSInputFile(plt_path), caption=response)
        os.remove(plt_path)
    else:
        await message.answer(response)

# === TRAIN
@dp.message(Command("log_workout"))
async def start_log_train(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id

    if not command.args:
        await message.answer("Используй команду так:\n/log_workout бег 40")
        return
    
    name, dur = command.args.split()
    try: 
        dur = int(dur)
    except ValueError:
        await message.answer("Введите ответ в формате '<тренировка> <время>':")
        return
    
    if user_id not in train_data:
        train_data[user_id] = {"today": dur,
                               "history": [{"amount": {name: dur}, "time": datetime.now().isoformat()}],
                               "goal": 60,
                               "date": get_today_date()}
    else:
        if train_data[user_id].get("date") != get_today_date():
            train_data[user_id] = {"today": dur,
                                   "history": [{"amount": {name: dur}, "time": datetime.now().isoformat()}],
                                   "goal": train_data[user_id].get("goal", 60),
                                   "date": get_today_date()}
        else:
            train_data[user_id]["today"] += dur
            train_data[user_id]["history"].append({"amount": dur, "time": datetime.now().isoformat()})
    
    train_today = train_data[user_id]["today"]
    train_goal = train_data[user_id]["goal"]
    train_percent = (train_today / train_goal * 100)
    
    await state.clear()
    
    if train_today >= train_goal:
        response = (f"Ты активничал уже {dur} мин\n"
                    f"Цель достигнута: {train_today}/{train_goal} мин\n")
    else:
        response = (f"Добавлено {dur} мин тренировки\n\n"
                    f"Сегодня: {train_today}/{train_goal} мин активности\n"
                    f"Осталось: {100 - train_percent:.0f}% или {train_goal - train_today} мин"
                    f"Дополнительно: выпейте 200 мл воды")
    
    await message.answer(response)

# === CAL
@dp.message(Command("log_food"))
async def start_log_food(message: Message, command: CommandObject, state: FSMContext):
    user_id = message.from_user.id

    if not command.args:
        await message.answer("Используй команду так:\n/log_food банан")
        return

    food_query = command.args.lower()
    food_info = get_food_info(food_query)

    if not food_info:
        await message.answer("В нашей базе нет такого продукта")
        return

    name, cal = food_info.values()

    if user_id not in cal_data or cal_data[user_id]["date"] != get_today_date():
        goal = (users_data.get(user_id, {}).get("calories", 1400))
        cal_data[user_id] = {"today": 0,
                             "history": [],
                             "goal": goal,
                             "date": get_today_date()}

    await state.update_data(food_name=name, food_cal=cal)
    await message.answer(f"{name} — {cal} ккал на 100 г.\nСколько грамм ты съел?")

    await state.set_state(FoodForm.weight)

@dp.message(FoodForm.weight)
async def process_cal_record(message: Message, state: FSMContext):
    user_id = message.from_user.id
    weight = message.text
    try: 
        weight = int(weight)
    except ValueError:
        await message.answer("Введите числовой ответ в граммах")
        return

    cal = (await state.get_data()).get("food_cal")
    name = (await state.get_data()).get("food_name")

    if user_id not in cal_data:
        cal_data[user_id] = {"today": cal * weight / 100,
                             "history": [{"amount": {'name': name, 'cal': cal * weight / 100}, "time": datetime.now().isoformat()}],
                             "goal": 1400,
                             "date": get_today_date()}
    else:
        if cal_data[user_id].get("date") != get_today_date():
            cal_data[user_id] = {"today": cal * weight / 100,
                                 "history": [{"amount": {'name': name, 'cal': cal * weight / 100}, "time": datetime.now().isoformat()}],
                                 "goal": cal_data[user_id].get("goal", 1400),
                                 "date": get_today_date()}
        else:
            cal_data[user_id]["today"] += cal * weight / 100
            cal_data[user_id]["history"].append({"amount": {'name': name, 'cal': cal * weight / 100}, "time": datetime.now().isoformat()})
    
    cal_today = cal_data[user_id]["today"]
    cal_goal = cal_data[user_id]["goal"]
    cal_percent = cal_today / cal_goal * 100
    
    await state.clear()
    
    if cal_today >= cal_goal:
        response = (f"Ты потребил уже уже {cal_today} калорий\n"
                    f"Цель достигнута: {cal_today}/{cal_goal} калорий\n")
    else:
        response = (f"Записано {cal_today} калорий\n\n"
                    f"Сегодня потреблено: {cal_today}/{cal_goal} калорий\n"
                    f"Осталось: {100 - cal_percent:.0f}% или {cal_goal - cal_today} калорий")
    
    if len(cal_data[user_id]['history']) >= 2:
        plt_path = plot_stat(user_id, 
                            [mass['amount']['cal'] for mass in cal_data[user_id]['history']],
                            [mass['time'] for mass in cal_data[user_id]['history']])
        
        await message.answer_photo(photo=FSInputFile(plt_path), caption=response)
        os.remove(plt_path)
    else:
        await message.answer(response)

# === PROGRESS

@dp.message(Command("check_progress"))
async def show_profile(message: Message):
    user_id = message.from_user.id
    if user_id not in users_data:
        await message.answer("Данные не найдены. Используй /start")

    if user_id in water_data:
        water_today = water_data[user_id].get("today", 0)
        water_goal = water_data[user_id].get("goal", 2000)
        water_resid = round(water_goal - water_today) if water_today < water_goal else 0
    else:
        water_today = 0
        water_goal = 2000
        water_resid = 2000

    if user_id in train_data:
        train_today = train_data[user_id].get("today", 0)
    else: 
        train_today = 0

    if user_id in cal_data:
        cal_today = cal_data[user_id].get("today", 0)
        cal_goal = cal_data[user_id].get("goal", 1800)
        cal_balance = round(cal_today - train_today)
    else:
        cal_today = 0
        cal_goal = 1400
        cal_balance = round(cal_today - train_today)

    response = (f"📊 Прогресс:\n"
                f"Вода:\n"
                f"- Выпито: {water_today} мл из {water_goal} мл\n"
                f"- Осталось: {water_resid} мл\n\n"
                f"Калории:\n"
                f"- Потреблено: {cal_today} ккал из {cal_goal} ккал\n"
                f"- Сожжено: {train_today} ккал\n"
                f"- Баланс: {cal_balance} ккал")
    
    await message.answer(response)

@dp.message(Command("profile"))
async def show_profile(message: Message):
    data = users_data.get(message.from_user.id)

    if not data:
        await message.answer("Данные не найдены. Используй /set_profile")
        return

    text = (
        f"📊 Твой профиль:\n\n"
        f"Вес: {data['weight']} кг\n"
        f"Рост: {data['height']} см\n"
        f"Возраст: {data['age']}\n"
        f"Активность: {data['activity']} мин/день\n"
        f"Город: {data['city']}\n"
        f"Цель калорий: {data['calories'] or 'не указана'}"
    )

    await message.answer(text)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
