#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
অ্যানিমেথিক আলট্রা বট v8.0 - সম্পূর্ণ ফিচার সহ, এরর-ফ্রি
"""

import os
import logging
import json
import re
import threading
import asyncio
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from flask import Flask
import requests
import feedparser

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ========== কনফিগারেশন (আপনার তথ্য) ==========
BOT_TOKEN = "8763338417:AAHCzL74xO3YxG8ktSrGar3aUF7OzklS0Ko"  # নতুন টোকেন
ADMIN_ID = 7406197326
GROUP_ID = -1002248871056
CHANNEL_ID = -1002225247609
BLOG_ID = "6445429841925204092"
API_KEY = "AIzaSyBd-2MBVvEpJMH1J8xfhT8uzDbxARaDc6Q"

# Flask app for Render
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "🤖 অ্যানিমেথিক আলট্রা বট v8.0 চলছে!"

# ========== লগিং ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== JSON ফাংশন ==========
def load_json(filename, default_data):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return default_data
    return default_data

def save_json(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        return False

# ========== ডাটাবেস ==========

# সেটিংস
settings_db = load_json('settings.json', {
    "poster": {
        "enabled": True,
        "interval": 30,
        "button_text": "DOWNLOAD 📥",
        "show_link": True,
        "template": "{title}\n\n[ {button} ]\n\n{link}",
        "filter_labels": [],
        "notify_success": True,
        "notify_failure": True,
        "use_cache": True
    },
    "welcome": {
        "enabled": True,
        "message": "👋 Welcome {name} to the group!\n\n🔍 To search anime, just type the name\nExample: Naruto Season 9\n\n📢 New releases in our channel"
    },
    "link_filter": {
        "enabled": True,
        "allowed_domains": ["animethic.in", "www.animethic.in"],
        "max_warnings": 3,
        "mute_duration": 60
    },
    "language": {
        "admin": "bn",
        "user": "en"
    },
    "last_post_id": None,
    "last_check": None
})

# ইউজার ডাটাবেস
users_db = load_json('users.json', {})

# স্ট্যাটস ডাটাবেস
stats_db = load_json('stats.json', {
    "total_requests": 0,
    "total_warnings": 0,
    "total_mutes": 0,
    "total_bans": 0,
    "posts_today": 0,
    "posts_week": 0,
    "anime_requests": {},
    "last_reset": str(datetime.now().date())
})

# ========== ইউজার ফাংশন ==========

def get_user(user_id):
    user_id = str(user_id)
    if user_id not in users_db:
        users_db[user_id] = {
            "warnings": 0,
            "is_muted": False,
            "mute_until": None,
            "is_banned": False,
            "is_admin": (user_id == str(ADMIN_ID)),
            "is_moderator": False,
            "join_date": str(datetime.now()),
            "last_active": str(datetime.now()),
            "total_requests": 0
        }
        save_json('users.json', users_db)
    return users_db[user_id]

def save_user(user_id, data):
    users_db[str(user_id)] = data
    save_json('users.json', users_db)

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def is_moderator(user_id):
    if is_admin(user_id):
        return True
    user = get_user(user_id)
    return user.get("is_moderator", False)

def should_ignore(user):
    """চেক করে এই ইউজারকে ইগনোর করবে কিনা"""
    # বট নিজেই
    if user.is_bot:
        return True
    
    # অ্যাডমিন
    if is_admin(user.id):
        return True
    
    # মডারেটর
    if is_moderator(user.id):
        return True
    
    return False

def add_warning(user_id, reason=""):
    user = get_user(user_id)
    user["warnings"] += 1
    user["last_warning"] = str(datetime.now())
    save_user(user_id, user)
    stats_db["total_warnings"] += 1
    save_json('stats.json', stats_db)
    return user["warnings"]

def clear_warnings(user_id):
    user = get_user(user_id)
    user["warnings"] = 0
    save_user(user_id, user)

def mute_user(user_id, minutes):
    user = get_user(user_id)
    user["is_muted"] = True
    user["mute_until"] = str(datetime.now() + timedelta(minutes=minutes))
    save_user(user_id, user)
    stats_db["total_mutes"] += 1
    save_json('stats.json', stats_db)

def unmute_user(user_id):
    user = get_user(user_id)
    user["is_muted"] = False
    user["mute_until"] = None
    save_user(user_id, user)

def ban_user(user_id, reason=""):
    user = get_user(user_id)
    user["is_banned"] = True
    user["ban_reason"] = reason
    user["ban_date"] = str(datetime.now())
    save_user(user_id, user)
    stats_db["total_bans"] += 1
    save_json('stats.json', stats_db)

def unban_user(user_id):
    user = get_user(user_id)
    user["is_banned"] = False
    save_user(user_id, user)

# ========== API ফাংশন ==========

def get_all_posts_from_api(max_results=10):
    """Blogger API থেকে পোস্ট আনে"""
    if not API_KEY or not BLOG_ID:
        return []
    try:
        url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts"
        params = {
            'key': API_KEY,
            'maxResults': max_results,
            'fetchBodies': 'true',
            'fetchImages': 'false',
            'status': 'live'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            posts = []
            for item in data.get('items', []):
                posts.append({
                    'id': item.get('id', ''),
                    'title': item.get('title', ''),
                    'link': item.get('url', ''),
                    'published': item.get('published', ''),
                    'labels': item.get('labels', [])
                })
            return posts
        else:
            logger.error(f"API error: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"API exception: {e}")
        return []

def search_anime(query, max_results=5):
    """অ্যানিমে সার্চ করে"""
    if not API_KEY or not BLOG_ID:
        return []
    try:
        url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/search"
        params = {
            'key': API_KEY,
            'q': query,
            'maxResults': max_results,
            'fetchBodies': 'false',
            'status': 'live'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get('items', []):
                title = item.get('title', '')
                # ফাজি ম্যাচিং
                if fuzzy_match(query, title) > 0.6:
                    results.append({
                        'title': title,
                        'link': item.get('url', ''),
                        'labels': item.get('labels', [])
                    })
            return results[:max_results]
        else:
            return []
    except:
        return []

def fuzzy_match(query, text):
    """ফাজি ম্যাচিং"""
    return SequenceMatcher(None, query.lower(), text.lower()).ratio()

def check_new_posts():
    """নতুন পোস্ট চেক করে"""
    if not settings_db.get("poster", {}).get("enabled", True):
        return []
    
    posts = get_all_posts_from_api(max_results=5)
    if not posts:
        return []
    
    new_posts = []
    last_id = settings_db.get("last_post_id")
    
    for post in posts:
        if post['id'] != last_id:
            new_posts.append(post)
        else:
            break
    
    if new_posts:
        settings_db["last_post_id"] = new_posts[0]['id']
        settings_db["last_check"] = str(datetime.now())
        save_json('settings.json', settings_db)
        
        # স্ট্যাটস আপডেট
        stats_db["posts_today"] += len(new_posts)
        stats_db["posts_week"] += len(new_posts)
        save_json('stats.json', stats_db)
    
    return new_posts[::-1]  # পুরনো আগে

# ========== ইউটিলিটি ফাংশন ==========

def extract_links(text):
    """লিংক বের করে"""
    url_pattern = r'https?://[^\s]+|www\.[^\s]+'
    return re.findall(url_pattern, text, re.IGNORECASE)

def is_allowed_domain(url):
    """অ্যালাউড ডোমেইন চেক করে"""
    allowed = settings_db.get("link_filter", {}).get("allowed_domains", [])
    for domain in allowed:
        if domain in url:
            return True
    return False

def is_anime_request(text):
    """অ্যানিমে রিকোয়েস্ট চেক করে"""
    if not text:
        return False
    
    text = text.lower().strip()
    
    # গ্রিটিংস ইগনোর
    greetings = ['hi', 'hello', 'hey', 'bye', 'thanks', 'ok']
    if text in greetings:
        return False
    
    # অ্যানিমে কিওয়ার্ড
    anime_keywords = ['naruto', 'one piece', 'demon slayer', 'attack on titan', 
                      'season', 'episode', 'anime', 'dubbed', 'subbed']
    
    for keyword in anime_keywords:
        if keyword in text:
            return True
    
    return False

# ========== টেলিগ্রাম হ্যান্ডলার ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """স্টার্ট কমান্ড"""
    user = update.effective_user
    
    # অ্যাডমিন/মডারেটর ইগনোর
    if should_ignore(user):
        return
    
    text = (
        "🤖 **Anime Search Bot**\n\n"
        "Welcome! I can help you find anime.\n\n"
        "🔍 **How to use:**\n"
        "Just type any anime name in the group\n"
        "Example: `Naruto Season 9`\n\n"
        "📢 **New releases:**\n"
        "Check our channel for latest anime!\n\n"
        "Commands:\n"
        "/help - Show help"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """হেল্প কমান্ড"""
    user = update.effective_user
    
    # অ্যাডমিন/মডারেটর ইগনোর
    if should_ignore(user):
        return
    
    text = (
        "📚 **Help Guide**\n\n"
        "Simply type an anime name in the group\n"
        "I'll search and give you download links\n\n"
        "**Examples:**\n"
        "• `Naruto Season 9`\n"
        "• `One Piece Episode 1000`\n"
        "• `Demon Slayer`\n\n"
        "**Admin commands are hidden**"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যাডমিন প্যানেল"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("⛔ আপনার অনুমতি নেই!")
        return
    
    # প্যানেল মেনু
    keyboard = [
        [
            InlineKeyboardButton("📊 ড্যাশবোর্ড", callback_data="panel_dashboard"),
            InlineKeyboardButton("📢 অটো পোস্টার", callback_data="panel_poster")
        ],
        [
            InlineKeyboardButton("👥 ইউজার", callback_data="panel_users"),
            InlineKeyboardButton("⚙️ সেটিংস", callback_data="panel_settings")
        ],
        [
            InlineKeyboardButton("📊 পরিসংখ্যান", callback_data="panel_stats"),
            InlineKeyboardButton("ℹ️ তথ্য", callback_data="panel_info")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔐 **অ্যাডমিন কন্ট্রোল প্যানেল**\n\n"
        "নিচের অপশন থেকে সিলেক্ট করুন:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """পরিসংখ্যান"""
    user = update.effective_user
    
    if not is_admin(user.id):
        return
    
    text = (
        f"📊 **পরিসংখ্যান**\n\n"
        f"📝 মোট রিকোয়েস্ট: {stats_db.get('total_requests', 0):,}\n"
        f"⚠️ মোট ওয়ার্নিং: {stats_db.get('total_warnings', 0):,}\n"
        f"🔇 মোট মিউট: {stats_db.get('total_mutes', 0):,}\n"
        f"🚫 মোট ব্যান: {stats_db.get('total_bans', 0):,}\n"
        f"👥 মোট ইউজার: {len(users_db):,}\n\n"
        f"📢 **পোস্টার স্ট্যাটস:**\n"
        f"• আজকে: {stats_db.get('posts_today', 0)}টি\n"
        f"• এই সপ্তাহে: {stats_db.get('posts_week', 0)}টি\n"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """মেসেজ হ্যান্ডলার"""
    if not update.message or not update.message.text:
        return
    
    user = update.message.from_user
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    
    # শুধু গ্রুপে কাজ করবে
    if chat_id != GROUP_ID:
        return
    
    # অ্যাডমিন/মডারেটর/বট ইগনোর
    if should_ignore(user):
        return
    
    # ইউজার ডাটা
    user_data = get_user(user.id)
    user_data["last_active"] = str(datetime.now())
    save_user(user.id, user_data)
    
    # ব্যান চেক
    if user_data.get("is_banned", False):
        try:
            await update.message.delete()
        except:
            pass
        return
    
    # মিউট চেক
    if user_data.get("is_muted", False):
        mute_until = user_data.get("mute_until")
        if mute_until:
            mute_time = datetime.fromisoformat(mute_until)
            if datetime.now() < mute_time:
                try:
                    await update.message.delete()
                except:
                    pass
                return
            else:
                unmute_user(user.id)
    
    # লিংক ফিল্টার
    if settings_db.get("link_filter", {}).get("enabled", True):
        links = extract_links(text)
        if links:
            allowed = True
            for link in links:
                if not is_allowed_domain(link):
                    allowed = False
                    break
            
            if not allowed:
                try:
                    await update.message.delete()
                    warnings = add_warning(user.id, "Forbidden link")
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ {user.mention_html()} posted a forbidden link!\nWarning: {warnings}/{settings_db['link_filter']['max_warnings']}",
                        parse_mode='HTML'
                    )
                    
                    if warnings >= settings_db['link_filter']['max_warnings']:
                        mute_user(user.id, settings_db['link_filter']['mute_duration'])
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"🔇 {user.mention_html()} muted for {settings_db['link_filter']['mute_duration']} minutes!",
                            parse_mode='HTML'
                        )
                except:
                    pass
                return
    
    # অ্যানিমে সার্চ
    if is_anime_request(text):
        stats_db["total_requests"] += 1
        user_data["total_requests"] += 1
        save_user(user.id, user_data)
        
        results = search_anime(text)
        
        if results:
            reply = f"🔍 **Found for '{text}':**\n\n"
            for i, res in enumerate(results, 1):
                reply += f"{i}. **{res['title']}**\n"
                reply += f"📥 [Download Here]({res['link']})\n\n"
                
                # স্ট্যাটস আপডেট
                stats_db["anime_requests"][res['title']] = stats_db["anime_requests"].get(res['title'], 0) + 1
            
            await update.message.reply_text(reply, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text(f"🔍 '{text}' not found.")
        
        save_json('stats.json', stats_db)

async def new_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নতুন মেম্বার জয়েন করলে"""
    if not settings_db.get("welcome", {}).get("enabled", True):
        return
    
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        
        # ইউজার ডাটা তৈরি
        get_user(member.id)
        
        welcome_text = settings_db["welcome"]["message"].replace("{name}", member.first_name)
        await update.message.reply_text(welcome_text)

