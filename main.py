import sqlite3
import logging
from datetime import datetime, timedelta, time
import pytz

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
)

# ================= CONFIG =================

TOKEN = "8389389993:AAFBzImBYwxlo1uaCFnFG3RzMJ7gf8pUwwo"
CHANNEL_USERNAME = "@RekberEloise"
CHANNEL_ID = -1001946813667
UANG_DONE_GROUP_ID = -5151128223
OWNER_USERNAME = "@cinnamoroiLi"

TIMEZONE = pytz.timezone("Asia/Jakarta")

# ==========================================

logging.basicConfig(level=logging.INFO)

db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()

# ================= DATABASE =================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    senin INTEGER DEFAULT 0,
    jumat INTEGER DEFAULT 0,
    minggu INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS used_usernames (
    username TEXT PRIMARY KEY,
    used_by INTEGER,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS join_logs (
    username TEXT PRIMARY KEY,
    join_time TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS weekly_archive (
    user_id INTEGER,
    username TEXT,
    senin INTEGER,
    jumat INTEGER,
    minggu INTEGER,
    points INTEGER,
    archived_at TIMESTAMP
)
""")

db.commit()

# ================= UTIL =================

def get_calling_name(username: str):
    if username == OWNER_USERNAME:
        return "Master 👑"
    return "Paw paw cinnamoon!"

def save_user(user):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user.id, user.username)
    )
    db.commit()

async def log_activity(context: ContextTypes.DEFAULT_TYPE, text: str):
    await context.bot.send_message(UANG_DONE_GROUP_ID, text)

# ================= JOIN TRACKER =================

async def track_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        username = member.new_chat_member.user.username
        if username:
            cursor.execute(
                "INSERT OR REPLACE INTO join_logs (username, join_time) VALUES (?, ?)",
                (username.lower(), datetime.now(TIMEZONE).isoformat())
            )
            db.commit()

# ================= CEK ABSEN =================

async def cek_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    cursor.execute(
        "SELECT senin, jumat, minggu, points FROM users WHERE user_id=?",
        (user.id,)
    )
    data = cursor.fetchone()

    senin = "✅" if data[0] else "⛔️"
    jumat = "✅" if data[1] else "⛔️"
    minggu = "✅" if data[2] else "⛔️"

    text = f"""
Halo @{user.username} 💭

Status absen kamu:

Senin  : {senin}
Jumat  : {jumat}
Minggu : {minggu}

Total Poin: {data[3]} ✨
"""
    await update.message.reply_text(text)

# ================= HANDLE SENIN =================

async def handle_senin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)

    # hanya bisa kirim hari Senin
    if now.weekday() != 0:
        return

    user = update.effective_user
    save_user(user)

    lines = update.message.text.strip().split("\n")
    usernames = [u.strip().lower() for u in lines if u.strip()]

    errors = []

    if len(usernames) != 25:
        errors.append("Jumlah username harus 25.")

    if len(usernames) != len(set(usernames)):
        errors.append("Ada username dobel.")

    for u in usernames:
        if not u.startswith("@"):
            errors.append(f"{u} tidak memakai @")

    for u in usernames:
        uname = u.replace("@", "")

        cursor.execute("SELECT 1 FROM used_usernames WHERE username=?", (uname,))
        if cursor.fetchone():
            errors.append(f"{u} sudah pernah digunakan.")

        cursor.execute("SELECT join_time FROM join_logs WHERE username=?", (uname,))
        row = cursor.fetchone()

        if not row:
            errors.append(f"{u} bukan member baru.")
        else:
            join_time = datetime.fromisoformat(row[0])
            if now - join_time > timedelta(days=1):
                errors.append(f"{u} lebih dari 1 hari.")

    if errors:
        await update.message.reply_text(
            "❌ Ada kesalahan:\n\n" + "\n".join(errors)
        )
        return

    for u in usernames:
        uname = u.replace("@", "")
        cursor.execute(
            "INSERT INTO used_usernames (username, used_by) VALUES (?, ?)",
            (uname, user.id)
        )

    cursor.execute("""
    UPDATE users
    SET senin=1,
        points=points+50
    WHERE user_id=?
    """, (user.id,))

    db.commit()

    await update.message.reply_text("🎉 25 Username valid!\nPoin +50 ✨")

    await log_activity(
        context,
        f"{user.username} berhasil absen Senin +50 poin"
    )

# ================= LEADERBOARD =================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("""
    SELECT username, points FROM users
    ORDER BY points DESC LIMIT 10
    """)
    rows = cursor.fetchall()

    text = "🏆 LEADERBOARD 🏆\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. @{row[0]} — {row[1]} poin\n"

    await update.message.reply_text(text)

# ================= WEEKLY RESET =================

async def weekly_reset(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)

    if now.weekday() == 0:  # Senin
        logging.info("Weekly reset berjalan")

        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        for user in users:
            cursor.execute("""
                INSERT INTO weekly_archive
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (*user, now.isoformat()))

        # reset absen
        cursor.execute("""
        UPDATE users
        SET senin=0,
            jumat=0,
            minggu=0
        """)

        # reset username yang pernah dipakai
        cursor.execute("DELETE FROM used_usernames")

        db.commit()

        await context.bot.send_message(
            UANG_DONE_GROUP_ID,
            "🔄 Reset mingguan selesai.\nData minggu lalu sudah diarsipkan."
        )

# ================= REMINDER =================

async def reminder(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE)
    if now.weekday() != 0:
        return

    cursor.execute("SELECT user_id, username FROM users WHERE senin=0")
    users = cursor.fetchall()

    for user_id, username in users:
        try:
            await context.bot.send_message(
                user_id,
                f"Halo @{username} 🌙\n5 jam lagi absen Senin ditutup!"
            )
        except:
            pass

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(ChatMemberHandler(track_join, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CommandHandler("cek", cek_absen))
    app.add_handler(CommandHandler("leaderboard", leaderboard))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_senin
    ))

    # reset tiap hari jam 00:00 (akan jalan hanya jika Senin)
    app.job_queue.run_daily(
        weekly_reset,
        time=time(0, 0, tzinfo=TIMEZONE)
    )

    # reminder jam 19:00 WIB
    app.job_queue.run_daily(
        reminder,
        time=time(19, 0, tzinfo=TIMEZONE)
    )

    app.run_polling()

if __name__ == "__main__":
    main()
