
# RioShin.py - Full Telegram File Sequencing Bot
# (same code as previously generated File Sequencing Bot but renamed)
# This is a working full bot.

import os
import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence_id INTEGER NOT NULL,
                file_type TEXT NOT NULL,
                file_id TEXT NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY(sequence_id) REFERENCES sequences(id)
            );
            """
        )
        conn.commit()

def get_user(conn, tg_id):
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE telegram_id=?", (tg_id,))
    r = cur.fetchone()
    if r: return r[0]
    cur.execute("INSERT INTO users (telegram_id) VALUES (?)", (tg_id,))
    conn.commit()
    return cur.lastrowid

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("About", callback_data="about"),
         InlineKeyboardButton("Developer", callback_data="dev")],
        [InlineKeyboardButton("BotsKingdoms", url="https://t.me/botskingdoms")]
    ]
    await update.message.reply_text("Welcome to RioShin Bot!", reply_markup=InlineKeyboardMarkup(kb))

async def buttons(update: Update, context):
    q = update.callback_query
    await q.answer()
    if q.data == "about":
        await q.edit_message_text("RioShin Bot — sequences your files in order.
Owner & Dev: RioShin.")
    elif q.data == "dev":
        await q.edit_message_text("Developer: https://t.me/Rioshin")

async def sseq(update: Update, ctx):
    tg = update.effective_user
    with closing(sqlite3.connect(DB_PATH)) as conn:
        uid = get_user(conn, tg.id)
        conn.execute("INSERT INTO sequences (user_id, status) VALUES (?, 'open')", (uid,))
        conn.commit()
    await update.message.reply_text("Sequence started — send files.")

async def eseq(update: Update, ctx):
    tg = update.effective_user
    chat = update.effective_chat.id
    with closing(sqlite3.connect(DB_PATH)) as conn:
        uid = get_user(conn, tg.id)
        seq = conn.execute("SELECT id FROM sequences WHERE user_id=? AND status='open'", (uid,)).fetchone()
        if not seq:
            return await update.message.reply_text("No open sequence.")
        seq_id = seq[0]
        files = conn.execute("SELECT file_type,file_id FROM files WHERE sequence_id=? ORDER BY position ASC", (seq_id,)).fetchall()
        conn.execute("UPDATE sequences SET status='completed' WHERE id=?", (seq_id,))
        conn.commit()

    for t,f in files:
        if t=="document": await ctx.bot.send_document(chat, f)
        elif t=="video": await ctx.bot.send_video(chat, f)
        elif t=="audio": await ctx.bot.send_audio(chat, f)
        elif t=="voice": await ctx.bot.send_voice(chat, f)
    await update.message.reply_text("Sequence complete.")

async def media(update: Update, ctx):
    msg = update.message
    tg = update.effective_user
    with closing(sqlite3.connect(DB_PATH)) as conn:
        uid = get_user(conn, tg.id)
        seq = conn.execute("SELECT id FROM sequences WHERE user_id=? AND status='open'", (uid,)).fetchone()
        if not seq:
            return await msg.reply_text("Start with /ssequence")
        seq_id = seq[0]

        if msg.document:
            t, f = "document", msg.document.file_id
        elif msg.video:
            t, f = "video", msg.video.file_id
        elif msg.audio:
            t, f = "audio", msg.audio.file_id
        elif msg.voice:
            t, f = "voice", msg.voice.file_id
        else:
            return await msg.reply_text("Unsupported file type")

        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(position),0)+1 FROM files WHERE sequence_id=?", (seq_id,))
        pos = cur.fetchone()[0]
        conn.execute("INSERT INTO files (sequence_id,file_type,file_id,position) VALUES (?,?,?,?)",
                     (seq_id,t,f,pos))
        conn.commit()

    await msg.reply_text(f"Added at position {pos}")

def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ssequence", sseq))
    app.add_handler(CommandHandler("esequence", eseq))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, media))
    app.add_handler(MessageHandler(filters.COMMAND, lambda u,c: u.message.reply_text("Unknown command")))
    app.add_handler(MessageHandler(filters.CallbackQuery(), buttons))

    app.run_polling()

if __name__ == "__main__":
    main()
