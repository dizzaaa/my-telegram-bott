import sqlite3
import re
import pytz
import pytesseract
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest

# --- CONFIG ---
TOKEN = '8389389993:AAHM1L3QAY-TeN8B10UpEU5ptGlEZRiF82M'
CHANNEL_TARGET = '@RekberEloise'
OWNER_USERNAME = '@cinnamoroiLi'
TIME_ZONE = pytz.timezone('Asia/Jakarta')

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS bc_logs (user_id INTEGER, username TEXT, tgl TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS used_data (content TEXT PRIMARY KEY)')
    c.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
    c.execute("INSERT OR IGNORE INTO settings VALUES ('konsekuensi', 'Belum ada hukuman dari Master U-U')")
    conn.commit()
    conn.close()

def get_sapaan():
    jam = datetime.now(TIME_ZONE).hour
    if 4 <= jam < 11: return "Pagi ☀️"
    elif 11 <= jam < 15: return "Siang ☁️"
    elif 15 <= jam < 18: return "Sore 🌤️"
    else: return "Malam 🌙"

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"☁️ Bot by {OWNER_USERNAME} ☁️")
    await update.message.reply_text(f"Hellow bellow @{user.username}! 🐾✨\nKenalin, aku asisten centilmu yang paling biru! Mau lapor apa hari ini?")

async def menu_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kbd = [
        [InlineKeyboardButton("☁️ Senin: Upsubs 25s", callback_data='mode_senin')],
        [InlineKeyboardButton("☁️ Jumat: Jaseb 50 LPM", callback_data='mode_jumat')],
        [InlineKeyboardButton("☁️ Minggu: Send MF 20x", callback_data='mode_minggu')],
        [InlineKeyboardButton("🐾 Cek Konsekuensi", callback_data='cek_hukuman')]
    ]
    await update.message.reply_text(
        "✨ **Silahkan Pilih Absen Untuk Reminder** ✨\nJangan bolos ya, nanti Cinnamoroll sedih...😿",
        reply_markup=InlineKeyboardMarkup(kbd), parse_mode='Markdown'
    )

# --- CALLBACKS ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'mode_senin':
        context.user_data['absen_type'] = 'senin'
        await query.edit_message_text("🐾 *Cinnamoroll mode on!* Silahkan kirim list 25 username @username ya, manis! 🩵")
    elif query.data == 'mode_jumat':
        context.user_data['absen_type'] = 'jumat'
        await query.edit_message_text("📸 Kirim screenshot grid-mu! Harus ada tanggal (DD/MM/YY) ya. Kalau buram aku tutup mata nih! 🙈")
    elif query.data == 'mode_minggu':
        context.user_data['absen_type'] = 'minggu'
        await query.edit_message_text("🔗 Kirim 20 link menfess kamu! Aku hitungin satu-satu ya... 🍰")
    elif query.data == 'cek_hukuman':
        conn = sqlite3.connect('cinnabot_pro.db')
        hukuman = conn.execute("SELECT value FROM settings WHERE key='konsekuensi'").fetchone()[0]
        conn.close()
        await query.edit_message_text(f"🐾 **Hukuman dari Master {OWNER_USERNAME}** 🐾\n\n{hukuman}\n\n_Dikerjakan ya!_", parse_mode='Markdown')

