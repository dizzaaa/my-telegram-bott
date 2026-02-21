import sqlite3
import re
import pytz
import pytesseract
import random
from PIL import Image
from io import BytesIO
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- CONFIG ---
TOKEN = '8389389993:AAFBzImBYwxlo1uaCFnFG3RzMJ7gf8pUwwo'
OWNER_USERNAME = '@cinnamoroiLi'
GROUP_LOG_ID = -5151128223  
TIME_ZONE = pytz.timezone('Asia/Jakarta')

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bc_logs (user_id INTEGER, username TEXT, tgl TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS used_data (content TEXT PRIMARY KEY, serial TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS absen_status 
                 (user_id INTEGER PRIMARY KEY, username TEXT, senin INTEGER DEFAULT 0, jumat INTEGER DEFAULT 0, minggu INTEGER DEFAULT 0, 
                  status_izin TEXT DEFAULT 'aktif', points INTEGER DEFAULT 0, warning INTEGER DEFAULT 0)''')
    c.execute('CREATE TABLE IF NOT EXISTS brain (keyword TEXT PRIMARY KEY, response TEXT)')
    conn.commit()
    conn.close()

# --- HELPERS ---
def get_panggilan(user):
    return f"@{user.username}" if user.username else user.first_name

# --- TOMBOL MENU UTAMA ---
def main_menu_buttons():
    keyboard = [
        [KeyboardButton("☁️ Menu Absen"), KeyboardButton("💰 Cek Poin")],
        [KeyboardButton("🟡 Izin Absen"), KeyboardButton("🏆 Leaderboard")],
        [KeyboardButton("💬 Tanya Cinnabot")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, placeholder="Pilih menu Cinnabot...")

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    panggilan = get_panggilan(update.effective_user)
    await update.message.reply_text(
        f"Hellow bellow {panggilan}! 🐾✨\nCinnabot siap melayani Master! Klik tombol di bawah buat mulai ya!",
        reply_markup=main_menu_buttons()
    )

async def menu_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kbd = [[InlineKeyboardButton("☁️ Senin: Upsubs", callback_data='m_senin')],
           [InlineKeyboardButton("☁️ Jumat: Jaseb (OCR)", callback_data='m_jumat')],
           [InlineKeyboardButton("☁️ Minggu: Send MF", callback_data='m_minggu')]]
    await update.message.reply_text("✨ **PILIH HARI ABSENMU** ✨", reply_markup=InlineKeyboardMarkup(kbd))

# --- MESSAGE PROCESSOR (LOGIKA TOMBOL & CHAT) ---
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    mode = context.user_data.get('absen_type')
    panggilan = get_panggilan(user)

    # A. LOGIKA TOMBOL REPLIES
    if text == "☁️ Menu Absen":
        await menu_absen(update, context)
        return
    elif text == "💰 Cek Poin":
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("SELECT points, warning FROM absen_status WHERE user_id=?", (user.id,)).fetchone()
        conn.close()
        p = res[0] if res else 0
        w = "🟡" * res[1] if res and res[1] > 0 else "🟢"
        await update.message.reply_text(f"💰 Poin {panggilan}: **{p}**\n⚠️ Status Warning: {w}")
        return
    elif text == "🟡 Izin Absen":
        await update.message.reply_text(f"🐾 {panggilan}, ketik `/izin [alasan]` ya!")
        return

    # B. BRAIN LEARNING DARI MASTER (LOG)
    if update.effective_chat.id == GROUP_LOG_ID and update.message.reply_to_message:
        orig = update.message.reply_to_message.text
        if "Tanya Jawab" in orig:
            q_match = re.search(r'`(.*?)`', orig)
            if q_match:
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("INSERT OR REPLACE INTO brain VALUES (?, ?)", (q_match.group(1).lower(), text))
                conn.commit()
                conn.close()
                return await update.message.reply_text("✅ Sudah Cinnamoroll hafal! 🐾")

    # C. MIRRORING & AI RESPOND (OTAK BOT)
    if text and not text.startswith('/') and update.effective_chat.id != GROUP_LOG_ID:
        # Mirror ke log master
        await context.bot.send_message(chat_id=GROUP_LOG_ID, text=f"☁️ **Tanya Jawab {panggilan}**:\n`{text}`", parse_mode='Markdown')
        
        conn = sqlite3.connect('cinnabot_pro.db')
        brain = conn.execute("SELECT keyword, response FROM brain").fetchall()
        conn.close()
        for k, r in brain:
            if k in text.lower():
                return await update.message.reply_text(r.format(user=panggilan))

    # D. LOGIKA ABSEN (Sama seperti sebelumnya)
    if mode == 'senin' and text and text.startswith('@'):
        unames = re.findall(r'@\w+', text)
        if len(unames) >= 25:
            # (Logika simpan database Senin Master di sini...)
            await update.message.reply_text(f"Absen Senin Berhasil, {panggilan}! ✅")
            context.user_data['absen_type'] = None
            return

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("absen", menu_absen))
    app.add_handler(CallbackQueryHandler(handle_callback)) # Pastikan handle_callback Master ada
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))
    
    print("☁️ Cinnabot dengan Tombol Menu siap!")
    app.run_polling()
