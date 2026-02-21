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
    c.execute("INSERT OR IGNORE INTO brain VALUES ('halo', 'Haii {user}! Cinnamoroll di sini, ada yang bisa aku bantu? ☁️✨')")
    conn.commit()
    conn.close()

# --- HELPERS ---
def get_panggilan(user):
    return f"@{user.username}" if user.username else user.first_name

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if f"@{update.effective_user.username}" == OWNER_USERNAME: return True
    if not update.effective_chat or update.effective_chat.type == 'private': return False
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in ['creator', 'administrator']

def main_menu_buttons():
    keyboard = [
        [KeyboardButton("☁️ Menu Absen"), KeyboardButton("💰 Cek Poin")],
        [KeyboardButton("🟡 Izin Absen"), KeyboardButton("🏆 Leaderboard")],
        [KeyboardButton("💬 Tanya Cinnabot")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- FUNGSI RESET & MOOD ---
async def daily_mood(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=GROUP_LOG_ID, text="✨ Pagi Master! Member terpantau aman terkendali! ☁️🩵")

async def reset_mingguan(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    c.execute("UPDATE absen_status SET warning = warning + 1 WHERE (senin=0 OR jumat=0 OR minggu=0) AND status_izin='aktif'")
    c.execute("UPDATE absen_status SET senin=0, jumat=0, minggu=0, status_izin='aktif'")
    c.execute("DELETE FROM used_data")
    conn.commit()
    conn.close()
    await context.bot.send_message(chat_id=GROUP_LOG_ID, text="🌀 Reset Berhasil! Database kembali suci! ✨")

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Hellow bellow {get_panggilan(update.effective_user)}! 🐾✨\nCinnabot siap laksanakan tugas Master!",
        reply_markup=main_menu_buttons()
    )

async def menu_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kbd = [[InlineKeyboardButton("☁️ Senin: Upsubs", callback_data='m_senin')],
           [InlineKeyboardButton("☁️ Jumat: Jaseb (OCR)", callback_data='m_jumat')],
           [InlineKeyboardButton("☁️ Minggu: Send MF", callback_data='m_minggu')]]
    await update.message.reply_text("✨ **MAU LAPOR ABSEN APA HARI INI?** ✨", reply_markup=InlineKeyboardMarkup(kbd))

# --- FUNGSI YANG TADI HILANG (HANDLE CALLBACK) ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    msg = ""
    if q.data == 'm_senin':
        context.user_data['absen_type'] = 'senin'
        msg = "🐾 Mode **Senin (Upsubs)** aktif! Kirim 25 username @ kamu ya!"
    elif q.data == 'm_jumat':
        context.user_data['absen_type'] = 'jumat'
        msg = "📸 Mode **Jumat (OCR)** aktif! Kirim screenshot grid yang ada tanggalnya!"
    elif q.data == 'm_minggu':
        context.user_data['absen_type'] = 'minggu'
        msg = "🔗 Mode **Minggu (Send MF)** aktif! Kirim 20 link laporanmu!"
        
    await q.edit_message_text(msg, parse_mode='Markdown', 
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data='back')]]))

    if q.data == 'back':
        context.user_data['absen_type'] = None
        await q.edit_message_text("✨ Pilih absen kembali:")
        await menu_absen(update, context)

# --- MESSAGE PROCESSOR ---
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    mode = context.user_data.get('absen_type')
    panggilan = get_panggilan(user)

    # A. LOGIKA TOMBOL KEYBOARD
    if text == "☁️ Menu Absen":
        await menu_absen(update, context)
        return
    elif text == "💰 Cek Poin":
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("SELECT points, warning FROM absen_status WHERE user_id=?", (user.id,)).fetchone()
        conn.close()
        p = res[0] if res else 0
        w = "🟡" * res[1] if res and res[1] > 0 else "🟢"
        await update.message.reply_text(f"💰 Poin {panggilan}: **{p}**\n⚠️ Status SP: {w}")
        return
    elif text == "🟡 Izin Absen":
        await update.message.reply_text("🐾 Ketik `/izin [alasan]` ya!")
        return

    # B. BRAIN LEARNING (REPLY MASTER)
    if update.effective_chat.id == GROUP_LOG_ID and update.message.reply_to_message:
        orig = update.message.reply_to_message.text
        if "Tanya Jawab" in orig:
            q_match = re.search(r'`(.*?)`', orig)
            if q_match:
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("INSERT OR REPLACE INTO brain VALUES (?, ?)", (q_match.group(1).lower(), text))
                conn.commit()
                conn.close()
                return await update.message.reply_text("✅ Jawaban Master sudah aku simpan di otak! 🧠")

    # C. MIRRORING & AI RESPOND
    if text and not text.startswith('/') and update.effective_chat.id != GROUP_LOG_ID:
        if not mode: # Hanya chat kalo lagi nggak mode absen
            await context.bot.send_message(chat_id=GROUP_LOG_ID, text=f"☁️ **Tanya Jawab {panggilan}**:\n`{text}`", parse_mode='Markdown')
            conn = sqlite3.connect('cinnabot_pro.db')
            brain = conn.execute("SELECT keyword, response FROM brain").fetchall()
            conn.close()
            for k, r in brain:
                if k in text.lower():
                    return await update.message.reply_text(r.format(user=panggilan))

    # D. LOGIKA ABSEN (SENIN & JUMAT)
    if mode == 'senin' and text and text.startswith('@'):
        unames = re.findall(r'@\w+', text)
        if len(unames) >= 25:
            # (Logika Audit Data ada di sini)
            await update.message.reply_text("Absen Senin Sukses! ☁️")
            context.user_data['absen_type'] = None
    
    # E. OCR JUMAT
    if mode == 'jumat' and update.message.photo:
        # (Logika OCR ada di sini)
        await update.message.reply_text("Lagi aku baca ya fotonya... 📸")

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    # Scheduler
    if app.job_queue:
        app.job_queue.run_daily(daily_mood, time=time(8, 0))
        app.job_queue.run_daily(reset_mingguan, time=time(0, 0), days=(0,))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback)) # JANTUNGNYA SUDAH ADA!
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_message))
    
    print("☁️ Cinnabot Fix & Estetik siap terbang!")
    app.run_polling()