# --- AUDIT LOGIC (ANTI-CURANG) ---
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    mode = context.user_data.get('absen_type')
    now = datetime.now(TIME_ZONE)
    tgl_full = now.strftime('%d/%m/%Y')
    jam_full = now.strftime('%H:%M')
    
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()

    # 1. LOGIKA SENIN: LIST 25 USERNAME
    if mode == 'senin' and update.message.text and update.message.text.startswith('@'):
        usernames = re.findall(r'@\w+', update.message.text)
        if len(usernames) < 25:
            await update.message.reply_text(f"❌ Kurang sayang! Baru {len(usernames)} username. Kirim 25 ya!")
            return
        
        # Cek Duplikat
        for u in usernames:
            c.execute("SELECT content FROM used_data WHERE content=?", (u,))
            if c.fetchone():
                await update.message.reply_text(f"Ih! @{user.username} curang ya? Username {u} udah pernah dipake absen! Gagal deh‼️😾")
                return
        
        for u in usernames: c.execute("INSERT INTO used_data VALUES (?)", (u,))
        conn.commit()
        await update.message.reply_text(f"Absensi di hari {now.strftime('%A')}, {jam_full}, {tgl_full} Berhasil. Terimakasih! ✅🩵")

    # 2. LOGIKA JUMAT: FOTO + TANGGAL (OCR)
    elif mode == 'jumat' and update.message.photo:
        wait = await update.message.reply_text("Bentar ya, aku pake kacamata dulu buat scan dulu fotonya... 🔍")
        file = await update.message.photo[-1].get_file()
        img_bytes = await file.download_as_bytearray()
        text_foto = pytesseract.image_to_string(Image.open(BytesIO(img_bytes)))
        
        if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', text_foto):
            await wait.edit_text(f"Absensi di hari {now.strftime('%A')}, {jam_full}, {tgl_full} Berhasil. Terimakasih! ✅🩵")
        else:
            await wait.edit_text("❌ Foto tampak tidak jelas/tanpa tanggal. Absensi Gagal‼️😾")

    # 3. LOGIKA MINGGU: 20 LINK
    elif mode == 'minggu' and update.message.text:
        links = re.findall(r'https?://\S+', update.message.text)
        if len(links) < 20:
            await update.message.reply_text(f"❌ Baru {len(links)} link, minimal 20 ya‼️")
            return
        
        for l in links:
            c.execute("SELECT content FROM used_data WHERE content=?", (l,))
            if c.fetchone():
                await update.message.reply_text("Duh! Ada link lama nih, jangan curang ya! Absensi Gagal‼️😾")
                return
        
        for l in links: c.execute("INSERT INTO used_data VALUES (?)", (l,))
        conn.commit()
        await update.message.reply_text(f"Absensi di hari {now.strftime('%A')}, {jam_full}, {tgl_full} Berhasil. Terimakasih! ✅🩵")

    # 4. TRACK BROADCAST (OTOMATIS)
    elif update.message.text and not update.message.text.startswith('/'):
        c.execute("INSERT INTO bc_logs VALUES (?, ?, ?)", (user.id, user.username, now.strftime('%Y-%m-%d')))
        conn.commit()

    conn.close()

# --- CEK STATISTIK (ESTETIK) ---
async def cek_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    tgl_ini = datetime.now(TIME_ZONE).strftime('%Y-%m-%d')
    
    c.execute("SELECT COUNT(*) FROM bc_logs WHERE user_id=? AND tgl=?", (user.id, tgl_ini))
    hari = c.fetchone()[0]
    
    c.execute("SELECT tgl, COUNT(*) as jml FROM bc_logs WHERE user_id=? GROUP BY tgl ORDER BY jml DESC LIMIT 1", (user.id,))
    rekor = c.fetchone()
    rekor_txt = f"_{rekor[0]} sejumlah {rekor[1]} bc_" if rekor else "_belum ada rekor_"

    await update.message.reply_text(
        f"🩵 Selamat {get_sapaan()}, @{user.username} 💭\n\n"
        f"🐾 Broadcast hari ini : **{hari}**\n"
        f"🐾 Broadcast 1 pekan : (on progress)\n"
        f"🐾 Broadcast tertinggi : {rekor_txt}\n\n"
        f"Jangan lupa makan roll cake ya! 🍰", parse_mode='Markdown'
    )
    conn.close()

# --- OWNER SET HUKUMAN ---
async def set_hukuman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if f"@{update.effective_user.username}" != OWNER_USERNAME: return
    text = " ".join(context.args)
    if not text: return await update.message.reply_text("Contoh: /sethukuman 1. Push up 10x")
    conn = sqlite3.connect('cinnabot_pro.db')
    conn.execute("UPDATE settings SET value=? WHERE key='konsekuensi'", (text,))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Hukuman Master sudah aku simpan! 🐾")

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("absen", menu_absen))
    app.add_handler(CommandHandler("cek", cek_stat))
    app.add_handler(CommandHandler("sethukuman", set_hukuman))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, process_message))
    app.run_polling()
