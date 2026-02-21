import sqlite3
import re
import pytz
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Konfigurasi Master ---
token = '8389389993:AAFBzImBYwxlo1uaCFnFG3RzMJ7gf8pUwwo'
owner_username = '@cinnamoroiLi'
group_log_id = -5151128223  
channel_id = '@RekberEloise'
time_zone = pytz.timezone('Asia/Jakarta')

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    # Digunakan untuk simpan data unik per minggu (anti-duplikat)
    c.execute('create table if not exists used_data (content text primary key, user_id integer)')
    # Simpan pengaturan custom master
    c.execute('create table if not exists settings (key text primary key, value text)')
    # Simpan sejarah mingguan
    c.execute('create table if not exists archive (week_num integer, user_info text, status text)')
    # Data utama member
    c.execute('''create table if not exists absen_status 
                 (user_id integer primary key, username text, senin integer default 0, 
                  jumat integer default 0, minggu integer default 0, 
                  points integer default 0, warning integer default 0, bbc_count integer default 0)''')
    conn.commit()
    conn.close()

# --- Menu Keyboards ---
def main_menu(is_admin=False):
    kbd = [[KeyboardButton("☁️ menu absen"), KeyboardButton("📊 progress bbc")],
           [KeyboardButton("💰 cek poin"), KeyboardButton("🏆 leaderboard")]]
    if is_admin:
        kbd.append([KeyboardButton("📜 rangkapan absen")])
    return ReplyKeyboardMarkup(kbd, resize_keyboard=True)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 kembali", callback_data='back')]])

