#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import dataclasses
import os
import random
import sqlite3
import sys
import time
from typing import Iterable, Optional

import requests
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
from dotenv import load_dotenv

# -----------------------------
# تحميل متغيرات .env
# -----------------------------
load_dotenv()

API_URL = "https://api.alquran.cloud/v1/ayah/"
TOTAL_AYAT = 6236

DB_PATH = os.environ.get("DB_PATH", "quran_bot.db")
DEFAULT_INTERVAL = int(os.environ.get("DEFAULT_INTERVAL", "30"))
LOOP_TICK_SECONDS = int(os.environ.get("LOOP_TICK_SECONDS", "30"))
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# -----------------------------
# قاعدة البيانات
# -----------------------------
@dataclasses.dataclass
class ChannelConf:
    chat_id: str
    interval_minutes: int
    enabled: bool
    last_post_ts: int


def db_connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """CREATE TABLE IF NOT EXISTS channels (
            chat_id TEXT PRIMARY KEY,
            interval_minutes INTEGER NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_post_ts INTEGER NOT NULL DEFAULT 0
        )"""
    )
    con.commit()
    return con


def db_upsert_channel(con, chat_id: str, interval_minutes: int, enabled: bool = True):
    con.execute(
        """
        INSERT INTO channels (chat_id, interval_minutes, enabled, last_post_ts)
        VALUES (?, ?, ?, COALESCE((SELECT last_post_ts FROM channels WHERE chat_id = ?), 0))
        ON CONFLICT(chat_id) DO UPDATE SET
            interval_minutes=excluded.interval_minutes,
            enabled=excluded.enabled
        """,
        (chat_id, interval_minutes, 1 if enabled else 0, chat_id),
    )
    con.commit()


def db_list_channels(con) -> Iterable[ChannelConf]:
    cur = con.execute("SELECT chat_id, interval_minutes, enabled, last_post_ts FROM channels")
    for row in cur.fetchall():
        yield ChannelConf(row[0], row[1], bool(row[2]), row[3])


def db_get_channel(con, chat_id: str) -> Optional[ChannelConf]:
    cur = con.execute(
        "SELECT chat_id, interval_minutes, enabled, last_post_ts FROM channels WHERE chat_id = ?",
        (chat_id,),
    )
    row = cur.fetchone()
    return ChannelConf(*row) if row else None


def db_set_enabled(con, chat_id: str, enabled: bool) -> bool:
    cur = con.execute("UPDATE channels SET enabled=? WHERE chat_id=?", (1 if enabled else 0, chat_id))
    con.commit()
    return cur.rowcount > 0


def db_set_interval(con, chat_id: str, minutes: int) -> bool:
    cur = con.execute("UPDATE channels SET interval_minutes=? WHERE chat_id=?", (minutes, chat_id))
    con.commit()
    return cur.rowcount > 0


def db_touch_posted(con, chat_id: str):
    con.execute("UPDATE channels SET last_post_ts=? WHERE chat_id=?", (int(time.time()), chat_id))
    con.commit()


def db_enable_all(con, enabled: bool):
    con.execute("UPDATE channels SET enabled=?", (1 if enabled else 0,))
    con.commit()


def db_set_interval_all(con, minutes: int):
    con.execute("UPDATE channels SET interval_minutes=?", (minutes,))
    con.commit()


# -----------------------------
# جلب آيات القرآن
# -----------------------------
class QuranProvider:
    def __init__(self, timeout: float = 10.0, retries: int = 3, backoff: float = 1.5):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

    def _get(self, url: str) -> Optional[dict]:
        delay = 0.0
        for attempt in range(1, self.retries + 1):
            try:
                if delay:
                    time.sleep(delay)
                r = requests.get(url, timeout=self.timeout)
                if r.status_code == 200:
                    return r.json()
            except Exception as e:
                print(f"[HTTP] attempt {attempt} error: {e}")
            delay = self.backoff * attempt
        return None

    def random_ayah_text(self) -> Optional[str]:
        idx = random.randint(1, TOTAL_AYAT)
        data = self._get(API_URL + str(idx))
        if not data or "data" not in data:
            return None
        d = data["data"]
        text = d.get("text", "").strip()
        surah = d.get("surah", {}).get("name", "").strip()
        number = d.get("numberInSurah", 0)
        return f"{text}\n\n({surah} • آية {number})\n\n— #قرآن #Quran"


quran = QuranProvider()

# -----------------------------
# تحقق صلاحيات المالك
# -----------------------------
def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id if update.effective_user else 0
        if uid != OWNER_ID:
            return await update.effective_message.reply_text("⛔️ غير مخول.")
        return await func(update, context)

    return wrapper

# -----------------------------
# أوامر البوت
# -----------------------------
@owner_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌙 أوامر التحكم:\n\n"
        "/addchannel @channel 30 — إضافة/تحديث قناة\n"
        "/setinterval @channel 45 — تغيير الفاصل\n"
        "/enable @channel — تفعيل النشر\n"
        "/disable @channel — إيقاف النشر\n"
        "/list — استعراض القنوات\n"
        "/testpost @channel — إرسال تجريبي\n\n"
        "— أوامر عامة —\n"
        "/setinterval_all 30 — تعديل للجميع\n"
        "/enable_all — تفعيل الجميع\n"
        "/disable_all — إيقاف الجميع"
    )

