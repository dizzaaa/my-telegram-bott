import sqlite3
import re
import pytz
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Konfigurasi Identitas ---
token = '8389389993:AAFBzImBYwxlo1uaCFnFG3RzMJ7gf8pUwwo'
owner_username = '@cinnamoroiLi'
group_log_id = -5151128223        # GRUP LOG (Master /done)
group_member_id = -5246034154     # GRUP MEMBER & ADMIN
channel_id = '@RekberEloise'
time_zone = pytz.timezone('Asia/Jakarta')

# --- Database ---
def init_db():
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    c.execute('create table if not exists used_data (content text primary key, user_id integer)')
    c.execute('create table if not exists archive (week_num integer, username text, senin integer, jumat integer, minggu integer, bbc_count integer)')
    c.execute('''create table if not exists absen_status 
                 (user_id integer primary key, username text, senin integer default 0, 
                  jumat integer default 0, minggu integer default 0, 
                  points integer default 0, warning integer default 0, bbc_count integer default 0)''')
    conn.commit()
    conn.close()

# --- Helpers ---
async def is_member(user_id, context):
    try:
        m = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return m.status in ['member', 'administrator', 'creator']
    except: return False

def pm_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("☁️ menu absen"), KeyboardButton("📊 progress bbc")],
        [KeyboardButton("💰 cek poin"), KeyboardButton("🏆 leaderboard")]
    ], resize_keyboard=True)

# --- JALUR CALLBACK (TOMBOL) ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    
    if q.data.startswith("m_"):
        mode = q.data.replace("m_", "")
        context.user_data['mode'] = mode
        await q.edit_message_text(f"Mode {mode.capitalize()} aktif! 🩵\nKirim datanya sekarang ya manis...")
    
    elif q.data.startswith("check_bbc_"):
        tid = q.data.split("_")[2]
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("select bbc_count from absen_status where user_id=?", (tid,)).fetchone()
        conn.close()
        await q.message.reply_text(f"📊 BBC Count member: {res[0] if res else 0}")

    elif q.data.startswith("ask_master_"):
        await q.message.reply_text("Pertanyaanmu sudah Cinna kirim ke Master! ☁️")
        await context.bot.send_message(chat_id=group_log_id, 
            text=f"🆘 **TANYA MASTER**\nDari: @{q.from_user.username}\nID: `{q.from_user.id}`\n\nReply pesan ini untuk jawab! 🧁")

# --- JALUR GRUP LOG (-5151128223) ---
async def handle_log_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return

    if text.startswith("/done") and update.message.reply_to_message:
        cap = update.message.reply_to_message.caption or ""
        match = re.search(r'ID: `(\d+)`', cap)
        if match:
            tid = int(match.group(1))
            conn = sqlite3.connect('cinnabot_pro.db')
            conn.execute("update absen_status set points=points+50, jumat=1 where user_id=?", (tid,))
            res = conn.execute("select senin, jumat, minggu, username from absen_status where user_id=?", (tid,)).fetchone()
            conn.commit(); conn.close()
            notif = f"Jaseb Jumat kamu sudah di-done Master! 🩵\n\nSenin: {'✅' if res[0] else '❌'}\nJumat: ✅\nMinggu: {'✅' if res[2] else '❌'}\n\nSemangat @{res[3]}! 🧁"
            await context.bot.send_message(chat_id=tid, text=notif)
            await update.message.reply_text(f"Berhasil! @{res[3]} sudah di-done. ✅")

    elif update.message.reply_to_message and "ID:" in update.message.reply_to_message.text:
        match = re.search(r'ID: `(\d+)`', update.message.reply_to_message.text)
        if match:
            tid = int(match.group(1))
            msg = f"Hellow manis! 🍭 Cinna bawa surat dari Master {owner_username}!\n\n💭: \"{text}\"\n\nLucu banget kan? Hehe 🩵☁️"
            await context.bot.send_message(chat_id=tid, text=msg)
            await update.message.reply_text("Pesan balasan terkirim! 🐾")

# --- JALUR GRUP MEMBER (-5246034154) ---
async def handle_member_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text and text.startswith("/absensi") and update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("select senin, jumat, minggu, points, warning from absen_status where user_id=?", (target.id,)).fetchone()
        conn.close()
        if res:
            msg = f"📝 **Status Absen @{target.username}**\n\nSenin: {'✅' if res[0] else '❌'}\nJumat: {'✅' if res[1] else '❌'}\nMinggu: {'✅' if res[2] else '❌'}\n\nPoin: {res[3]} | SP: {res[4]}"
            kbd = [[InlineKeyboardButton("📊 Cek BBC", callback_data=f"check_bbc_{target.id}"),
                    InlineKeyboardButton("☁️ Tanya Master", callback_data=f"ask_master_{target.id}")]]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kbd), parse_mode='Markdown')