# --- Reset Mingguan & Archive ---
async def reset_mingguan(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('cinnabot_pro.db')
    users = conn.execute("select username, senin, jumat, minggu, bbc_count, user_id from absen_status").fetchall()
    week_num = datetime.now(time_zone).isocalendar()[1]
    
    for u in users:
        is_lengkap = (u[1] and u[2] and u[3] and u[4] >= 500)
        status = "lengkap" if is_lengkap else "bolos"
        info = f"@{u[0]} (bbc: {u[4]})"
        conn.execute("insert into archive values (?, ?, ?)", (week_num, info, status))
        if not is_lengkap:
            conn.execute("update absen_status set warning = warning + 1, points = points - 50 where user_id=?", (u[5],))

    conn.execute("update absen_status set senin=0, jumat=0, minggu=0, bbc_count=0")
    conn.execute("delete from used_data")
    conn.commit()
    conn.close()
    await context.bot.send_message(chat_id=group_log_id, text=f"laporan minggu {week_num} sudah diarsip master! 🩵💭")

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_master = (f"@{user.username}" == owner_username)
    if update.effective_chat.type == 'private':
        conn = sqlite3.connect('cinnabot_pro.db')
        conn.execute("insert or ignore into absen_status (user_id, username) values (?,?)", (user.id, user.username))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"hellow master {user.first_name}! 🩵 mau setor absen apa? 💭🧁", reply_markup=main_menu(is_master))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == 'm_senin':
        context.user_data['mode'] = 'senin'
        await q.edit_message_text("mode senin aktif! kirim 25 uname dalam satu bubble (list 1-25) ☁️🧁", reply_markup=back_button())
    elif q.data == 'm_jumat':
        context.user_data['mode'] = 'jumat'
        await q.edit_message_text("mode jumat aktif! kirim screenshot grid jaseb kamu 📸🩵", reply_markup=back_button())
    elif q.data == 'm_minggu':
        context.user_data['mode'] = 'minggu'
        await q.edit_message_text("mode minggu aktif! kirim 20 link dalam satu bubble 🔗💭", reply_markup=back_button())
    elif q.data == 'back':
        context.user_data['mode'] = None
        kbd = [[InlineKeyboardButton("senin ☁️", callback_data='m_senin')],
               [InlineKeyboardButton("jumat 📸", callback_data='m_jumat')],
               [InlineKeyboardButton("minggu 🔗", callback_data='m_minggu')]]
        await q.edit_message_text("mau absen apa hari ini? 🩵", reply_markup=InlineKeyboardMarkup(kbd))

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    mode = context.user_data.get('mode')
    is_master = (f"@{user.username}" == owner_username)

    # 1. Fitur Grup Log (Master Only)
    if update.effective_chat.id == group_log_id:
        if text == "📜 rangkapan absen" and is_master:
            conn = sqlite3.connect('cinnabot_pro.db')
            data = conn.execute("select week_num, user_info, status from archive order by week_num desc limit 50").fetchall()
            conn.close()
            if not data: return await update.message.reply_text("arsip kosong ☁️")
            msg = "laporan mingguan 📑\n\n"
            cw = None
            for w, info, st in data:
                if w != cw: msg += f"minggu {w}:\n"; cw = w
                msg += f"{'✅' if st=='lengkap' else '❌'} {info}\n"
            return await update.message.reply_text(msg)

        if text == "/done" and update.message.reply_to_message:
            u_id = re.search(r'ID: `(\d+)`', update.message.reply_to_message.caption or "")
            if u_id:
                tid = int(u_id.group(1))
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("update absen_status set points = points + 50, jumat = 1 where user_id=?", (tid,))
                res = conn.execute("select senin, jumat, minggu from absen_status where user_id=?", (tid,)).fetchone()
                conn.commit(); conn.close()
                notif = f"jaseb jumat di-done! 🩵\nsenin: {'✅' if res[0] else '❌'}\njumat: {'✅' if res[1] else '❌'}\nminggu: {'✅' if res[2] else '❌'}\nsemangat! 🧁"
                await context.bot.send_message(chat_id=tid, text=notif)
                return await update.message.reply_text("notif forward sukses! ✅")

    # 2. Fitur Private (Member)
    if update.effective_chat.type == 'private':
        if mode in ['senin', 'minggu'] and text:
            finds = re.findall(r'@\w+' if mode == 'senin' else r'http[s]?://\S+', text)
            req = 25 if mode == 'senin' else 20
            if len(finds) >= req:
                conn = sqlite3.connect('cinnabot_pro.db')
                for f in finds:
                    dupe = conn.execute("select user_id from used_data where content=?", (f,)).fetchone()
                    if dupe and dupe[0] != user.id:
                        conn.execute("update absen_status set warning=warning+1, points=points-50 where user_id=?", (user.id,))
                        conn.commit(); conn.close()
                        return await update.message.reply_text(f"duplikat terdeteksi pada {f}! SP + potong 50 poin! 😾🟡")
                for f in finds: conn.execute("insert or replace into used_data values (?,?)", (f, user.id))
                conn.execute(f"update absen_status set points=points+50, {mode}=1 where user_id=?", (user.id,))
                conn.commit(); conn.close()
                context.user_data['mode'] = None
                await context.bot.send_message(chat_id=group_log_id, text=f"lapor! @{user.username} absen {mode} lengkap (1 bubble) ✅")
                return await update.message.reply_text(f"absen {mode} sukses! 🩵🍭")
            else:
                return await update.message.reply_text(f"harus {req} data dalam satu bubble ya! ☁️")

        if mode == 'jumat' and update.message.photo:
            await context.bot.send_photo(chat_id=group_log_id, photo=update.message.photo[-1].file_id, 
                                         caption=f"jaseb jumat: @{user.username}\nID: `{user.id}`\nmaster reply /done 💭")
            context.user_data['mode'] = None
            return await update.message.reply_text("terkirim ke master! 🩵🧁")

        if text and not mode and ("http" in text or "@" in text):
            conn = sqlite3.connect('cinnabot_pro.db')
            conn.execute("update absen_status set bbc_count = bbc_count + 1 where user_id=?", (user.id,))
            conn.commit(); conn.close()

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(token).build()
    if app.job_queue: app.job_queue.run_daily(reset_mingguan, time=time(0, 0), days=(0,))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_message))
    app.run_polling()
