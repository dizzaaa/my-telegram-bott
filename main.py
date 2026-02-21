import sqlite3
import re
import pytz
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Konfigurasi Master ---
token = '8389389993:AAFBzImBYwxlo1uaCFnFG3RzMJ7gf8pUwwo'
owner_username = '@cinnamoroiLi'
group_log_id = -5151128223  
channel_id = '@RekberEloise'
time_zone = pytz.timezone('Asia/Jakarta')

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

async def cek_member_channel(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def menu_utama(is_master=False):
    kbd = [
        [InlineKeyboardButton("☁️ Menu Absen", callback_data='menu_absen')],
        [InlineKeyboardButton("💰 Cek Poin", callback_data='cek_poin'), InlineKeyboardButton("📊 Progress BBC", callback_data='cek_bbc')],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')]
    ]
    return InlineKeyboardMarkup(kbd)

# --- Handler Utama ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type == 'private':
        conn = sqlite3.connect('cinnabot_pro.db')
        conn.execute("insert or ignore into absen_status (user_id, username) values (?,?)", (user.id, user.username))
        conn.commit(); conn.close()
        await update.message.reply_text(f"Hellow Master {user.first_name}! 🩵\nSiap setor absen hari ini? 🧁", 
                                       reply_markup=menu_utama(f"@{user.username}" == owner_username))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == 'menu_absen':
        kbd = [[InlineKeyboardButton("Senin ☁️", callback_data='m_senin')],
               [InlineKeyboardButton("Jumat 📸", callback_data='m_jumat')],
               [InlineKeyboardButton("Minggu 🔗", callback_data='m_minggu')],
               [InlineKeyboardButton("🔙 Kembali", callback_data='back')]]
        await q.edit_message_text("Pilih jadwal absenmu manis: 🩵", reply_markup=InlineKeyboardMarkup(kbd))
    elif q.data == 'back':
        context.user_data['mode'] = None
        await q.edit_message_text("Main Menu 🩵💭", reply_markup=menu_utama(f"@{q.from_user.username}" == owner_username))
    elif q.data.startswith('m_'):
        mode = q.data.replace('m_', '')
        context.user_data['mode'] = mode
        await q.edit_message_text(f"Mode {mode.capitalize()} aktif! 🩵\nKirim datanya sekarang ya...", 
                                  reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Batal", callback_data='back')]]))

# --- Jalur Master (Grup Log) ---
async def group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != group_log_id: return
    text = update.message.text
    
    if text and text.startswith("/done") and update.message.reply_to_message:
        caption = update.message.reply_to_message.caption or ""
        u_id_search = re.search(r'ID: `(\d+)`', caption)
        if u_id_search:
            tid = int(u_id_search.group(1))
            conn = sqlite3.connect('cinnabot_pro.db')
            conn.execute("update absen_status set points=points+50, jumat=1 where user_id=?", (tid,))
            res = conn.execute("select senin, jumat, minggu, username from absen_status where user_id=?", (tid,)).fetchone()
            conn.commit(); conn.close()
            
            notif = (f"Jaseb Jumat kamu sudah di-done Master! 🩵\n\n"
                     f"Senin: {'✅' if res[0] else '❌'}\n"
                     f"Jumat: ✅\nMinggu: {'✅' if res[2] else '❌'}\n\n"
                     f"Makin rajin ya @{res[3]}! 🧁🍭")
            await context.bot.send_message(chat_id=tid, text=notif)
            await update.message.reply_text(f"Absen @{res[3]} sukses di-konfirmasi! ✅")

# --- Jalur Private (Member) ---
async def private_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != 'private': return
    user = update.effective_user
    text = update.message.text
    mode = context.user_data.get('mode')

    # Audit Senin/Minggu (Wajib Join Channel & 1 Bubble)
    if mode in ['senin', 'minggu'] and text:
        is_joined = await cek_member_channel(user.id, context)
        if not is_joined:
            return await update.message.reply_text(f"Eits! Join dulu ke channel {channel_id} baru bisa absen manis! 😾☁️")

        finds = re.findall(r'@\w+' if mode == 'senin' else r'http[s]?://\S+', text)
        req = 25 if mode == 'senin' else 20
        if len(finds) >= req:
            conn = sqlite3.connect('cinnabot_pro.db')
            for f in finds:
                dupe = conn.execute("select user_id from used_data where content=?", (f,)).fetchone()
                if dupe and dupe[0] != user.id:
                    conn.execute("update absen_status set warning=warning+1, points=points-50 where user_id=?", (user.id,))
                    conn.commit(); conn.close()
                    return await update.message.reply_text("Duplikat terdeteksi! Kamu dapet SP 🟡")
            
            for f in finds: conn.execute("insert or replace into used_data values (?,?)", (f, user.id))
            conn.execute(f"update absen_status set points=points+50, {mode}=1 where user_id=?", (user.id,))
            conn.commit(); conn.close()
            context.user_data['mode'] = None
            await context.bot.send_message(chat_id=group_log_id, text=f"Lapor! @{user.username} absen {mode} lengkap (1 bubble) ✅")
            return await update.message.reply_text(f"Absen {mode} berhasil! 🩵🍭")
        else:
            return await update.message.reply_text(f"Kurang manis! Wajib {req} data dlm 1 bubble! ☁️")

    # Foto Jumat
    if mode == 'jumat' and update.message.photo:
        await context.bot.send_photo(chat_id=group_log_id, photo=update.message.photo[-1].file_id, 
                                     caption=f"Jaseb Jumat: @{user.username}\nID: `{user.id}`\nMaster reply /done 💭")
        context.user_data['mode'] = None
        return await update.message.reply_text("Jaseb terkirim ke Master! 🩵🧁")

    # BBC Counter
    if text and not mode and ("http" in text or "@" in text):
        conn = sqlite3.connect('cinnabot_pro.db')
        conn.execute("update absen_status set bbc_count=bbc_count+1 where user_id=?", (user.id,))
        conn.commit(); conn.close()

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.Chat(group_log_id), group_handler))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, private_handler))
    app.run_polling()
