# RioShin.py - Full Telegram File Sequencing Bot with IMAGE start
import os
import sqlite3
from pathlib import Path
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types.message import ContentType
from aiogram.types import InputFile
from aiogram import F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext

# Load config
from config import BOT_TOKEN, DB_PATH

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Ensure DB exists
db_path = Path(DB_PATH)
if not db_path.exists():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            file_id TEXT,
            caption TEXT,
            file_name TEXT,
            order_num INTEGER
        )
    """)
    conn.commit()
    conn.close()

# ---------------- /start Handler ----------------
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    image_url = "https://i.postimg.cc/7ZkqjJf5/rio-start-banner.jpg"  # Change to your own banner
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="About", callback_data="about")],
        [InlineKeyboardButton(text="Developer", url="https://t.me/RioShin")],
        [InlineKeyboardButton(text="BotsKingdoms", url="https://t.me/botskingdoms")]
    ])
    
    await msg.answer_photo(
        photo=image_url,
        caption=(
            "✨ **RioShin Bot**\n"
            "Sequence your files perfectly — auto ordered, auto clean.\n\n"
            "🔹 Use /ssequence to start\n"
            "🔹 Send files\n"
            "🔹 Use /esequence to finish\n\n"
            "Powered by **BotsKingdoms**"
        ),
        reply_markup=kb
    )

# ---------------- About Callback ----------------
@dp.callback_query(lambda c: c.data == "about")
async def about_cb(call: types.CallbackQuery):
    await call.message.answer(
        "📄 **About RioShin Bot**\n\n"
        "This bot helps you sequence files in order and manage them easily.\n"
        "Send multiple files, start sequencing with /ssequence, "
        "then finish with /esequence to get everything neatly ordered."
    )
    await call.answer()

# ---------------- Start Sequence ----------------
@dp.message(Command("ssequence"))
async def start_sequence(msg: types.Message):
    await msg.answer("🟢 Sequence started! Now send your files one by one. They will be saved in order.")

# ---------------- End Sequence ----------------
@dp.message(Command("esequence"))
async def end_sequence(msg: types.Message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT file_id, caption, file_name FROM files WHERE chat_id=? ORDER BY order_num ASC", (msg.chat.id,))
    files = c.fetchall()
    
    if not files:
        await msg.answer("❌ No files found to sequence. Use /ssequence and send files first.")
        conn.close()
        return
    
    # Send files in order
    for file_id, caption, file_name in files:
        await msg.answer_document(document=file_id, caption=caption or file_name)
    
    # Clean up
    c.execute("DELETE FROM files WHERE chat_id=?", (msg.chat.id,))
    conn.commit()
    conn.close()
    await msg.answer("✅ Sequence finished! All files sent in order.")

# ---------------- Save Files ----------------
@dp.message(F.content_type.in_([ContentType.DOCUMENT, ContentType.PHOTO]))
async def save_file(msg: types.Message):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Determine file type
    if msg.document:
        file_id = msg.document.file_id
        file_name = msg.document.file_name
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_name = "Photo"
    else:
        return
    
    # Get last order number
    c.execute("SELECT MAX(order_num) FROM files WHERE chat_id=?", (msg.chat.id,))
    last_order = c.fetchone()[0] or 0
    order_num = last_order + 1
    
    # Insert file
    c.execute(
        "INSERT INTO files (chat_id, file_id, caption, file_name, order_num) VALUES (?, ?, ?, ?, ?)",
        (msg.chat.id, file_id, msg.caption, file_name, order_num)
    )
    conn.commit()
    conn.close()
    
    await msg.answer(f"✅ File saved! Position in sequence: {order_num}")

# ---------------- Run Bot ----------------
if __name__ == "__main__":
    import asyncio
    from aiogram import exceptions
    
    async def main():
        try:
            print("🚀 Bot started...")
            await dp.start_polling(bot)
        except exceptions.TelegramAPIError as e:
            print("Telegram API Error:", e)
    
    asyncio.run(main())
