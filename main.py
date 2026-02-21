import sqlite3
import re
import pytz
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- identitas rahasia cinnabot ---
token = '8389389993:AAFBzImBYwxlo1uaCFnFG3RzMJ7gf8pUwwo'
owner_username = '@cinnamoroiLi'
group_log_id = -5151128223  
time_zone = pytz.timezone('Asia/Jakarta')

# --- bikin rumah buat data (database) ---
def init_db():
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    c.execute('create table if not exists brain (keyword text primary key, response text)')
    c.execute('create table if not exists used_data (content text primary key)')
    c.execute('create table if not exists settings (key text primary key, value text)')
    c.execute('''create table if not exists absen_status 
                 (user_id integer primary key, username text, senin integer default 0, 
                  jumat integer default 0, minggu integer default 0, 
                  points integer default 0, warning integer default 0, bbc_count integer default 0)''')
    conn.commit()
    conn.close()

# --- ambil setting custom dari master ---
def get_setting(key, default):
    conn = sqlite3.connect('cinnabot_pro.db')
    res = conn.execute("select value from settings where key=?", (key,)).fetchone()
    conn.close()
    return res[0] if res else default

# --- sapu-sapu otomatis tiap senin pagi ---
async def reset_mingguan(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('cinnabot_pro.db')
    c = conn.cursor()
    c.execute("update absen_status set warning = warning + 1 where (senin=0 or jumat=0 or minggu=0 or bbc_count < 500)")
    c.execute("update absen_status set senin=0, jumat=0, minggu=0, bbc_count=0")
    c.execute("delete from used_data")
    conn.commit()
    conn.close()
    await context.bot.send_message(chat_id=group_log_id, text="wushhh! udah senin pagi, semua data aku sapu bersih ya master! yang males udah aku kasih kartu kuning manja 🩵💭")

def get_panggilan(user):
    return f"@{user.username}" if user.username else user.first_name

def main_menu():
    return ReplyKeyboardMarkup([[KeyboardButton("☁️ menu absen"), KeyboardButton("📊 progress bbc")],
                                [KeyboardButton("💰 cek poin"), KeyboardButton("🏆 leaderboard")],
                                [KeyboardButton("💭 tanya cinna")]], resize_keyboard=True)

# --- awal perjumpaan ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_chat.type == 'private':
        conn = sqlite3.connect('cinnabot_pro.db')
        conn.execute("insert or ignore into absen_status (user_id, username) values (?,?)", (user.id, user.username))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"hellow bellow master {get_panggilan(user)}! 🩵 cinnabot siap temenin hari-hari kamu! mau ngapain kita hari ini? 💭🧁", reply_markup=main_menu())

# --- tombol-tombol lucu ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == 'm_senin':
        context.user_data['mode'] = 'senin'
        await q.edit_message_text("mode senin aktif! kirim 25 username @ kamu ya manis! jangan ada yang typo ☁️🧁")
    elif q.data == 'm_jumat':
        context.user_data['mode'] = 'jumat'
        await q.edit_message_text("mode jumat aktif! mana screenshot grid jaseb kamu? sini kasih ke aku 📸🩵")
    elif q.data == 'm_minggu':
        context.user_data['mode'] = 'minggu'
        await q.edit_message_text("mode minggu aktif! kirim 20 link laporan kamu sekarang ya sayang 🔗💭")
    elif q.data == 'back':
        context.user_data['mode'] = None
        kbd = [[InlineKeyboardButton("senin ☁️", callback_data='m_senin')],
               [InlineKeyboardButton("jumat 📸", callback_data='m_jumat')],
               [InlineKeyboardButton("minggu 🔗", callback_data='m_minggu')]]
        await q.edit_message_text("mau absen apa hari ini? pilih ya! 🩵", reply_markup=InlineKeyboardMarkup(kbd))