# --- JALUR PRIVATE ---
async def handle_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    mode = context.user_data.get('mode')

    if text == "🏆 leaderboard":
        conn = sqlite3.connect('cinnabot_pro.db')
        top = conn.execute("select username, points from absen_status order by points desc limit 5").fetchall()
        conn.close()
        msg = "🏆 **LEADERBOARD POIN**\n" + "\n".join([f"{i+1}. @{u[0]} - {u[1]} pts" for i, u in enumerate(top)])
        return await update.message.reply_text(msg, parse_mode='Markdown')
    
    elif text == "💰 cek poin":
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("select points, warning from absen_status where user_id=?", (user.id,)).fetchone()
        conn.close()
        return await update.message.reply_text(f"Poin: {res[0] if res else 0} 💰 | SP: {res[1] if res else 0} ⚠️")

    elif text == "📊 progress bbc":
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("select bbc_count from absen_status where user_id=?", (user.id,)).fetchone()
        conn.close()
        return await update.message.reply_text(f"📊 Broadcast kamu: {res[0] if res else 0} kali. 🩵")

    elif text == "☁️ menu absen":
        kbd = [[InlineKeyboardButton("Senin ☁️", callback_data='m_senin')], 
               [InlineKeyboardButton("Jumat 📸", callback_data='m_jumat')], 
               [InlineKeyboardButton("Minggu 🔗", callback_data='m_minggu')]]
        return await update.message.reply_text("Mau setor absen apa? 🩵", reply_markup=InlineKeyboardMarkup(kbd))

    # Logika Absen Teks
    if text and mode in ['senin', 'minggu']:
        if not await is_member(user.id, context): return await update.message.reply_text(f"Join {channel_id} dulu! 😾")
        finds = re.findall(r'@\w+' if mode == 'senin' else r'http[s]?://\S+', text)
        req = 25 if mode == 'senin' else 20
        if len(finds) >= req:
            conn = sqlite3.connect('cinnabot_pro.db')
            for f in finds:
                d = conn.execute("select user_id from used_data where content=?", (f,)).fetchone()
                if d and d[0] != user.id:
                    conn.execute("update absen_status set warning=warning+1, points=points-50 where user_id=?", (user.id,))
                    conn.commit(); conn.close()
                    return await update.message.reply_text("DUPLIKAT! SP + Potong 50 poin! 🟡")
            for f in finds: conn.execute("insert or replace into used_data values (?,?)", (f, user.id))
            conn.execute(f"update absen_status set points=points+50, {mode}=1 where user_id=?", (user.id,))
            conn.commit(); conn.close()
            context.user_data['mode'] = None
            await context.bot.send_message(chat_id=group_log_id, text=f"Lapor! @{user.username} absen {mode} ✅")
            return await update.message.reply_text(f"Absen {mode} sukses! 🍭")

    # BBC Counter & Auto-Register (PENTING!)
    if text and not mode and ("@" in text or "http" in text):
        conn = sqlite3.connect('cinnabot_pro.db')
        conn.execute("insert or ignore into absen_status (user_id, username) values (?,?)", (user.id, user.username or "Unknown"))
        conn.execute("update absen_status set bbc_count=bbc_count+1 where user_id=?", (user.id,))
        conn.commit(); conn.close()

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private': return
    user = update.effective_user
    if context.user_data.get('mode') == 'jumat':
        await context.bot.send_photo(chat_id=group_log_id, photo=update.message.photo[-1].file_id, 
                                     caption=f"Jaseb Jumat: @{user.username}\nID: `{user.id}`\nMaster reply /done 💭")
        context.user_data['mode'] = None
        await update.message.reply_text("Jaseb terkirim ke Master! 🧁")

# --- Fitur Reset & Arsip ---
async def reset_mingguan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if f"@{update.effective_user.username}" != owner_username: return
    week = datetime.now(time_zone).isocalendar()[1]
    conn = sqlite3.connect('cinnabot_pro.db')
    data = conn.execute("select username, senin, jumat, minggu, bbc_count from absen_status").fetchall()
    for r in data: conn.execute("insert into archive values (?,?,?,?,?,?)", (week, *r))
    conn.execute("update absen_status set senin=0, jumat=0, minggu=0, bbc_count=0")
    conn.execute("delete from used_data")
    conn.commit(); conn.close()
    await update.message.reply_text(f"✅ Data Minggu {week} sudah diarsip & reset! 🩵")

# --- MAIN ---
if __name__ == '__main__':
    init_db()
    app = Application.builder().token(token).build()
    
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Hellow!", reply_markup=pm_keyboard()) if u.effective_chat.type == 'private' else None))
    app.add_handler(CommandHandler("reset_mingguan", reset_mingguan))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    app.add_handler(MessageHandler(filters.Chat(group_log_id), handle_log_group))
    app.add_handler(MessageHandler(filters.Chat(group_member_id), handle_member_group))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_private))
    
    app.run_polling()
    