# ========== বাটন হ্যান্ডলার ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বাটন ক্লিক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
        return
    
    data = query.data
    
    if data == "panel_dashboard":
        text = (
            "📊 **ড্যাশবোর্ড**\n\n"
            f"👥 মোট ইউজার: {len(users_db):,}\n"
            f"📝 মোট রিকোয়েস্ট: {stats_db.get('total_requests', 0):,}\n"
            f"⚠️ মোট ওয়ার্নিং: {stats_db.get('total_warnings', 0):,}\n"
            f"🔇 মোট মিউট: {stats_db.get('total_mutes', 0):,}\n"
            f"🚫 মোট ব্যান: {stats_db.get('total_bans', 0):,}\n\n"
            f"📢 **পোস্টার স্ট্যাটাস:** {'চালু' if settings_db['poster']['enabled'] else 'বন্ধ'}\n"
            f"⏱️ চেক ইন্টারভাল: {settings_db['poster']['interval']} সেকেন্ড"
        )
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "panel_poster":
        text = (
            "📢 **অটো পোস্টার সেটিংস**\n\n"
            f"🟢 স্ট্যাটাস: {'চালু' if settings_db['poster']['enabled'] else 'বন্ধ'}\n"
            f"⏱️ ইন্টারভাল: {settings_db['poster']['interval']} সেকেন্ড\n"
            f"🎨 বাটন টেক্সট: {settings_db['poster']['button_text']}\n\n"
            "**কন্ট্রোল:**\n"
            "/poster on - চালু\n"
            "/poster off - বন্ধ\n"
            "/poster interval [সেকেন্ড] - সময় সেট\n"
            "/poster button [টেক্সট] - বাটন পরিবর্তন\n"
            "/poster now - এখনই পোস্ট"
        )
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "panel_users":
        text = (
            "👥 **ইউজার ম্যানেজমেন্ট**\n\n"
            f"📊 মোট ইউজার: {len(users_db):,}\n"
            f"⚠️ ওয়ার্নিং দেওয়া: {stats_db.get('total_warnings', 0):,}\n"
            f"🔇 মিউট করা: {stats_db.get('total_mutes', 0):,}\n"
            f"🚫 ব্যান করা: {stats_db.get('total_bans', 0):,}\n\n"
            "**কমান্ড:**\n"
            "/warn (রিপ্লাই) - ওয়ার্ন দিন\n"
            "/mute [মিনিট] (রিপ্লাই) - মিউট করুন\n"
            "/unmute (রিপ্লাই) - মিউট উঠান\n"
            "/ban (রিপ্লাই) - ব্যান করুন\n"
            "/unban (রিপ্লাই) - আনব্যান করুন"
        )
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "panel_settings":
        text = (
            "⚙️ **সেটিংস**\n\n"
            f"👋 ওয়েলকাম: {'চালু' if settings_db['welcome']['enabled'] else 'বন্ধ'}\n"
            f"🔗 লিংক ফিল্টার: {'চালু' if settings_db['link_filter']['enabled'] else 'বন্ধ'}\n"
            f"📝 ম্যাক্স ওয়ার্নিং: {settings_db['link_filter']['max_warnings']}\n"
            f"⏱️ মিউট ডিউরেশন: {settings_db['link_filter']['mute_duration']} মিনিট\n\n"
            "**অ্যালাউড ডোমেইন:**\n"
            + "\n".join([f"• {d}" for d in settings_db['link_filter']['allowed_domains']])
        )
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "panel_stats":
        text = (
            "📊 **পরিসংখ্যান**\n\n"
            f"📝 মোট রিকোয়েস্ট: {stats_db.get('total_requests', 0):,}\n"
            f"⚠️ মোট ওয়ার্নিং: {stats_db.get('total_warnings', 0):,}\n"
            f"🔇 মোট মিউট: {stats_db.get('total_mutes', 0):,}\n"
            f"🚫 মোট ব্যান: {stats_db.get('total_bans', 0):,}\n"
            f"📢 আজকের পোস্ট: {stats_db.get('posts_today', 0)}\n"
            f"📢 এই সপ্তাহে: {stats_db.get('posts_week', 0)}\n\n"
            "**টপ অ্যানিমে:**\n"
        )
        
        top_anime = sorted(stats_db.get('anime_requests', {}).items(), key=lambda x: x[1], reverse=True)[:5]
        for anime, count in top_anime:
            text += f"• {anime[:30]}... - {count} বার\n"
        
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "panel_info":
        text = (
            "ℹ️ **তথ্য**\n\n"
            "🤖 বট ভার্সন: v8.0\n"
            "📅 তৈরি: মার্চ ২০২৬\n"
            "👑 অ্যাডমিন: @ashikmee12\n\n"
            "**ফিচার:**\n"
            "• অ্যানিমে সার্চ (API v3)\n"
            "• অটো পোস্টার (৩০ সেকেন্ড)\n"
            "• লিংক প্রোটেকশন\n"
            "• ওয়েলকাম মেসেজ\n"
            "• অ্যাডমিন প্যানেল"
        )
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "panel_back":
        keyboard = [
            [
                InlineKeyboardButton("📊 ড্যাশবোর্ড", callback_data="panel_dashboard"),
                InlineKeyboardButton("📢 অটো পোস্টার", callback_data="panel_poster")
            ],
            [
                InlineKeyboardButton("👥 ইউজার", callback_data="panel_users"),
                InlineKeyboardButton("⚙️ সেটিংস", callback_data="panel_settings")
            ],
            [
                InlineKeyboardButton("📊 পরিসংখ্যান", callback_data="panel_stats"),
                InlineKeyboardButton("ℹ️ তথ্য", callback_data="panel_info")
            ]
        ]
        await query.edit_message_text(
            "🔐 **অ্যাডমিন কন্ট্রোল প্যানেল**\n\n"
            "নিচের অপশন থেকে সিলেক্ট করুন:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ========== অ্যাডমিন কমান্ড ==========

async def poster_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অটো পোস্টার চালু"""
    if not is_admin(update.effective_user.id):
        return
    settings_db["poster"]["enabled"] = True
    save_json('settings.json', settings_db)
    await update.message.reply_text("✅ অটো পোস্টার চালু করা হয়েছে!")

async def poster_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অটো পোস্টার বন্ধ"""
    if not is_admin(update.effective_user.id):
        return
    settings_db["poster"]["enabled"] = False
    save_json('settings.json', settings_db)
    await update.message.reply_text("✅ অটো পোস্টার বন্ধ করা হয়েছে!")

async def poster_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অটো পোস্টার ইন্টারভাল সেট"""
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("📝 ব্যবহার: /poster interval [সেকেন্ড]")
        return
    try:
        interval = int(context.args[0])
        if interval < 10:
            interval = 10
        settings_db["poster"]["interval"] = interval
        save_json('settings.json', settings_db)
        await update.message.reply_text(f"✅ ইন্টারভাল {interval} সেকেন্ড সেট করা হয়েছে!")
    except:
        await update.message.reply_text("❌ ভুল সংখ্যা!")

async def poster_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বাটন টেক্সট সেট"""
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("📝 ব্যবহার: /poster button [টেক্সট]")
        return
    button_text = ' '.join(context.args)
    settings_db["poster"]["button_text"] = button_text
    save_json('settings.json', settings_db)
    await update.message.reply_text(f"✅ বাটন টেক্সট '{button_text}' সেট করা হয়েছে!")

async def poster_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """এখনই পোস্ট করুন"""
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text("⏳ নতুন পোস্ট চেক করা হচ্ছে...")
    await auto_poster(context)

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ওয়ার্ন কমান্ড"""
    if not is_moderator(update.effective_user.id):
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /warn ব্যবহার করুন")
        return
    
    target = update.message.reply_to_message.from_user
    reason = ' '.join(context.args) if context.args else "No reason"
    
    warnings = add_warning(target.id, reason)
    await update.message.reply_text(
        f"⚠️ {target.mention_html()} কে ওয়ার্ন দেওয়া হয়েছে!\n"
        f"কারণ: {reason}\n"
        f"মোট ওয়ার্নিং: {warnings}",
        parse_mode='HTML'
    )

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """মিউট কমান্ড"""
    if not is_moderator(update.effective_user.id):
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /mute ব্যবহার করুন")
        return
    
    target = update.message.reply_to_message.from_user
    duration = 60
    
    if context.args:
        try:
            duration = int(context.args[0])
        except:
            pass
    
    mute_user(target.id, duration)
    await update.message.reply_text(
        f"🔇 {target.mention_html()} {duration} মিনিটের জন্য মিউট করা হয়েছে!",
        parse_mode='HTML'
    )

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """আনমিউট কমান্ড"""
    if not is_moderator(update.effective_user.id):
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /unmute ব্যবহার করুন")
        return
    
    target = update.message.reply_to_message.from_user
    unmute_user(target.id)
    await update.message.reply_text(
        f"✅ {target.mention_html()} এর মিউট উঠানো হয়েছে!",
        parse_mode='HTML'
    )

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ব্যান কমান্ড"""
    if not is_admin(update.effective_user.id):
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /ban ব্যবহার করুন")
        return
    
    target = update.message.reply_to_message.from_user
    reason = ' '.join(context.args) if context.args else "No reason"
    
    ban_user(target.id, reason)
    await update.message.reply_text(
        f"🚫 {target.mention_html()} ব্যান করা হয়েছে!\nকারণ: {reason}",
        parse_mode='HTML'
    )

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """আনব্যান কমান্ড"""
    if not is_admin(update.effective_user.id):
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ কোন মেসেজের রিপ্লাই হিসেবে /unban ব্যবহার করুন")
        return
    
    target = update.message.reply_to_message.from_user
    unban_user(target.id)
    await update.message.reply_text(
        f"✅ {target.mention_html()} এর ব্যান উঠানো হয়েছে!",
        parse_mode='HTML'
    )

# ========== অটো পোস্টার ==========

async def auto_poster(context: ContextTypes.DEFAULT_TYPE):
    """অটো পোস্টার ফাংশন"""
    if not settings_db.get("poster", {}).get("enabled", True):
        return
    
    new_posts = check_new_posts()
    
    for post in new_posts:
        try:
            # টেমপ্লেট তৈরি
            template = settings_db["poster"]["template"]
            button_text = settings_db["poster"]["button_text"]
            
            message = template.format(
                title=post['title'],
                button=button_text,
                link=post['link']
            )
            
            # ইনলাইন বাটন
            keyboard = [[InlineKeyboardButton(button_text, url=post['link'])]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # চ্যানেলে পাঠান
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            logger.info(f"Posted to channel: {post['title']}")
            
            # নোটিফিকেশন
            if settings_db["poster"].get("notify_success", True):
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"✅ পোস্ট পাঠানো হয়েছে:\n{post['title']}"
                )
            
            await asyncio.sleep(2)  # ২ সেকেন্ড বিরতি
            
        except Exception as e:
            logger.error(f"Auto poster error: {e}")
            if settings_db["poster"].get("notify_failure", True):
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"❌ পোস্ট ব্যর্থ: {str(e)[:100]}"
                )

