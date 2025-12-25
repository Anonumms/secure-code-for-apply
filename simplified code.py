from aiogram import Bot, Dispatcher, executor, types
import openai
import random
import asyncio
import functools
import concurrent.futures
import os
import time

# cfg
openai.api_key = "REMOVED_FOR_SECURITY"
bot = Bot(token="REMOVED_FOR_SECURITY")
dp = Dispatcher(bot)

# ThreadPool for blocking OpenAI calls
executor_pool = concurrent.futures.ThreadPoolExecutor()

# user memory
user_data = {}

# Prompts for different modes
PROMPTS = {
    "study": "REMOVED",
    "chat": "REMOVED",
    "health": "REMOVED",
    "help": "REMOVED"
}

# simplified vers
def humanize_text(text):
    interjections = ["well", "so", "hey", "hmm", "like", "you know", "lol", "haha"]
    emojis = ["🔥", "😅", "🤔", "👌", "😂"]
    if len(text.split()) < 10 and random.random() < 0.45:
        text = random.choice(interjections) + ", " + text
    if len(text.split()) >= 10 and random.random() < 0.2:
        text += " " + random.choice(emojis)
    if len(text.split()) < 10 and random.random() < 0.25:
        text += " " + random.choice(emojis)
    return text

# Ensure user exists
def ensure_user(user_id, first_name=None):
    if user_id not in user_data:
        user_data[user_id] = {
            "name": first_name or "friend",
            "mode": "chat",
            "history": [],
            "preferences": {"short_responses": False, "love_memes": True}
        }
    return user_data[user_id]

# Run OpenAI ChatCompletion in executor
async def call_chat_completion(messages):
    loop = asyncio.get_event_loop()
    func = functools.partial(openai.ChatCompletion.create, model="gpt-4o-mini", messages=messages)
    return await loop.run_in_executor(executor_pool, func)

# Generate reply
async def chatgpt_answer(user_id, message_text):
    user = ensure_user(user_id)
    mode = user["mode"]
    history = user["history"]

    history.append({"role": "user", "content": message_text})
    if len(history) > 15:
        history = history[-10:]

    system_prompt = PROMPTS.get(mode, PROMPTS["chat"]) + f" Address the user by their name: {user['name']}. Adjust style according to their preferences: {user['preferences']}"
    messages = [{"role": "system", "content": system_prompt}] + history

    try:
        response = await call_chat_completion(messages)
        reply = response.choices[0].message["content"]
    except Exception as e:
        reply = f"Error occurred: {e}"

    if user["preferences"].get("short_responses", False):
        reply = (reply.split(".")[0] + ".") if "." in reply else reply

    reply = humanize_text(reply)
    history.append({"role": "assistant", "content": reply})
    user["history"] = history
    return reply

# Command handler
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    ensure_user(user_id, message.from_user.first_name)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("📚 Study", callback_data="study"),
        types.InlineKeyboardButton("😎 Chat", callback_data="chat"),
        types.InlineKeyboardButton("🏥 Health", callback_data="health"),
        types.InlineKeyboardButton("🛠 Help", callback_data="help")
    )
    await message.answer(f"Hey {user_data[user_id]['name']}! Choose a mode 👇", reply_markup=keyboard)

# Mode switch handler
@dp.callback_query_handler(lambda c: c.data in PROMPTS)
async def process_mode(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    ensure_user(user_id, callback_query.from_user.first_name)
    user_data[user_id]["mode"] = callback_query.data
    user_data[user_id]["history"] = []  # reset history
    await callback_query.answer(f"Mode switched to {callback_query.data}")
    await callback_query.message.answer(f"✅ Switched to {callback_query.data} mode!")

# Run bot
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
