#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
অ্যানিমেথিক বট v5.0 - সম্পূর্ণ ফাইনাল
✅ আপনার সব কথা মতো তৈরি
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
BLOG_ID = "6445429841925204092"
API_KEY = "AIzaSyBd-2MBVvEpJMH1J8xfhT8uzDbxARaDc6Q"

app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Anime Bot Running"

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
    "welcome": {
        "enabled": True,
        "message": "👋 Welcome {name} to the group!\n\n📌 **Rules:**\n• Only anime related discussions\n• No external links\n• Use /search [name] or just type anime name\n\n🔍 **How to search:**\n• Type anime name directly (e.g., Naruto Season 9)\n• Or use /search command (e.g., /search One Piece)"
    },
    "filter": {
        "enabled": True,
        "domains": ["animethic.in", "www.animethic.in"],
        "max_warnings": 3,
        "mute_duration": 60
    },
    "search": {
        "auto": True,
        "command": True
    },
    "bot_name": "Anime Search Bot"
})

users = load_json('users.json', {})
stats = load_json('stats.json', {"req": 0, "w": 0, "m": 0, "b": 0, "anime": {}})

# ========== ইউজার ফাংশন ==========
def get_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "warnings": 0,
            "is_muted": False,
            "mute_until": None,
            "is_banned": False,
            "is_moderator": False,
            "join_date": str(datetime.now()),
            "last_active": str(datetime.now()),
            "total_requests": 0
        }
        save_json('users.json', users)
    return users[uid]

def save_user(uid, d):
    users[str(uid)] = d
    save_json('users.json', users)

def is_admin(uid):
    return str(uid) == str(ADMIN_ID)

def ignore(u):
    """আপনার কথা: admin, bot, moderator der reply dibe na"""
    if u.is_bot:
        return True
    if is_admin(u.id):
        return True
    if get_user(u.id).get("is_moderator", False):
        return True
    return False

# ========== API ফাংশন ==========
def search_anime(query):
    if not API_KEY or not BLOG_ID:
        return []
    try:
        url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/search"
        params = {
            'key': API_KEY,
            'q': query,
            'maxResults': 3,
            'fetchBodies': 'false',
            'status': 'live'
        }
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            items = r.json().get('items', [])
            results = []
            for item in items:
                title = item.get('title', '')
                if SequenceMatcher(None, query.lower(), title.lower()).ratio() > 0.5:
                    results.append({
                        'title': title,
                        'link': item.get('url', '')
                    })
            return results[:3]
    except:
        pass
    return []

# ========== কমন সার্চ ফাংশন ==========
async def do_search(msg, query):
    stats["req"] += 1
    save_json('stats.json', stats)
    
    results = search_anime(query)
    
    if results:
        reply = f"🔍 **Found for '{query}':**\n\n"
        for i, res in enumerate(results, 1):
            reply += f"{i}. **{res['title']}**\n📥 [Download Here]({res['link']})\n\n"
            stats["anime"][res['title']] = stats["anime"].get(res['title'], 0) + 1
        await msg.reply_text(reply, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        # আপনার দেওয়া নট ফাউন্ড মেসেজ
        not_found = (
            f"🔍 '{query}' not found.\n\n"
            f"Possible reasons:\n"
            f"• The bot couldn't find it in the website database\n"
            f"• The anime might not be added to the website yet\n"
            f"• The anime may not have been released\n\n"
            f"📞 Contact: @animethic_admin_bot"
        )
        await msg.reply_text(not_found)
    
    save_json('stats.json', stats)

# ========== ইউজার কমান্ড (ইংরেজি) ==========
async def start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if ignore(u.effective_user):
        return
    user = u.effective_user
    text = (
        f"👋 **Welcome {user.first_name}!**\n\n"
        f"🔍 **I can help you find anime.**\n\n"
        f"**How to search:**\n"
        f"• Type anime name directly (e.g., `Naruto Season 9`)\n"
        f"• Use /search command (e.g., `/search One Piece`)\n\n"
        f"📌 **Commands:**\n"
        f"/help - Show help"
    )
    await u.message.reply_text(text, parse_mode='Markdown')

async def help_(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if ignore(u.effective_user):
        return
    text = (
        f"📚 **Help Guide**\n\n"
        f"**How to search:**\n"
        f"1️⃣ **Direct search:** Just type anime name\n"
        f"   Example: `Naruto Season 9`\n\n"
        f"2️⃣ **Command search:** /search [name]\n"
        f"   Example: `/search One Piece`\n\n"
        f"**Rules:**\n"
        f"• Only anime related discussions\n"
        f"• No external links\n"
        f"• Admins have special commands"
    )
    await u.message.reply_text(text, parse_mode='Markdown')

async def search_command(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if ignore(u.effective_user):
        return
    if not settings["search"]["command"]:
        await u.message.reply_text("❌ Search command is currently disabled.")
        return
    if not c.args:
        await u.message.reply_text("Usage: /search [anime name]\nExample: /search Naruto Season 9")
        return
    query = ' '.join(c.args)
    await do_search(u.message, query)

# ========== অ্যাডমিন কমান্ড (বাংলা) ==========
async def panel(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="dash"),
         InlineKeyboardButton("👥 Users", callback_data="users")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="set"),
         InlineKeyboardButton("🔌 API Status", callback_data="api")],
        [InlineKeyboardButton("🔍 Search Settings", callback_data="search"),
         InlineKeyboardButton("👑 Moderators", callback_data="mod")]
    ]
    await u.message.reply_text("🔐 **অ্যাডমিন প্যানেল**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def api_status(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    if not API_KEY or not BLOG_ID:
        await u.message.reply_text("❌ API কনফিগার করা হয়নি")
        return
    try:
        r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts",
                        params={"key": API_KEY, "maxResults": 1}, timeout=5)
        if r.status_code == 200:
            await u.message.reply_text("✅ API সংযোগ সক্রিয়")
        else:
            await u.message.reply_text(f"❌ API Error: {r.status_code}")
    except Exception as e:
        await u.message.reply_text(f"❌ API Error: {str(e)}")

