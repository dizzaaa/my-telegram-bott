import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- GANTI BAGIAN INI ---
TOKEN = '8389389993:AAHM1L3QAY-TeN8B10UpEU5ptGlEZRiF82M'
CHANNEL_TARGET = '@RekberEloise' 
MIN_SUBS = 25

def init_db():
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS logs (user_id INTEGER, username TEXT, tgl TEXT)')
    conn.commit()
    conn.close()

async def start_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kbd = [[InlineKeyboardButton("Konfirmasi 25 Subs", callback_data='cek')]]
    await update.message.reply_text("Klik tombol untuk absen:", reply_markup=InlineKeyboardMarkup(kbd))

async def handle_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        count = await context.bot.get_chat_member_count(CHANNEL_TARGET)
        if count >= MIN_SUBS:
            await query.edit_message_text(f"✅ Diterima! Subs: {count}")
        else:
            await query.edit_message_text(f"❌ Kurang! Baru {count} subs.")
    except:
        await query.edit_message_text("❌ Bot belum jadi admin di channel!")

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and not update.message.text.startswith('/'):
        conn = sqlite3.connect('bot.db')
        c = conn.cursor()
        c.execute("INSERT INTO logs VALUES (?, ?, ?)", 
                  (update.effective_user.id, update.effective_user.username, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        conn.close()

async def cek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('bot.db')
    c = conn.cursor()
    tgl = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT COUNT(*) FROM logs WHERE user_id=? AND tgl=?", (update.effective_user.id, tgl))
    hasil = c.fetchone()[0]
    await update.message.reply_text(f"📊 Broadcast hari ini: {hasil}")
    conn.close()

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("absen", start_absen))
    app.add_handler(CommandHandler("cek", cek))
    app.add_handler(CallbackQueryHandler(handle_btn))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), track))
    app.run_polling()
