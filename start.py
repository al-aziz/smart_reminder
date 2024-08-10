import asyncio
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class ReminderStates(StatesGroup):
    waiting_for_task = State()
    waiting_for_time = State()


tasks = {}


@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Handles the /start command.
    Initiates the conversation by asking the user to input a task.
    Sets the bot's state to waiting for a task.
    """
    await message.answer(
        "Привет! Я бот-напоминалка. Напиши задачу, о которой нужно напомнить."
    )
    await state.set_state(ReminderStates.waiting_for_task)


@dp.message(ReminderStates.waiting_for_task)
async def process_task(message: types.Message, state: FSMContext):
    """
    Handles the user's task input.
    Stores the task in the bot's state and asks for the reminder time.
    Sets the bot's state to waiting for time input.
    """
    await state.update_data(task=message.text)
    await message.answer(
        "Отлично! Когда вам напомнить? Укажите время в формате ЧЧ:ММ (например, 14:30 или 14 30 с "
        "пробелом)."
    )
    await state.set_state(ReminderStates.waiting_for_time)


@dp.message(ReminderStates.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    """
    Handles the user's time input.
    Parses the time and schedules the reminder if the format is correct.
    If the time is in the past, it schedules the reminder for the next day.
    Clears the bot's state after scheduling the reminder.
    """
    time_str = message.text
    try:
        alarm_time = time_str.replace(" ", ":")
        print(time_str)
        reminder_time = datetime.strptime(alarm_time, "%H:%M").time()
        now = datetime.now()
        reminder_datetime = datetime.combine(now.date(), reminder_time)
        if reminder_datetime < now:
            reminder_datetime += timedelta(days=1)

        data = await state.get_data()
        task = data["task"]
        tasks[message.chat.id] = (task, reminder_datetime)
        await message.answer(
            f'Отлично! Напомню вам о задаче "{task}" в {reminder_datetime.strftime("%H:%M")}.'
        )

        delta = (reminder_datetime - now).total_seconds()
        # noinspection PyAsyncCall
        asyncio.create_task(send_reminder(message.chat.id, task, delta))

        await state.clear()
    except ValueError:
        await message.answer(
            "Время указано в неверном формате. Пожалуйста, используйте формат ЧЧ:ММ."
        )


async def send_reminder(chat_id: int, task: str, delay: float):
    """
    Sends a reminder message after a specified delay.
    Sleeps for the delay duration and then sends the reminder message to the user.
    """
    await asyncio.sleep(delay)
    await bot.send_message(chat_id, f"Напоминание: {task}", parse_mode=ParseMode.HTML)


@dp.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    """
    Handles the /cancel command.
    Clears the bot's state and cancels the current operation.
    """
    await state.clear()
    await message.answer("Операция отменена.")


@dp.message(Command("show_tasks"))
async def show_tasks(message: types.Message):
    if tasks:
        # task_list = []
        for chat_id, (task, reminder_time) in tasks.items():
            msg = (
                f"Chat ID: {chat_id} Time: {reminder_time.strftime('%H:%M')}\n"
                f"Task: `{task}`"
            )
            await bot.send_message(chat_id=message.chat.id, text=msg)
    else:
        await message.answer("No tasks found.")


async def main():
    """
    The main entry point of the bot.
    Registers the bot with the dispatcher and starts polling for updates.
    """
    while True:
        try:
            await dp.start_polling(bot, skip_updates=True)
        except TelegramNetworkError as e:
            print(f"Network error occurred: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break


if __name__ == "__main__":
    asyncio.run(main())