# --- pusat kendali pesan ---
async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    mode = context.user_data.get('mode')
    panggilan = get_panggilan(user)

    # 1. fitur khusus grup (master/admin log)
    if update.effective_chat.id == group_log_id:
        # fitur /set_link buat custom audit
        if text and text.startswith("/set_link ") and f"@{user.username}" == owner_username:
            syarat = text.replace("/set_link ", "").strip()
            conn = sqlite3.connect('cinnabot_pro.db')
            conn.execute("insert or replace into settings values ('link_keyword', ?)", (syarat,))
            conn.commit()
            conn.close()
            return await update.message.reply_text(f"beres master! sekarang link absen minggu harus ada kata '{syarat}' ya 🩵💭")

        # fitur /done buat jaseb
        if text == "/done" and update.message.reply_to_message:
            u_id_match = re.search(r'ID: `(\d+)`', update.message.reply_to_message.caption or "")
            if u_id_match:
                tid = int(u_id_match.group(1))
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("update absen_status set points = points + 50, jumat = 1 where user_id=?", (tid,))
                conn.commit()
                conn.close()
                await context.bot.send_message(chat_id=tid, text="yay! jaseb kamu udah di-done sama master! poin kamu nambah 50 ya sayang 🩵💭🍭")
                return await update.message.reply_text("beres master! notifnya udah aku bisikin ke usernya 🧁")

        # fitur /add poin manual
        if text and text.startswith("/add ") and update.message.reply_to_message:
            try:
                amount = int(text.split()[1])
                tid = update.message.reply_to_message.from_user.id
                u_id_cap = re.search(r'ID: `(\d+)`', update.message.reply_to_message.caption or "")
                if u_id_cap: tid = int(u_id_cap.group(1))
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("update absen_status set points = points + ? where user_id=?", (amount, tid))
                conn.commit()
                conn.close()
                await context.bot.send_message(chat_id=tid, text=f"yeay! kamu dapet bonus {amount} poin dari master! makin semangat ya manis 🩵💭🍭")
                return await update.message.reply_text(f"sip master! {amount} poin sudah meluncur ✨")
            except: pass

        # fitur /warn (potong 50 poin)
        if text == "/warn" and update.message.reply_to_message:
            try:
                tid = update.message.reply_to_message.from_user.id
                u_id_cap = re.search(r'ID: `(\d+)`', update.message.reply_to_message.caption or "")
                if u_id_cap: tid = int(u_id_cap.group(1))
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("update absen_status set warning = warning + 1, points = points - 50 where user_id=?", (tid,))
                conn.commit()
                conn.close()
                await context.bot.send_message(chat_id=tid, text="aduh... kamu melanggar aturan master. poin dipotong 50 dan dapet kartu kuning 🥺💔💭")
                return await update.message.reply_text("hukuman dilaksanakan! poin dia aku potong 50 master 🟡")
            except: pass

        # fitur /cek progress
        if text == "/cek" and update.message.reply_to_message:
            target = update.message.reply_to_message.from_user
            conn = sqlite3.connect('cinnabot_pro.db')
            res = conn.execute("select senin, jumat, minggu, bbc_count from absen_status where user_id=?", (target.id,)).fetchone()
            conn.close()
            if res:
                s, j, m, b = res
                msg = f"laporan kerja {get_panggilan(target)}:\nsenin: {'✅' if s else '❌'}\njumat: {'✅' if j else '❌'}\nminggu: {'✅' if m else '❌'}\nbbc: {b}/500 🩵💭"
                return await update.message.reply_text(msg)

        # fitur ngajar ai (custom brain)
        if update.message.reply_to_message and "master, ada yang nanya" in update.message.reply_to_message.text:
            q_match = re.search(r'`(.*?)`', update.message.reply_to_message.text)
            if q_match:
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("insert or replace into brain values (?, ?)", (q_match.group(1).lower(), text))
                conn.commit()
                conn.close()
                return await update.message.reply_text("oke master! sekarang aku udah pinter jawab itu 🧠🩵")

    # 2. fitur pribadi (member manis)
    if update.effective_chat.type == 'private':
        if text == "☁️ menu absen":
            kbd = [[InlineKeyboardButton("senin ☁️", callback_data='m_senin')],
                   [InlineKeyboardButton("jumat 📸", callback_data='m_jumat')],
                   [InlineKeyboardButton("minggu 🔗", callback_data='m_minggu')]]
            return await update.message.reply_text("mau setor absen apa hari ini manis? 🩵🧁", reply_markup=InlineKeyboardMarkup(kbd))
        
        elif text == "📊 progress bbc":
            conn = sqlite3.connect('cinnabot_pro.db')
            res = conn.execute("select bbc_count from absen_status where user_id=?", (user.id,)).fetchone()
            conn.close()
            count = res[0] if res else 0
            return await update.message.reply_text(f"progress bbc kamu: {count}/500! ayo semangat lagi biar master seneng 🩵💭🏃‍♂️")

        elif text == "💰 cek poin":
            conn = sqlite3.connect('cinnabot_pro.db')
            res = conn.execute("select points, warning from absen_status where user_id=?", (user.id,)).fetchone()
            conn.close()
            wrn = "🟡" * res[1] if res and res[1] > 0 else "🟢 bersih"
            return await update.message.reply_text(f"poin kamu: {res[0] if res else 0} 💰\nstatus sp: {wrn}\njaga kelakuan ya manis 🩵🧁")

        elif text == "🏆 leaderboard":
            conn = sqlite3.connect('cinnabot_pro.db')
            top = conn.execute("select username, points from absen_status order by points desc limit 5").fetchall()
            conn.close()
            msg = "piala pekerja terrajin minggu ini 🏆\n\n"
            for i, (u, p) in enumerate(top, 1): msg += f"{i}. @{u} - {p} poin\n"
            return await update.message.reply_text(msg + "\npertahankan ya manis! 🩵🧁")

        # logika audit absen (custom keyword)
        if mode in ['senin', 'minggu'] and text:
            finds = re.findall(r'@\w+' if mode == 'senin' else r'http[s]?://\S+', text)
            req = 25 if mode == 'senin' else 20
            
            # cek syarat custom link buat hari minggu
            if mode == 'minggu':
                keyword = get_setting('link_keyword', '')
                if keyword and not all(keyword in f for f in finds):
                    return await update.message.reply_text(f"duh manis, linknya salah! master bilang harus ada kata '{keyword}' di setiap link ya! 🩵💭")

            if len(finds) >= req:
                conn = sqlite3.connect('cinnabot_pro.db')
                for f in finds:
                    if conn.execute("select 1 from used_data where content=?", (f,)).fetchone():
                        conn.close()
                        return await update.message.reply_text("jangan pakai data basi dong! aku tau ini udah pernah dipakai 🩵💭😾")
                for f in finds: conn.execute("insert into used_data values (?)", (f,))
                conn.execute(f"update absen_status set points = points + 50, {mode} = 1 where user_id=?", (user.id,))
                conn.commit()
                conn.close()
                context.user_data['mode'] = None
                await context.bot.send_message(chat_id=group_log_id, text=f"lapor master! {panggilan} udah setor absen {mode} 🩵🧁")
                return await update.message.reply_text(f"absen {mode} berhasil! poin kamu nambah 50 ya sayang 💭🍭")
            else:
                return await update.message.reply_text(f"eits kurang! harus ada {req} ya biar aku terima 🩵☁️")

        if mode == 'jumat' and update.message.photo:
            await context.bot.send_photo(chat_id=group_log_id, photo=update.message.photo[-1].file_id,
                caption=f"ada jaseb jumat baru! 🩵\ndari: {panggilan}\nid: `{user.id}`\nmaster tinggal reply pke /done ya! 💭")
            context.user_data['mode'] = None
            return await update.message.reply_text("foto jaseb udah aku kasih ke master! tunggu di-done ya sayang 🩵🧁")

        # bbc counter & ai
        if text and not text.startswith('/'):
            if "http" in text or "@" in text or "t.me/" in text:
                conn = sqlite3.connect('cinnabot_pro.db')
                conn.execute("update absen_status set bbc_count = bbc_count + 1 where user_id=?", (user.id,))
                conn.commit()
                conn.close()
                return
            
            await context.bot.send_message(chat_id=group_log_id, text=f"master, ada yang nanya nih dari {panggilan}:\n`{text}`", parse_mode='Markdown')
            conn = sqlite3.connect('cinnabot_pro.db')
            ans = conn.execute("select response from brain where keyword=?", (text.lower(),)).fetchone()
            conn.close()
            await update.message.reply_text(ans[0] if ans else "aduh manis, master lagi sibuk banget. nanti aku tanyain ya! 🩵💭☁️")

if __name__ == '__main__':
    init_db()
    app = Application.builder().token(token).build()
    if app.job_queue: app.job_queue.run_daily(reset_mingguan, time=time(0, 0), days=(0,))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, process_message))
    app.run_polling()