# ========== মডারেটর কমান্ড ==========
async def addmod(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    if not u.message.reply_to_message:
        await u.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /addmod ব্যবহার করুন")
        return
    target = u.message.reply_to_message.from_user
    user = get_user(target.id)
    user["is_moderator"] = True
    save_user(target.id, user)
    await u.message.reply_text(f"✅ {target.first_name} কে মডারেটর করা হয়েছে")

async def delmod(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    if not u.message.reply_to_message:
        await u.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /delmod ব্যবহার করুন")
        return
    target = u.message.reply_to_message.from_user
    user = get_user(target.id)
    user["is_moderator"] = False
    save_user(target.id, user)
    await u.message.reply_text(f"✅ {target.first_name} কে মডারেটর থেকে সরানো হয়েছে")

# ========== বাটন হ্যান্ডলার ==========
async def button_handler(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q = u.callback_query
    await q.answer()
    uid = q.from_user.id
    
    if not is_admin(uid):
        await q.edit_message_text("⛔ আপনার অনুমতি নেই!")
        return
    
    data = q.data
    
    if data == "dash":
        active = sum(1 for u in users.values() if u.get('last_active', '').startswith(str(datetime.now().date())))
        text = (
            f"📊 **Dashboard**\n\n"
            f"👥 মোট ইউজার: {len(users)}\n"
            f"🟢 আজকে একটিভ: {active}\n"
            f"📝 মোট রিকোয়েস্ট: {stats['req']}\n"
            f"⚠️ মোট ওয়ার্নিং: {stats['w']}\n"
            f"🔇 মোট মিউট: {stats['m']}\n"
            f"🚫 মোট ব্যান: {stats['b']}"
        )
        await q.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ পিছনে", callback_data="back")]]))
    
    elif data == "users":
        banned = sum(1 for u in users.values() if u.get('is_banned'))
        muted = sum(1 for u in users.values() if u.get('is_muted'))
        text = (
            f"👥 **User Management**\n\n"
            f"📊 মোট: {len(users)}\n"
            f"🚫 ব্যান করা: {banned}\n"
            f"🔇 মিউট করা: {muted}\n\n"
            f"**কমান্ড:**\n"
            f"/warn (রিপ্লাই) - ওয়ার্ন\n"
            f"/mute [মিনিট] (রিপ্লাই) - মিউট\n"
            f"/unmute (রিপ্লাই) - আনমিউট\n"
            f"/ban (রিপ্লাই) - ব্যান\n"
            f"/unban (রিপ্লাই) - আনব্যান"
        )
        await q.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ পিছনে", callback_data="back")]]))
    
    elif data == "set":
        text = (
            f"⚙️ **Settings**\n\n"
            f"👋 ওয়েলকাম: {'চালু' if settings['welcome']['enabled'] else 'বন্ধ'}\n"
            f"🔗 লিংক ফিল্টার: {'চালু' if settings['filter']['enabled'] else 'বন্ধ'}\n"
            f"⚠️ ম্যাক্স ওয়ার্নিং: {settings['filter']['max_warnings']}\n"
            f"🔇 মিউট ডিউরেশন: {settings['filter']['mute_duration']} মিনিট\n\n"
            f"**অ্যালাউড ডোমেইন:**\n" + "\n".join([f"• {d}" for d in settings['filter']['domains']])
        )
        await q.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ পিছনে", callback_data="back")]]))
    
    elif data == "api":
        if not API_KEY or not BLOG_ID:
            text = "❌ API কনফিগার করা হয়নি"
        else:
            try:
                r = requests.get(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts",
                                params={"key": API_KEY, "maxResults": 1}, timeout=5)
                text = "✅ API সংযোগ সক্রিয়" if r.status_code == 200 else f"❌ API Error: {r.status_code}"
            except Exception as e:
                text = f"❌ API Error: {str(e)}"
        await q.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ পিছনে", callback_data="back")]]))
    
    elif data == "search":
        text = (
            f"🔍 **Search Settings**\n\n"
            f"📝 অটো সার্চ: {'চালু' if settings['search']['auto'] else 'বন্ধ'}\n"
            f"🔍 /search কমান্ড: {'চালু' if settings['search']['command'] else 'বন্ধ'}\n\n"
            f"**কমান্ড:**\n"
            f"/autoon - অটো সার্চ চালু\n"
            f"/autooff - অটো সার্চ বন্ধ\n"
            f"/searchon - /search চালু\n"
            f"/searchoff - /search বন্ধ"
        )
        await q.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ পিছনে", callback_data="back")]]))
    
    elif data == "mod":
        mods = [(uid, u) for uid, u in users.items() if u.get('is_moderator')]
        text = f"👑 **Moderators**\n\nমোট মডারেটর: {len(mods)}\n\n"
        if mods:
            for uid, u in mods[:5]:
                text += f"• User {uid[:8]}...\n"
        else:
            text += "কোন মডারেটর নেই\n\n"
        text += "**কমান্ড:**\n/addmod (রিপ্লাই) - যোগ\n/delmod (রিপ্লাই) - সরান"
        await q.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ পিছনে", callback_data="back")]]))
    
    elif data == "back":
        keyboard = [
            [InlineKeyboardButton("📊 Dashboard", callback_data="dash"),
             InlineKeyboardButton("👥 Users", callback_data="users")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="set"),
             InlineKeyboardButton("🔌 API Status", callback_data="api")],
            [InlineKeyboardButton("🔍 Search Settings", callback_data="search"),
             InlineKeyboardButton("👑 Moderators", callback_data="mod")]
        ]
        await q.edit_message_text("🔐 **অ্যাডমিন প্যানেল**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ========== সার্চ কন্ট্রোল ==========
async def auto_on(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["search"]["auto"] = True
        save_json('settings.json', settings)
        await u.message.reply_text("✅ অটো সার্চ চালু করা হয়েছে")

async def auto_off(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["search"]["auto"] = False
        save_json('settings.json', settings)
        await u.message.reply_text("✅ অটো সার্চ বন্ধ করা হয়েছে")

async def search_on(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["search"]["command"] = True
        save_json('settings.json', settings)
        await u.message.reply_text("✅ /search কমান্ড চালু করা হয়েছে")

async def search_off(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if is_admin(u.effective_user.id):
        settings["search"]["command"] = False
        save_json('settings.json', settings)
        await u.message.reply_text("✅ /search কমান্ড বন্ধ করা হয়েছে")

# ========== মডারেশন কমান্ড ==========
async def warn(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    if not u.message.reply_to_message:
        await u.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /warn ব্যবহার করুন")
        return
    target = u.message.reply_to_message.from_user
    user = get_user(target.id)
    user["warnings"] += 1
    save_user(target.id, user)
    stats["w"] += 1
    save_json('stats.json', stats)
    await u.message.reply_text(f"⚠️ {target.first_name} কে ওয়ার্ন দেওয়া হয়েছে (মোট: {user['warnings']})")

async def mute(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    if not u.message.reply_to_message:
        await u.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /mute ব্যবহার করুন")
        return
    target = u.message.reply_to_message.from_user
    minutes = 60
    if c.args:
        try:
            minutes = int(c.args[0])
        except:
            pass
    user = get_user(target.id)
    user["is_muted"] = True
    user["mute_until"] = str(datetime.now() + timedelta(minutes=minutes))
    save_user(target.id, user)
    stats["m"] += 1
    save_json('stats.json', stats)
    await u.message.reply_text(f"🔇 {target.first_name} {minutes} মিনিটের জন্য মিউট করা হয়েছে")

async def unmute(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    if not u.message.reply_to_message:
        await u.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /unmute ব্যবহার করুন")
        return
    target = u.message.reply_to_message.from_user
    user = get_user(target.id)
    user["is_muted"] = False
    user["mute_until"] = None
    save_user(target.id, user)
    await u.message.reply_text(f"✅ {target.first_name} এর মিউট উঠানো হয়েছে")

async def ban(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    if not u.message.reply_to_message:
        await u.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /ban ব্যবহার করুন")
        return
    target = u.message.reply_to_message.from_user
    user = get_user(target.id)
    user["is_banned"] = True
    save_user(target.id, user)
    stats["b"] += 1
    save_json('stats.json', stats)
    await u.message.reply_text(f"🚫 {target.first_name} ব্যান করা হয়েছে")

async def unban(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not is_admin(u.effective_user.id):
        return
    if not u.message.reply_to_message:
        await u.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /unban ব্যবহার করুন")
        return
    target = u.message.reply_to_message.from_user
    user = get_user(target.id)
    user["is_banned"] = False
    save_user(target.id, user)
    await u.message.reply_text(f"✅ {target.first_name} এর ব্যান উঠানো হয়েছে")

# ========== মেসেজ হ্যান্ডলার ==========
async def handle_message(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not u.message or not u.message.text:
        return
    user = u.message.from_user
    if ignore(user) or u.message.chat_id != GROUP_ID:
        return
    
    uid = user.id
    text = u.message.text.strip()
    user_data = get_user(uid)
    user_data["last_active"] = str(datetime.now())
    save_user(uid, user_data)
    
    # ব্যান চেক
    if user_data.get("is_banned"):
        try:
            await u.message.delete()
        except:
            pass
        return
    
    # মিউট চেক
    if user_data.get("is_muted"):
        mute_until = user_data.get("mute_until")
        if mute_until:
            try:
                if datetime.now() < datetime.fromisoformat(mute_until):
                    try:
                        await u.message.delete()
                    except:
                        pass
                    return
                else:
                    user_data["is_muted"] = False
                    user_data["mute_until"] = None
                    save_user(uid, user_data)
            except:
                pass
    
    # লিংক ফিল্টার
    if settings["filter"]["enabled"]:
        links = re.findall(r'https?://[^\s]+', text)
        if links:
            for link in links:
                allowed = False
                for domain in settings["filter"]["domains"]:
                    if domain in link:
                        allowed = True
                        break
                if not allowed:
                    try:
                        await u.message.delete()
                    except:
                        pass
                    user_data["warnings"] += 1
                    save_user(uid, user_data)
                    stats["w"] += 1
                    save_json('stats.json', stats)
                    await c.bot.send_message(
                        GROUP_ID,
                        f"⚠️ {user.mention_html()} Warning {user_data['warnings']}/{settings['filter']['max_warnings']}",
                        parse_mode='HTML'
                    )
                    if user_data["warnings"] >= settings["filter"]["max_warnings"]:
                        user_data["is_muted"] = True
                        user_data["mute_until"] = str(datetime.now() + timedelta(minutes=settings["filter"]["mute_duration"]))
                        save_user(uid, user_data)
                        await c.bot.send_message(
                            GROUP_ID,
                            f"🔇 {user.mention_html()} muted for {settings['filter']['mute_duration']} minutes",
                            parse_mode='HTML'
                        )
                    return
    
    # অটো সার্চ
    if settings["search"]["auto"]:
        anime_keywords = ['naruto', 'one piece', 'demon slayer', 'attack on titan', 'season', 'episode', 'anime']
        if any(k in text.lower() for k in anime_keywords):
            user_data["total_requests"] += 1
            save_user(uid, user_data)
            await do_search(u.message, text)

# ========== নিউ মেম্বার হ্যান্ডলার ==========
async def new_member(u: Update, c: ContextTypes.DEFAULT_TYPE):
    if not settings["welcome"]["enabled"]:
        return
    for member in u.message.new_chat_members:
        if member.is_bot:
            continue
        get_user(member.id)
        welcome_text = settings["welcome"]["message"].replace("{name}", member.first_name)
        await u.message.reply_text(welcome_text, parse_mode='Markdown')

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
    app.add_handler(CommandHandler("autoon", auto_on))
    app.add_handler(CommandHandler("autooff", auto_off))
    app.add_handler(CommandHandler("searchon", search_on))
    app.add_handler(CommandHandler("searchoff", search_off))
    app.add_handler(CommandHandler("addmod", addmod))
    app.add_handler(CommandHandler("delmod", delmod))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    
    # হ্যান্ডলার
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