@owner_only
async def cmd_addchannel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        return await update.message.reply_text("⚠️ الاستعمال: /addchannel @channel [minutes]")
    chat = context.args[0]
    minutes = int(context.args[1]) if len(context.args) > 1 else DEFAULT_INTERVAL
    con = db_connect()
    db_upsert_channel(con, chat, max(1, minutes), True)
    await update.message.reply_text(f"✅ تمت إضافة/تحديث {chat} كل {minutes} دقيقة.")

@owner_only
async def cmd_setinterval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await update.message.reply_text("⚠️ الاستعمال: /setinterval @channel 45")
    chat = context.args[0]
    try:
        minutes = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("🚫 عدد الدقائق غير صالح.")
    con = db_connect()
    if db_set_interval(con, chat, minutes):
        await update.message.reply_text(f"✅ تم تعديل الفاصل لـ {chat} → {minutes} دقيقة.")
    else:
        await update.message.reply_text("❌ لم أجد القناة بقاعدة البيانات.")

@owner_only
async def cmd_enable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ الاستعمال: /enable @channel")
    chat = context.args[0]
    con = db_connect()
    if db_set_enabled(con, chat, True):
        await update.message.reply_text(f"✅ تم تفعيل النشر في {chat}.")
    else:
        await update.message.reply_text("❌ لم أجد القناة.")

@owner_only
async def cmd_disable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ الاستعمال: /disable @channel")
    chat = context.args[0]
    con = db_connect()
    if db_set_enabled(con, chat, False):
        await update.message.reply_text(f"🚫 تم إيقاف النشر في {chat}.")
    else:
        await update.message.reply_text("❌ لم أجد القناة.")

@owner_only
async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = db_connect()
    rows = list(db_list_channels(con))
    if not rows:
        return await update.message.reply_text("ℹ️ لا توجد قنوات محفوظة.")
    msg = "📋 القنوات:\n\n"
    for r in rows:
        msg += f"{r.chat_id} — كل {r.interval_minutes} دقيقة — {'✅' if r.enabled else '❌'}\n"
    await update.message.reply_text(msg)

@owner_only
async def cmd_testpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ الاستعمال: /testpost @channel")
    chat = context.args[0]
    msg = quran.random_ayah_text() or "تعذر جلب آية الآن."
    try:
        await context.bot.send_message(chat_id=chat, text=msg)
        await update.message.reply_text(f"✅ أرسلت رسالة تجريبية إلى {chat}.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")

@owner_only
async def cmd_setinterval_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ الاستعمال: /setinterval_all 30")
    try:
        minutes = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("🚫 عدد الدقائق غير صالح.")
    con = db_connect()
    db_set_interval_all(con, minutes)
    await update.message.reply_text(f"✅ تم تعديل الفاصل للجميع إلى {minutes} دقيقة.")

@owner_only
async def cmd_enable_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = db_connect()
    db_enable_all(con, True)
    await update.message.reply_text("✅ تم تفعيل النشر للجميع.")

@owner_only
async def cmd_disable_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = db_connect()
    db_enable_all(con, False)
    await update.message.reply_text("🚫 تم إيقاف النشر للجميع.")


# -----------------------------
# Loop للنشر التلقائي
# -----------------------------
async def scheduler_loop(app: Application):
    print(f"[LOOP] tick={LOOP_TICK_SECONDS}s default={DEFAULT_INTERVAL}m db={DB_PATH}")
    con = db_connect()
    while True:
        try:
            now = int(time.time())
            for row in list(db_list_channels(con)):
                if not row.enabled:
                    continue
                due = (row.last_post_ts == 0) or (now - row.last_post_ts >= row.interval_minutes * 60)
                if not due:
                    continue
                msg = quran.random_ayah_text() or "تعذر جلب آية الآن."
                try:
                    await app.bot.send_message(chat_id=row.chat_id, text=msg)
                    db_touch_posted(con, row.chat_id)
                    print(f"[POST] sent → {row.chat_id}")
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"[POST] error to {row.chat_id}: {e}")
        except Exception as e:
            print("[LOOP] unexpected error:", e)
        await asyncio.sleep(LOOP_TICK_SECONDS)


# -----------------------------
# Bootstrapping
# -----------------------------
def main():
    if not BOT_TOKEN or OWNER_ID == 0:
        print("[CONFIG] BOT_TOKEN أو OWNER_ID مفقودين في .env")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # أوامر
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("addchannel", cmd_addchannel))
    app.add_handler(CommandHandler("setinterval", cmd_setinterval))
    app.add_handler(CommandHandler("enable", cmd_enable))
    app.add_handler(CommandHandler("disable", cmd_disable))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("testpost", cmd_testpost))
    app.add_handler(CommandHandler("setinterval_all", cmd_setinterval_all))
    app.add_handler(CommandHandler("enable_all", cmd_enable_all))
    app.add_handler(CommandHandler("disable_all", cmd_disable_all))

    # شغل اللوب بعد ما يبدأ البوت
    async def post_init(application: Application):
        asyncio.create_task(scheduler_loop(application))

    app.post_init = post_init

    print("[RUN] polling…")
    app.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("[SYS] stopped by user.")