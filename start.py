import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from datetime import datetime, timedelta

API_TOKEN = ''

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


class ReminderStates(StatesGroup):
    waiting_for_task = State()
    waiting_for_time = State()


tasks = {}


@dp.message_handler(commands='start', state='*')
async def cmd_start(message: types.Message):
    await message.answer("Привет! Я бот-напоминалка. Напишите задачу, о которой нужно напомнить.")
    await ReminderStates.waiting_for_task.set()


@dp.message_handler(state=ReminderStates.waiting_for_task)
async def process_task(message: types.Message, state: FSMContext):
    await state.update_data(task=message.text)
    await message.answer(
        "Отлично! Когда вам напомнить? Укажите время в формате ЧЧ:ММ (например, 14:30).")
    await ReminderStates.waiting_for_time.set()


@dp.message_handler(state=ReminderStates.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    time_str = message.text
    try:
        reminder_time = datetime.strptime(time_str, '%H:%M').time()
        now = datetime.now()
        reminder_datetime = datetime.combine(now.date(), reminder_time)
        if reminder_datetime < now:
            reminder_datetime += timedelta(days=1)

        data = await state.get_data()
        task = data['task']
        tasks[message.chat.id] = (task, reminder_datetime)
        await message.answer(
            f'Отлично! Напомню вам о задаче "{task}" в {reminder_datetime.strftime("%H:%M")}.')

        # Schedule the reminder
        delta = (reminder_datetime - now).total_seconds()
        asyncio.create_task(send_reminder(message.chat.id, task, delta))

        await state.finish()
    except ValueError:
        await message.answer(
            "Время указано в неверном формате. Пожалуйста, используйте формат ЧЧ:ММ.")


async def send_reminder(chat_id: int, task: str, delay: float):
    await asyncio.sleep(delay)
    await bot.send_message(chat_id, f'Напоминание: {task}')


@dp.message_handler(commands='cancel', state='*')
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer('Операция отменена.')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
