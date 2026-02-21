import sqlite3
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Konfigurasi Master ---
token = '8389389993:AAFBzImBYwxlo1uaCFnFG3RzMJ7gf8pUwwo'
owner_username = '@cinnamoroiLi'
group_log_id = -5151128223        # GRUP LOG (Master /done)
group_member_id = -5246034154     # GRUP MEMBER & ADMIN
channel_id = '@RekberEloise'

def init_db():
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    c.execute('create table if not exists used_data (content text primary key, user_id integer)')
    c.execute('''create table if not exists absen_status 
                 (user_id integer primary key, username text, senin integer default 0, 
                  jumat integer default 0, minggu integer default 0, 
                  points integer default 0, warning integer default 0, bbc_count integer default 0)''')
    conn.commit()
    conn.close()

# --- JALUR 1: LOGIKA GRUP LOG (-5151128223) ---
async def handle_log_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return

    # FITUR /DONE MASTER
    if text.startswith("/done") and update.message.reply_to_message:
        cap = update.message.reply_to_message.caption or ""
        match = re.search(r'ID: `(\d+)`', cap)
        if match:
            tid = int(match.group(1))
            conn = sqlite3.connect('cinnabot_pro.db')
            conn.execute("update absen_status set points=points+50, jumat=1 where user_id=?", (tid,))
            res = conn.execute("select senin, jumat, minggu, username from absen_status where user_id=?", (tid,)).fetchone()
            conn.commit(); conn.close()
            
            notif = f"Yeay! Jaseb Jumat kamu sudah di-done Master! 🩵\n\nSenin: {'✅' if res[0] else '❌'}\nJumat: ✅\nMinggu: {'✅' if res[2] else '❌'}\n\nSemangat @{res[3]}! 🧁"
            await context.bot.send_message(chat_id=tid, text=notif)
            await update.message.reply_text(f"Berhasil konfirmasi @{res[3]}! ✅")
            return

    # FITUR BALAS CHAT MEMBER (FORWARD)
    if update.message.reply_to_message and "ID:" in update.message.reply_to_message.text:
        match = re.search(r'ID: `(\d+)`', update.message.reply_to_message.text)
        if match:
            tid = int(match.group(1))
            msg = f"Hellow manis! 🍭 Ada pesan dari Master {owner_username}:\n\n💭: \"{text}\"\n\nLucu banget kan? Hehe 🩵☁️"
            await context.bot.send_message(chat_id=tid, text=msg)
            await update.message.reply_text("Pesan sudah Cinna sampaikan! 🐾")

# --- JALUR 2: LOGIKA GRUP MEMBER (-5246034154) ---
async def handle_member_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text: return

    # ADMIN CEK ABSENSI
    if text.startswith("/absensi") and update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("select senin, jumat, minggu, points, warning from absen_status where user_id=?", (target.id,)).fetchone()
        conn.close()
        
        if res:
            msg = (f"📝 **Status Absen @{target.username}**\n\n"
                   f"Senin: {'✅' if res[0] else '❌'}\n"
                   f"Jumat: {'✅' if res[1] else '❌'}\n"
                   f"Minggu: {'✅' if res[2] else '❌'}\n\n"
                   f"Poin: {res[3]} | SP: {res[4]}")
            kbd = [[InlineKeyboardButton("📊 Cek BBC", callback_data=f"check_bbc_{target.id}")],
                   [InlineKeyboardButton("☁️ Tanya Master", callback_data=f"ask_master_{target.id}")]]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kbd), parse_mode='Markdown')
        else:
            await update.message.reply_text("User ini belum terdaftar di sistem Cinna ☁️")

# --- JALUR 3: PRIVATE CHAT ---
async def handle_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    mode = context.user_data.get('mode')

    if text == "🏆 leaderboard":
        conn = sqlite3.connect('cinnabot_pro.db')
        top = conn.execute("select username, points from absen_status order by points desc limit 5").fetchall()
        conn.close()
        msg = "🏆 **TOP 5 LEADERBOARD**\n\n" + "\n".join([f"{i+1}. @{u[0]} - {u[1]} pts" for i, u in enumerate(top)])
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    elif text == "💰 cek poin":
        conn = sqlite3.connect('cinnabot_pro.db')
        res = conn.execute("select points, warning from absen_status where user_id=?", (user.id,)).fetchone()
        conn.close()
        await update.message.reply_text(f"Poin Master: {res[0] if res else 0} 💰\nSP: {res[1] if res else 0} ⚠️")

    elif text == "☁️ menu absen":
        kbd = [[InlineKeyboardButton("Senin ☁️", callback_data='m_senin')],
               [InlineKeyboardButton("Jumat 📸", callback_data='m_jumat')],
               [InlineKeyboardButton("Minggu 🔗", callback_data='m_minggu')]]
        await update.message.reply_text("Pilih menu absen kamu: 🩵", reply_markup=InlineKeyboardMarkup(kbd))

    # BBC Counter Otomatis di PM
    if text and not mode and ("@" in text or "http" in text):
        conn = sqlite3.connect('cinnabot_pro.db')
        conn.execute("update absen_status set bbc_count=bbc_count+1 where user_id=?", (user.id,))
        conn.commit(); conn.close()

# --- HANDLER FOTO ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private': return
    if context.user_data.get('mode') == 'jumat':
        await context.bot.send_photo(chat_id=group_log_id, photo=update.message.photo[-1].file_id, 
                                     caption=f"Jaseb Jumat: @{update.effective_user.username}\nID: `{update.effective_user.id}`\nMaster reply /done 💭")
        context.user_data['mode'] = None
        await update.message.reply_text("Jaseb terkirim ke Master! 🧁")

# --- MAIN RUNNER ---
if __name__ == '__main__':
    init_db()
    app = Application.builder().token(token).build()
    
    # 1. Callback (Tombol)
    app.add_handler(CallbackQueryHandler(handle_callback)) # Fungsi handle_callback tetap sama
    
    # 2. Grup Log Handler
    app.add_handler(MessageHandler(filters.Chat(group_log_id) & filters.TEXT, handle_log_group))
    
    # 3. Grup Member Handler
    app.add_handler(MessageHandler(filters.Chat(group_member_id) & filters.TEXT, handle_member_group))
    
    # 4. Private Handler
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_private))
    
    # 5. Start Command
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Hellow!", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("☁️ menu absen"), KeyboardButton("💰 cek poin")], [KeyboardButton("🏆 leaderboard")]], resize_keyboard=True)) if u.effective_chat.type == 'private' else None))

    app.run_polling()