# ========== ডেইলি রিসেট ==========

async def daily_reset(context: ContextTypes.DEFAULT_TYPE):
    """প্রতিদিন স্ট্যাটস রিসেট"""
    stats_db["posts_today"] = 0
    stats_db["last_reset"] = str(datetime.now().date())
    save_json('stats.json', stats_db)

# ========== মেইন ফাংশন ==========

def main():
    """মেইন ফাংশন"""
    
    # Flask চালু
    threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=8081, debug=False)).start()
    
    # বট চালু
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ইউজার কমান্ড
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # অ্যাডমিন কমান্ড
    app.add_handler(CommandHandler("panel", panel_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("poster", poster_on))
    app.add_handler(CommandHandler("posteron", poster_on))
    app.add_handler(CommandHandler("posteroff", poster_off))
    app.add_handler(CommandHandler("posterinterval", poster_interval))
    app.add_handler(CommandHandler("posterbutton", poster_button))
    app.add_handler(CommandHandler("posternow", poster_now))
    app.add_handler(CommandHandler("warn", warn_command))
    app.add_handler(CommandHandler("mute", mute_command))
    app.add_handler(CommandHandler("unmute", unmute_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    
    # মেসেজ হ্যান্ডলার
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # বাটন হ্যান্ডলার
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # জব কিউ
    app.job_queue.run_repeating(auto_poster, interval=settings_db["poster"]["interval"], first=10)
    app.job_queue.run_daily(daily_reset, time=datetime.time(hour=0, minute=0, second=0))
    
    logger.info("🤖 বট চালু হয়েছে!")
    app.run_polling()

if __name__ == "__main__":
    main()
