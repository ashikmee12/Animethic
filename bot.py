#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
অ্যানিমেথিক বট v2.0 - ডুয়াল মোড সার্চ সহ
✅ normal search (auto)
✅ /search command
✅ admin panel control
"""

import os
import logging
import json
import re
import threading
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from flask import Flask
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ========== কনফিগ ==========
BOT_TOKEN = "8763338417:AAHCzL74xO3YxG8ktSrGar3aUF7OzklS0Ko"
ADMIN_ID = 7406197326
GROUP_ID = -1002248871056
CHANNEL_ID = -1002225247609
BLOG_ID = "6445429841925204092"
API_KEY = "AIzaSyBd-2MBVvEpJMH1J8xfhT8uzDbxARaDc6Q"

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot Running"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== JSON ==========
def load_json(f, d):
    try:
        with open(f, 'r') as x:
            return json.load(x)
    except:
        return d

def save_json(f, d):
    with open(f, 'w') as x:
        json.dump(d, x, indent=4)

# ========== ডাটাবেস ==========
settings = load_json('settings.json', {
    "poster": {"enabled": True, "interval": 30, "button": "📥 DOWNLOAD", "template": "{title}\n\n[ {button} ]\n\n{link}"},
    "welcome": {"enabled": True, "msg": "👋 Welcome {name}!\nType anime name or /search"},
    "filter": {"enabled": True, "domains": ["animethic.in", "www.animethic.in"], "max_warnings": 3, "mute_duration": 60},
    "bot_name": "Anime Bot",
    "search": {"auto": True, "command": True}  # ডুয়াল মোড কন্ট্রোল
})
users = load_json('users.json', {})
stats = load_json('stats.json', {"req": 0, "w": 0, "m": 0, "b": 0, "anime": {}})

# ========== ইউজার ==========
def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {"w": 0, "m": False, "mu": None, "b": False, "join": str(datetime.now())}
        save_json('users.json', users)
    return users[uid]

def save_user(uid, d):
    users[str(uid)] = d
    save_json('users.json', users)

def is_admin(uid):
    return str(uid) == str(ADMIN_ID)

def ignore(u):
    return u.is_bot or is_admin(u.id)

# ========== API ==========
def search(q):
    if not API_KEY or not BLOG_ID:
        return []
    try:
        r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/search",
                        params={"key": API_KEY, "q": q, "maxResults": 3}, timeout=5)
        if r.status_code == 200:
            return [{"title": i["title"], "link": i["url"]} for i in r.json().get("items", [])]
    except:
        pass
    return []

def fuzzy_match(q, t):
    return SequenceMatcher(None, q.lower(), t.lower()).ratio()

def check_new():
    if not settings["poster"]["enabled"]:
        return []
    try:
        r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts",
                        params={"key": API_KEY, "maxResults": 1}, timeout=5)
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                post = items[0]
                last = settings.get("last")
                if post["id"] != last:
                    settings["last"] = post["id"]
                    save_json('settings.json', settings)
                    return [post]
    except:
        pass
    return []

# ========== সার্চ ফাংশন (কমন) ==========
async def perform_search(u, query, is_command=False):
    """সার্চ করে রেজাল্ট পাঠায়"""
    stats["req"] += 1
    save_json('stats.json', stats)
    
    res = search(query)
    if res:
        reply = f"🔍 **Found for '{query}':**\n\n"
        for r in res:
            reply += f"• **{r['title']}**\n📥 [Download]({r['link']})\n\n"
            stats["anime"][r['title']] = stats["anime"].get(r['title'], 0) + 1
        await u.reply_text(reply, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        await u.reply_text(f"🔍 '{query}' not found.")
    
    save_json('stats.json', stats)

# ========== কমান্ড ==========
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if ignore(u.effective_user):
        return
    await u.message.reply_text(f"🤖 {settings['bot_name']}\n\nType anime name or /search [name]")

async def help_(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if ignore(u.effective_user):
        return
    await u.message.reply_text("Type anime name or /search [name]")

# ========== সার্চ কমান্ড ==========
async def search_command(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """ /search anime name """
    if ignore(u.effective_user):
        return
    if not settings["search"]["command"]:
        await u.message.reply_text("❌ Search command is disabled")
        return
    if not c.args:
        await u.message.reply_text("Usage: /search [anime name]\nExample: /search Naruto Season 9")
        return
    query = ' '.join(c.args)
    await perform_search(u.message, query, is_command=True)

# ========== অ্যাডমিন প্যানেল ==========
async def panel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    k = [
        [InlineKeyboardButton("📊 Dashboard", cb="dash"), InlineKeyboardButton("📢 Poster", cb="post")],
        [InlineKeyboardButton("🔌 API", cb="api"), InlineKeyboardButton("⚙️ Settings", cb="set")],
        [InlineKeyboardButton("👥 Users", cb="users"), InlineKeyboardButton("🔍 Search", cb="search")]  # নতুন বাটন
    ]
    await u.message.reply_text("🔐 Panel", reply_markup=InlineKeyboardMarkup(k))

async def api_status(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    if API_KEY and BLOG_ID:
        try:
            r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts",
                            params={"key": API_KEY, "maxResults": 1}, timeout=5)
            if r.status_code == 200:
                await u.message.reply_text("✅ API Working")
            else:
                await u.message.reply_text(f"❌ API Error: {r.status_code}")
        except Exception as e:
            await u.message.reply_text(f"❌ API Error: {str(e)}")
    else:
        await u.message.reply_text("❌ API Not Configured")

async def btn(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    await q.answer()
    uid = q.from_user.id
    if not is_admin(uid):
        await q.edit_message_text("⛔ No permission")
        return
    d = q.data
    
    if d == "dash":
        text = f"📊 Dashboard\n\n👥 Users: {len(users)}\n📝 Requests: {stats['req']}\n⚠️ Warnings: {stats['w']}\n🔇 Mutes: {stats['m']}\n🚫 Bans: {stats['b']}"
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", cb="back")]]))
    
    elif d == "post":
        text = f"📢 Poster\n\nStatus: {'ON' if settings['poster']['enabled'] else 'OFF'}\nInterval: {settings['poster']['interval']}s\nButton: {settings['poster']['button']}"
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", cb="back")]]))
    
    elif d == "api":
        if API_KEY and BLOG_ID:
            try:
                r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts",
                                params={"key": API_KEY, "maxResults": 1}, timeout=5)
                text = "✅ API Working" if r.status_code == 200 else f"❌ API Error: {r.status_code}"
            except Exception as e:
                text = f"❌ API Error: {str(e)}"
        else:
            text = "❌ API Not Configured"
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", cb="back")]]))
    
    elif d == "set":
        text = (f"⚙️ Settings\n\n"
                f"👋 Welcome: {'ON' if settings['welcome']['enabled'] else 'OFF'}\n"
                f"🔗 Filter: {'ON' if settings['filter']['enabled'] else 'OFF'}\n"
                f"⚠️ Max Warn: {settings['filter']['max_warnings']}\n"
                f"🔇 Mute: {settings['filter']['mute_duration']}min\n")
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", cb="back")]]))
    
    elif d == "users":
        active = sum(1 for u in users.values() if u.get('last_active', '').startswith(str(datetime.now().date())))
        banned = sum(1 for u in users.values() if u.get('b'))
        muted = sum(1 for u in users.values() if u.get('m'))
        text = f"👥 Users\n\nTotal: {len(users)}\nActive: {active}\nBanned: {banned}\nMuted: {muted}"
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", cb="back")]]))
    
    # নতুন: সার্চ সেটিংস
    elif d == "search":
        text = (f"🔍 Search Settings\n\n"
                f"📝 Auto Search: {'ON' if settings['search']['auto'] else 'OFF'}\n"
                f"🔍 /search Command: {'ON' if settings['search']['command'] else 'OFF'}\n\n"
                f"Commands:\n"
                f"/search on/off - Toggle command\n"
                f"/auto on/off - Toggle auto search")
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", cb="back")]]))
    
    elif d == "back":
        k = [
            [InlineKeyboardButton("📊 Dashboard", cb="dash"), InlineKeyboardButton("📢 Poster", cb="post")],
            [InlineKeyboardButton("🔌 API", cb="api"), InlineKeyboardButton("⚙️ Settings", cb="set")],
            [InlineKeyboardButton("👥 Users", cb="users"), InlineKeyboardButton("🔍 Search", cb="search")]
        ]
        await q.edit_message_text("🔐 Panel", reply_markup=InlineKeyboardMarkup(k))

# ========== সার্চ কন্ট্রোল কমান্ড ==========
async def search_on(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["search"]["command"] = True
        save_json('settings.json', settings)
        await u.message.reply_text("✅ /search command enabled")

async def search_off(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["search"]["command"] = False
        save_json('settings.json', settings)
        await u.message.reply_text("✅ /search command disabled")

async def auto_on(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["search"]["auto"] = True
        save_json('settings.json', settings)
        await u.message.reply_text("✅ Auto search enabled")

async def auto_off(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["search"]["auto"] = False
        save_json('settings.json', settings)
        await u.message.reply_text("✅ Auto search disabled")

# ========== মেসেজ ==========
async def msg(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text:
        return
    user = u.message.from_user
    if ignore(user) or u.message.chat_id != GROUP_ID:
        return
    uid = user.id
    txt = u.message.text.strip()
    ud = get_user(uid)
    ud["last_active"] = str(datetime.now())
    save_user(uid, ud)
    
    # ব্যান/মিউট চেক
    if ud.get("b"):
        try:
            await u.message.delete()
        except:
            pass
        return
    if ud.get("m"):
        mu = ud.get("mu")
        if mu and datetime.now() < datetime.fromisoformat(mu):
            try:
                await u.message.delete()
            except:
                pass
            return
        else:
            ud["m"] = False
            ud["mu"] = None
            save_user(uid, ud)
    
    # লিংক ফিল্টার
    if settings["filter"]["enabled"]:
        links = re.findall(r'https?://[^\s]+', txt)
        if links:
            for l in links:
                allowed = any(d in l for d in settings["filter"]["domains"])
                if not allowed:
                    try:
                        await u.message.delete()
                    except:
                        pass
                    ud["w"] += 1
                    save_user(uid, ud)
                    stats["w"] += 1
                    save_json('stats.json', stats)
                    await c.bot.send_message(GROUP_ID, f"⚠️ Warning {ud['w']}/{settings['filter']['max_warnings']}")
                    if ud["w"] >= settings["filter"]["max_warnings"]:
                        ud["m"] = True
                        ud["mu"] = str(datetime.now() + timedelta(minutes=settings["filter"]["mute_duration"]))
                        save_user(uid, ud)
                        await c.bot.send_message(GROUP_ID, f"🔇 Muted {settings['filter']['mute_duration']}min")
                    return
    
    # অটো সার্চ (যদি চালু থাকে)
    if settings["search"]["auto"]:
        anime_keywords = ['naruto', 'one piece', 'demon slayer', 'attack on titan', 'season', 'episode', 'anime']
        if any(k in txt.lower() for k in anime_keywords):
            await perform_search(u.message, txt)

# ========== নিউ মেম্বার ==========
async def new(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not settings["welcome"]["enabled"]:
        return
    for m in u.message.new_chat_members:
        if m.is_bot:
            continue
        get_user(m.id)
        await u.message.reply_text(settings["welcome"]["msg"].replace("{name}", m.first_name))

# ========== অটো পোস্টার ==========
async def poster(c: ContextTypes.DEFAULT_TYPE):
    posts = check_new()
    for p in posts:
        try:
            msg = settings["poster"]["template"].format(title=p["title"], button=settings["poster"]["button"], link=p["url"])
            kb = [[InlineKeyboardButton(settings["poster"]["button"], url=p["url"])]]
            await c.bot.send_message(CHANNEL_ID, msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        except:
            pass

# ========== অ্যাডমিন কমান্ড ==========
async def poster_on(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["poster"]["enabled"] = True
        save_json('settings.json', settings)
        await u.message.reply_text("✅ Poster ON")

async def poster_off(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["poster"]["enabled"] = False
        save_json('settings.json', settings)
        await u.message.reply_text("✅ Poster OFF")

async def poster_int(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not c.args:
        return
    try:
        sec = int(c.args[0])
        if sec >= 10:
            settings["poster"]["interval"] = sec
            save_json('settings.json', settings)
            await u.message.reply_text(f"✅ Interval {sec}s")
    except:
        pass

async def poster_btn(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id) and c.args:
        btn = ' '.join(c.args)
        settings["poster"]["button"] = btn
        save_json('settings.json', settings)
        await u.message.reply_text(f"✅ Button '{btn}'")

async def warn(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not u.message.reply_to_message:
        return
    target = u.message.reply_to_message.from_user
    ud = get_user(target.id)
    ud["w"] += 1
    save_user(target.id, ud)
    stats["w"] += 1
    save_json('stats.json', stats)
    await u.message.reply_text(f"⚠️ Warned")

async def mute(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not u.message.reply_to_message:
        return
    target = u.message.reply_to_message.from_user
    mins = 60
    if c.args:
        try:
            mins = int(c.args[0])
        except:
            pass
    ud = get_user(target.id)
    ud["m"] = True
    ud["mu"] = str(datetime.now() + timedelta(minutes=mins))
    save_user(target.id, ud)
    stats["m"] += 1
    save_json('stats.json', stats)
    await u.message.reply_text(f"🔇 Muted {mins}min")

async def unmute(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not u.message.reply_to_message:
        return
    target = u.message.reply_to_message.from_user
    ud = get_user(target.id)
    ud["m"] = False
    ud["mu"] = None
    save_user(target.id, ud)
    await u.message.reply_text(f"✅ Unmuted")

async def ban(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not u.message.reply_to_message:
        return
    target = u.message.reply_to_message.from_user
    ud = get_user(target.id)
    ud["b"] = True
    save_user(target.id, ud)
    stats["b"] += 1
    save_json('stats.json', stats)
    await u.message.reply_text(f"🚫 Banned")

async def unban(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id) or not u.message.reply_to_message:
        return
    target = u.message.reply_to_message.from_user
    ud = get_user(target.id)
    ud["b"] = False
    save_user(target.id, ud)
    await u.message.reply_text(f"✅ Unbanned")

# ========== মেইন ==========
def main():
    threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=8081, debug=False)).start()
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ইউজার কমান্ড
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_))
    app.add_handler(CommandHandler("search", search_command))
    
    # অ্যাডমিন কমান্ড
    app.add_handler(CommandHandler("panel", panel))
    app.add_handler(CommandHandler("api", api_status))
    app.add_handler(CommandHandler("posteron", poster_on))
    app.add_handler(CommandHandler("posteroff", poster_off))
    app.add_handler(CommandHandler("posterinterval", poster_int))
    app.add_handler(CommandHandler("posterbutton", poster_btn))
    app.add_handler(CommandHandler("searchon", search_on))
    app.add_handler(CommandHandler("searchoff", search_off))
    app.add_handler(CommandHandler("autoon", auto_on))
    app.add_handler(CommandHandler("autooff", auto_off))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    
    # হ্যান্ডলার
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg))
    
    # জব কিউ
    app.job_queue.run_repeating(poster, interval=settings["poster"]["interval"], first=10)
    
    app.run_polling()

if __name__ == "__main__":
    main()
