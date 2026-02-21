import sqlite3
import re
import pytz
import pytesseract
import random
from PIL import Image
from io import BytesIO
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS absen_status 
                 (user_id INTEGER PRIMARY KEY, username TEXT, senin INTEGER DEFAULT 0, jumat INTEGER DEFAULT 0, minggu INTEGER DEFAULT 0, status_izin TEXT DEFAULT 'aktif')''')
    c.execute("INSERT OR IGNORE INTO settings VALUES ('konsekuensi', 'Belum ada hukuman dari Master U-U')")
    conn.commit()
    conn.close()

# --- HELPERS ---
def get_panggilan(user):
    return f"@{user.username}" if user.username else user.first_name

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private': return True
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in ['creator', 'administrator']

# --- AUTOMATION: RESET SENIN 00:00 ---
async def reset_mingguan(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    c.execute("UPDATE absen_status SET senin=0, jumat=0, minggu=0, status_izin='aktif'")
    c.execute("DELETE FROM used_data")
    conn.commit()
    conn.close()
    await context.bot.send_message(chat_id=GROUP_LOG_ID, text="☁️ **Sistem Reset Berhasil!**\nSemua status absen kembali ke ⛔️. Ayo kerja lagi Master! 🩵")

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    panggilan = get_panggilan(update.effective_user)
    await update.message.reply_text(f"☁️ Bot by {OWNER_USERNAME} ☁️")
    await update.message.reply_text(f"Hellow bellow {panggilan}! 🐾✨\nKenalin, aku asisten centilmu yang paling biru! Mau lapor apa hari ini?")

async def menu_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kbd = [
        [InlineKeyboardButton("☁️ Senin: Upsubs 25s", callback_data='mode_senin')],
        [InlineKeyboardButton("☁️ Jumat: Jaseb 50 LPM", callback_data='mode_jumat')],
        [InlineKeyboardButton("☁️ Minggu: Send MF 20x", callback_data='mode_minggu')]
    ]
    await update.message.reply_text("✨ **Silahkan Pilih Absen Untuk Reminder** ✨\nJangan bolos ya, nanti Cinnamoroll sedih...😿", 
                                   reply_markup=InlineKeyboardMarkup(kbd), parse_mode='Markdown')

async def admin_absensi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    if not update.message.reply_to_message:
        return await update.message.reply_text("🐾 Master, reply salah satu user dulu buat cek status absennya! 🩵")
    
    target = update.message.reply_to_message.from_user
    conn = sqlite3.connect('cinnabot_pro.db')
    res = conn.execute("SELECT senin, jumat, minggu, status_izin FROM absen_status WHERE user_id=?", (target.id,)).fetchone()
    conn.close()
    
    s = "✅" if res and res[0] else "⛔️"
    j = "✅" if res and res[1] else "⛔️"
    m = "✅" if res and res[2] else "⛔️"
    iz = f"\n🐾 Status: {res[3]}" if res else ""
    
    await update.message.reply_text(f"🐾 **LAPORAN @{target.username}**\n\nSenin: {s}\nJumat: {j}\nMinggu: {m}{iz}", parse_mode='Markdown')

async def izin_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    alasan = " ".join(context.args)
    if not alasan: return await update.message.reply_text(f"🐾 {get_panggilan(user)}, tulis alasannya ya! Contoh: `/izin Sakit`")
    
    conn = sqlite3.connect('cinnabot_pro.db')
    conn.execute("INSERT OR IGNORE INTO absen_status (user_id, username) VALUES (?, ?)", (user.id, user.username))
    conn.execute("UPDATE absen_status SET status_izin='izin' WHERE user_id=?", (user.id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Oke {get_panggilan(user)}, Cinnamoroll catat kamu izin ya. Cepat sembuh/selesai urusannya! 🥺🩵")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('cinnabot_pro.db')
    rows = conn.execute("SELECT username, COUNT(*) as jml FROM bc_logs GROUP BY user_id ORDER BY jml DESC LIMIT 5").fetchall()
    conn.close()
    teks = "🏆 **Bintang Broadcast Pekan Ini** 🏆\n\n"
    for i, r in enumerate(rows, 1): teks += f"{i}. @{r[0]} — {r[1]} BC 🐾\n"
    await update.message.reply_text(teks, parse_mode='Markdown')

# --- CALLBACK HANDLER ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    back = [[InlineKeyboardButton("🔙 Kembali", callback_data='back_to_menu')]]
    
    if query.data == 'mode_senin':
        context.user_data['absen_type'] = 'senin'
        await query.edit_message_text("🐾 *Cinnamoroll mode on!* Silahkan kirim list 25 username @username ya, manis! 🩵", reply_markup=InlineKeyboardMarkup(back))
    elif query.data == 'mode_jumat':
        context.user_data['absen_type'] = 'jumat'
        await query.edit_message_text("📸 Kirim screenshot grid-mu! Harus ada tanggal (DD/MM/YY) ya.", reply_markup=InlineKeyboardMarkup(back))
    elif query.data == 'mode_minggu':
        context.user_data['absen_type'] = 'minggu'
        await query.edit_message_text("🔗 Kirim 20 link menfess kamu! Aku hitungin satu-satu ya...", reply_markup=InlineKeyboardMarkup(back))
    elif query.data == 'back_to_menu':
        context.user_data['absen_type'] = None
        kbd = [[InlineKeyboardButton("☁️ Senin: Upsubs 25s", callback_data='mode_senin')], [InlineKeyboardButton("☁️ Jumat: Jaseb 50 LPM", callback_data='mode_jumat')], [InlineKeyboardButton("☁️ Minggu: Send MF 20x", callback_data='mode_minggu')]]
        await query.edit_message_text("✨ **Silahkan Pilih Absen Untuk Reminder** ✨", reply_markup=InlineKeyboardMarkup(kbd))

# --- MESSAGE PROCESSOR ---
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    mode = context.user_data.get('absen_type')
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    hukuman_kbd = [[InlineKeyboardButton("💢 Klik Konsekuensi", callback_data='cek_hukuman')]]

    if mode == 'senin' and update.message.text and update.message.text.startswith('@'):
        usernames = re.findall(r'@\w+', update.message.text)
        if len(usernames) < 25: return await update.message.reply_text(f"❌ Kurang sayang! Baru {len(usernames)} username.")
        
        for u in usernames:
            if c.execute("SELECT content FROM used_data WHERE content=?", (u,)).fetchone():
                return await update.message.reply_text(f"Ih! @{user.username} curang! Username {u} udah pernah dipake! Gagal deh‼️😾")
        
        for u in usernames: c.execute("INSERT INTO used_data VALUES (?, ?)", (u, str(random.getrandbits(16))))
        c.execute("INSERT OR IGNORE INTO absen_status (user_id, username) VALUES (?, ?)", (user.id, user.username))
        c.execute("UPDATE absen_status SET senin=1 WHERE user_id=?", (user.id,))
        conn.commit()
        await update.message.reply_text(f"Absensi Berhasil, {get_panggilan(user)}! ✅🩵")

    elif update.message.text and not update.message.text.startswith('/'):
        c.execute("INSERT INTO bc_logs VALUES (?, ?, ?)", (user.id, user.username, datetime.now(TIME_ZONE).strftime('%Y-%m-%d')))
        conn.commit()
    conn.close()

# --- MAIN RUNNER ---
if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    if app.job_queue:
        app.job_queue.run_daily(reset_mingguan, time=time(0, 0), days=(0,))
        print("✅ Scheduler Aktif")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("absen", menu_absen))
    app.add_handler(CommandHandler("absensi", admin_absensi))
    app.add_handler(CommandHandler("top", leaderboard))
    app.add_handler(CommandHandler("izin", izin_absen))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, process_message))
    
    print("☁️ Cinnabot Terbang!")
    app.run_polling()
