import sqlite3
import re
import pytz
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- BIAR CINNABOT KENAL MASTER ---
TOKEN = '8389389993:AAFBzImBYwxlo1uaCFnFG3RzMJ7gf8pUwwo'
OWNER_USERNAME = '@cinnamoroiLi'
GROUP_LOG_ID = -5151128223  
TIME_ZONE = pytz.timezone('Asia/Jakarta')

# --- DAPUR RAHASIA CINNABOT (DATABASE) ---
def init_db():
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS brain (keyword TEXT PRIMARY KEY, response TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS used_data (content TEXT PRIMARY KEY)')
    c.execute('''CREATE TABLE IF NOT EXISTS absen_status 
                 (user_id INTEGER PRIMARY KEY, username TEXT, senin INTEGER DEFAULT 0, 
                  jumat INTEGER DEFAULT 0, minggu INTEGER DEFAULT 0, 
                  points INTEGER DEFAULT 0, warning INTEGER DEFAULT 0, bbc_count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

# --- SI SAPU AJAIB (RESET MINGGUAN) ---
async def reset_mingguan(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    # Kasih kartu kuning buat yang males (BBC kurang 500 atau absen bolong)
    c.execute("UPDATE absen_status SET warning = warning + 1 WHERE (senin=0 OR jumat=0 OR minggu=0 OR bbc_count < 500)")
    c.execute("UPDATE absen_status SET senin=0, jumat=0, minggu=0, bbc_count=0")
    c.execute("DELETE FROM used_data")
    conn.commit()
    conn.close()
    await context.bot.send_message(chat_id=GROUP_LOG_ID, text="🌀 **WUSHHH!** Udah Senin subuh, database aku sapu bersih ya Master! Yang males udah aku ksh kartu kuning manja! 🟡😾")

def get_panggilan(user):
    return f"@{user.username}" if user.username else user.first_name

def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("☁️ Menu Absen"), KeyboardButton("📊 Progress BBC")],
        [KeyboardButton("💰 Cek Poin"), KeyboardButton("🏆 Leaderboard")],
        [KeyboardButton("💬 Tanya Cinnabot")]
    ], resize_keyboard=True)

# --- MULAI AKSI! ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect('cinnabot_pro.db')
    conn.execute("INSERT OR IGNORE INTO absen_status (user_id, username) VALUES (?,?)", (user.id, user.username))
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"Hellow Bellow Sayangnya Cinnabot, {get_panggilan(user)}! 🐾\nAku udah siap nemenin kamu kerja rodi di bawah perintah Master @cinnamoroiLi! Semangat kejar **500 BBC** ya manis! ✨🍭",
        reply_markup=main_menu()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text_map = {
        'm_senin': "📝 **MODE SENIN**: Kirim 25 username @ kamu ya manis! Jangan ada yang ketinggalan!",
        'm_jumat': "📸 **MODE JUMAT**: Mana screenshot grid jaseb-mu? Sini ksh aku, nanti aku bisikin Master!",
        'm_minggu': "🔗 **MODE MINGGU**: Kirim 20 link laporanmu! Pastiin link-nya bener ya cantik/ganteng!"
    }
    if q.data in text_map:
        context.user_data['mode'] = q.data.replace('m_', '')
        await q.edit_message_text(text_map[q.data], 
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Ga Jadi Deh", callback_data='back')]]))
    elif q.data == 'back':
        context.user_data['mode'] = None
        kbd = [[InlineKeyboardButton("☁️ Senin", callback_data='m_senin')],
               [InlineKeyboardButton("📸 Jumat", callback_data='m_jumat')],
               [InlineKeyboardButton("🔗 Minggu", callback_data='m_minggu')]]
        await q.edit_message_text("✨ Mau absen hari apa hari ini? Klik ya!", reply_markup=InlineKeyboardMarkup(kbd))

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    mode = context.user_data.get('mode')
    panggilan = get_panggilan(user)

    # 1. POLISI STIKER (Hapus kalau bukan Master)
    if update.message.sticker and f"@{user.username}" != OWNER_USERNAME:
        try: await update.message.delete()
        except: pass
        return

    # 2. TOA MASTER (/bc)
    if text and text.startswith('/bc ') and f"@{user.username}" == OWNER_USERNAME:
        msg_bc = text.replace('/bc ', '')
        conn = sqlite3.connect('cinnabot_pro.db')
        users = conn.execute("SELECT user_id FROM absen_status").fetchall()
        for u in users:
            try: await context.bot.send_message(chat_id=u[0], text=f"📢 **PESAN CINTA DARI MASTER:**\n\n{msg_bc}")
            except: continue
        conn.close()
        return await update.message.reply_text("✅ Pesan Master udah aku sebar ke seluruh dunia! Muach! 💋")

    # 3. PENGHITUNG BBC (Otomatis hitung link/forward-an)
    if text and not mode and update.effective_chat.id != GROUP_LOG_ID:
        if "http" in text or "@" in text or "t.me/" in text:
            conn = sqlite3.connect('cinnabot_pro.db')
            conn.execute("UPDATE absen_status SET bbc_count = bbc_count + 1 WHERE user_id=?", (user.id,))
            res = conn.execute("SELECT bbc_count FROM absen_status WHERE user_id=?", (user.id,)).fetchone()
            conn.commit()
            conn.close()
            if res and res[0] % 50 == 0:
                await update.message.reply_text(f"🔥 **WOW!** BBC kamu udah tembus {res[0]}! Sedikit lagi 500, semangat manis! 🧁")
            return

    # 4. MENU CEK-CEK
    if text == "☁️ Menu Absen":
        kbd = [[InlineKeyboardButton("☁️ Senin", callback_data='m_senin')],
               [InlineKeyboardButton("📸 Jumat", callback_data='m_jumat')],
               [InlineKeyboardButton("🔗 Minggu", callback_data='m_minggu')]]
        return await update.message.reply_text("Mau absen apa hari ini? Jangan telat ya nanti Master sedih! 🥺", reply_markup=InlineKeyboardMarkup(kbd))
    
    elif text == "📊 Progress BBC":
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("SELECT bbc_count FROM absen_status WHERE user_id=?", (user.id,)).fetchone()
        conn.close()
        count = res[0] if res else 0
        persen = min((count / 500) * 100, 100)
        bar = "🟦" * int(persen/10) + "⬜" * (10 - int(persen/10))
        return await update.message.reply_text(f"📊 **NASIB BBC KAMU**\n\nTarget: 500\nTerkirim: **{count}**\nProgress: {bar} {int(persen)}%\n\n" + ("Bentar lagi dapet reward! 🎁" if count >= 500 else "Ayo gaspol lagi larinya! 🏃‍♂️"))

    elif text == "💰 Cek Poin":
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("SELECT points, warning FROM absen_status WHERE user_id=?", (user.id,)).fetchone()
        conn.close()
        wrn = "🟡" * res[1] if res and res[1] > 0 else "🟢 Bersih"
        return await update.message.reply_text(f"💰 Poin kamu: **{res[0] if res else 0}**\n⚠️ Status SP: {wrn}\n\nJaga kelakuan ya biar poinnya makin tumpah-tumpah! 🍭")

    # 5. ABSEN MODE (SENIN/MINGGU)
    if mode in ['senin', 'minggu'] and text:
        finds = re.findall(r'@\w+' if mode == 'senin' else r'http[s]?://\S+', text)
        req = 25 if mode == 'senin' else 20
        if len(finds) >= req:
            conn = sqlite3.connect('cinnabot_pro.db')
            for f in finds:
                if conn.execute("SELECT 1 FROM used_data WHERE content=?", (f,)).fetchone():
                    conn.close()
                    return await update.message.reply_text("❌ Duh manis, jangan pake data basi dong! Aku tau ini udah pernah dipake! 😾")
            for f in finds: conn.execute("INSERT INTO used_data VALUES (?)", (f,))
            conn.execute(f"UPDATE absen_status SET points = points + 50, {mode} = 1 WHERE user_id=?", (user.id,))
            conn.commit()
            conn.close()
            context.user_data['mode'] = None
            await context.bot.send_message(chat_id=GROUP_LOG_ID, text=f"✅ **LAPOR MASTER!** {panggilan} udah setor absen {mode.upper()} nih!")
            return await update.message.reply_text(f"Absen {mode} berhasil! Poin kamu nambah 50, makin kaya deh! ✅✨")
        else:
            return await update.message.reply_text(f"Eits! Kurang dikit lagi! Harus {req} biar aku terima ya sayang~ ☁️")

    # 6. JASEB JUMAT
    if mode == 'jumat' and update.message.photo:
        await context.bot.send_photo(chat_id=GROUP_LOG_ID, photo=update.message.photo[-1].file_id,
            caption=f"🚨 **ADA JASEB JUMAT NIH!**\nDari: {panggilan}\nID: `{user.id}`\n\nMaster @cinnamoroiLi bales pke `/done` ya!")
        context.user_data['mode'] = None
        return await update.message.reply_text("Foto jaseb-mu udah aku ksh ke Master. Duduk manis ya nunggu di-done! ☕☁️")

    # 7. BALASAN MASTER (DONE & TEACH)
    if update.effective_chat.id == GROUP_LOG_ID:
        if text == "/done" and update.message.reply_to_message:
            u_id = re.search(r'ID: `(\d+)`', update.message.reply_to_message.caption or "")
            if u_id:
                tid = int(u_id.group(1))
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("UPDATE absen_status SET points = points + 50, jumat = 1 WHERE user_id=?", (tid,))
                conn.commit()
                conn.close()
                await context.bot.send_message(chat_id=tid, text="✨ **YAY!** Jaseb kamu udah di-DONE sama Master! Poin nambah 50 ya! ✅🍭")
                return await update.message.reply_text("Sip! Notif beres, poin sukses nambah! ✅")

        if update.message.reply_to_message and "💬 Tanya Jawab" in update.message.reply_to_message.text:
            q_match = re.search(r'`(.*?)`', update.message.reply_to_message.text)
            if q_match:
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("INSERT OR REPLACE INTO brain VALUES (?, ?)", (q_match.group(1).lower(), text))
                conn.commit()
                conn.close()
                return await update.message.reply_text("✅ Oke Master! Sekarang aku udah pinter jawab itu! 🧠✨")

    # 8. TANYA JAWAB & AI
    if text and not text.startswith('/') and update.effective_chat.id != GROUP_LOG_ID:
        await context.bot.send_message(chat_id=GROUP_LOG_ID, text=f"💬 **Master, {panggilan} nanya nih:**\n`{text}`", parse_mode='Markdown')
        conn = sqlite3.connect('cinnabot_pro.db')
        ans = conn.execute("SELECT response FROM brain WHERE keyword=?", (text.lower(),)).fetchone()
        conn.close()
        if ans:
            await update.message.reply_text(ans[0].format(user=panggilan))
        else:
            await update.message.reply_text("Aduh manis, Master lagi sibuk banget urus dunia. Nanti aku bisikin ya kalau Master udah luang! ☁️🩵")

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(TOKEN).build()
    if app.job_queue: app.job_queue.run_daily(reset_mingguan, time=time(0, 0), days=(0,))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_message))
    app.run_polling()
