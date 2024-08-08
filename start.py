import asyncio
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
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
        "Привет! Я бот-напоминалка. Напишите задачу, о которой нужно напомнить."
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
        "Отлично! Когда вам напомнить? Укажите время в формате ЧЧ:ММ (например, 14:30)."
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
        reminder_time = datetime.strptime(time_str, "%H:%M").time()
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
        asyncio.create_task(
            send_reminder(message.chat.id, task, delta)
        )  # noinspection PyAsyncCall

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


async def main():
    """
    The main entry point of the bot.
    Registers the bot with the dispatcher and starts polling for updates.
    """
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
