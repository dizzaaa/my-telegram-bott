import sqlite3
import logging
import re
from datetime import datetime, timedelta, time
import pytz

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
)

# ================= CONFIG =================
TOKEN = "8389389993:AAHFz3HbVQeuWKmQFkVDvjmJVNTqkWx9Wn0"
CHANNEL_USERNAME = "@RekberEloise"
CHANNEL_ID = -1001946813667
UANG_DONE_GROUP_ID = -5151128223
OWNER_USERNAME = "cinnamoroiLi"  
TIMEZONE = pytz.timezone("Asia/Jakarta")

# ================= DATABASE =================
db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()

def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        senin INTEGER DEFAULT 0,
        jumat INTEGER DEFAULT 0,
        minggu INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0
    )""")
    cursor.execute("CREATE TABLE IF NOT EXISTS used_usernames (username TEXT PRIMARY KEY, used_by INTEGER, used_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    cursor.execute("CREATE TABLE IF NOT EXISTS join_logs (username TEXT PRIMARY KEY, join_time TEXT)")
    db.commit()

# ================= UTIL & LOGIC =================
def save_user(user):
    if not user.username: return
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user.id, user.username.lower()))
    db.commit()

async def log_activity(context: ContextTypes.DEFAULT_TYPE, text: str):
    try: await context.bot.send_message(UANG_DONE_GROUP_ID, text)
    except: pass

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    await update.message.reply_text(
        f"Hellow Master @{user.username}! 🩵\nCinna siap bantu catat absen hari ini. Gunakan /cek buat lihat progress kamu ya manis! 🐾☁️",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/cek"), KeyboardButton("/leaderboard")]], resize_keyboard=True)
    )

async def track_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        user = member.new_chat_member.user
        if user.username:
            cursor.execute("INSERT OR REPLACE INTO join_logs VALUES (?, ?)", 
                         (user.username.lower(), datetime.now(TIMEZONE).isoformat()))
            db.commit()

async def cek_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    cursor.execute("SELECT senin, jumat, minggu, points FROM users WHERE user_id=?", (user.id,))
    data = cursor.fetchone()
    
    if not data:
        return await update.message.reply_text("Data kamu belum ada di buku catatan Cinna... 🥺")

    text = (f"Halo @{user.username} 💭\n\n"
            f"Senin  : {'✅' if data[0] else '❌'}\n"
            f"Jumat  : {'✅' if data[1] else '❌'}\n"
            f"Minggu : {'✅' if data[2] else '❌'}\n\n"
            f"Total Poin: {data[3]} ✨\nSemangat terus ya Master! 🍭")
    await update.message.reply_text(text)

async def handle_senin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)
    if now.weekday() != 0:
        return await update.message.reply_text("Sekarang bukan hari Senin, Master sayang... Simpan dulu ya! 🤫")

    user = update.effective_user
    save_user(user)
    
    lines = update.message.text.strip().split("\n")
    usernames = [u.strip().lower() for u in lines if u.strip()]
    errors = []

    if len(usernames) != 25: errors.append("Jumlahnya harus 25 ya, jangan kurang/lebih! 😾")
    if len(usernames) != len(set(usernames)): errors.append("Ada username dobel nih, hayo dicek lagi! 😼")

    for u in usernames:
        if not u.startswith("@"): 
            errors.append(f"{u} nggak pake @")
            continue
        uname = u.replace("@", "")
        cursor.execute("SELECT 1 FROM used_usernames WHERE username=?", (uname,))
        if cursor.fetchone(): errors.append(f"{u} sudah pernah dipake orang lain... 🥺")
        
        cursor.execute("SELECT join_time FROM join_logs WHERE username=?", (uname,))
        row = cursor.fetchone()
        if not row: errors.append(f"{u} bukan member baru di channel Rekber Eloise 🟡")
        else:
            join_time = datetime.fromisoformat(row[0])
            if now - join_time > timedelta(days=1): errors.append(f"{u} sudah lebih dari 24 jam... ⏰")

    if errors:
        return await update.message.reply_text("❌ **Waduh, ada salah nih Master:**\n\n" + "\n".join(errors))

    for u in usernames:
        cursor.execute("INSERT INTO used_usernames VALUES (?, ?, CURRENT_TIMESTAMP)", (u.replace("@",""), user.id))
    
    cursor.execute("UPDATE users SET senin=1, points=points+50 WHERE user_id=?", (user.id,))
    db.commit()
    await update.message.reply_text("🎉 Horeee! 25 Username valid! Poin Master nambah +50 ✨")
    await log_activity(context, f"✅ @{user.username} Berhasil Absen Senin!")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 10")
    rows = cursor.fetchall()
    text = "🏆 **LEADERBOARD TER-GEMOY** 🏆\n\n"
    for i, row in enumerate(rows, 1): text += f"{i}. @{row[0]} — {row[1]} pts 💰\n"
    await update.message.reply_text(text)

async def weekly_reset(context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("UPDATE users SET senin=0, jumat=0, minggu=0")
    cursor.execute("DELETE FROM used_usernames")
    db.commit()
    await log_activity(context, "🔄 Reset mingguan selesai, Master! Buku catatan sudah bersih lagi ☁️")

# ================= MAIN =================
def main():
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    # Cegah Crash Jika JobQueue Gagal
    if app.job_queue:
        app.job_queue.run_daily(weekly_reset, time=time(0, 0, tzinfo=TIMEZONE))
        logging.info("JobQueue jalan! Auto-reset standby.")
    else:
        logging.warning("JobQueue TIDAK ditemukan. Install: pip install python-telegram-bot[job-queue]")

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(track_join, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("cek", cek_absen))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_senin))

    print("CinnaBot PRO sudah bangun dan siap melayani Master! 🐾☁️")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
