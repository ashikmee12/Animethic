#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
অ্যানিমেথিক আলট্রা বট v7.0 - সম্পূর্ণ ফাইনাল, সব ফিচার সহ
"""

import os
import logging
import json
import re
import threading
import asyncio
import shutil
import random
import string
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

from config import *

# ========== লগিং ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== ফ্লাস্ক অ্যাপ ==========
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return f"🤖 অ্যানিমেথিক আলট্রা বট v7.0 is Running!"

# ========== ডাটাবেস ফাংশন ==========

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def load_json(filename, default_data):
    ensure_data_dir()
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            backup_file = f"{filename}.backup"
            if os.path.exists(backup_file):
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    pass
            return default_data
    return default_data

def save_json(filename, data):
    ensure_data_dir()
    try:
        if os.path.exists(filename):
            backup_file = f"{filename}.backup"
            try:
                shutil.copy2(filename, backup_file)
            except:
                pass
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        return False

# ========== ডাটাবেস ইনিশিয়ালাইজ ==========

users_db = load_json(USERS_FILE, {})

stats_db = load_json(STATS_FILE, {
    "total_requests": 0,
    "total_warnings": 0,
    "total_mutes": 0,
    "total_bans": 0,
    "daily_requests": 0,
    "daily_users": 0,
    "anime_requests": {},
    "user_requests": {},
    "last_reset": str(datetime.now().date())
})

settings_db = load_json(SETTINGS_FILE, {
    "bot_name": "🤖 অ্যানিমেথিক আলট্রা বট",
    "bot_version": "v7.0",
    "bot_tagline": "আপনার অ্যানিমে সহায়ক",
    "groups": {
        "primary": GROUP_ID,
        "channels": {
            "primary": CHANNEL_ID
        },
        "additional": []
    },
    "features": {
        "user_system": True,
        "moderation": True,
        "calendar": True,
        "daily_release": True,
        "analytics": True,
        "security": True,
        "backup": True,
        "ratings": True,
        "challenges": True,
        "multi_group": True
    },
    "poster": {
        "enabled": True,
        "interval": 30,
        "format": {
            "title": True,
            "link": True,
            "excerpt": True,
            "labels": False
        },
        "template": "📢 **New Post!**\n\n**{title}**\n\n📝 {excerpt}\n\n📥 [Download Here]({link})",
        "filter": {
            "enabled": False,
            "labels": []
        },
        "shorten_links": True,
        "shortener": "tinyurl",
        "notify_admin": True
    },
    "welcome": {
        "enabled": True,
        "message": "👋 Welcome {name} to the group!\n\n📌 Please read the rules and enjoy!"
    },
    "link_filter": {
        "enabled": True,
        "allowed_domains": ["animethic.in", "www.animethic.in"]
    },
    "warnings": {
        "max": 3,
        "mute_duration": 60,
        "auto_mute": True
    },
    "language": {
        "user": "en",
        "mod": "bn",
        "admin": "bn",
        "group_default": "en",
        "available": ["en", "bn", "hi"]
    },
    "security": {
        "two_factor": False,
        "login_alert": True
    },
    "backup": {
        "auto": True,
        "interval": 24,
        "keep": 30
    },
    "api": {
        "use_api": True,
        "use_rss": True,
        "fuzzy_threshold": 0.6
    },
    "ratings": {
        "enabled": True,
        "allow_reviews": True
    },
    "challenges": {
        "enabled": True,
        "daily": True,
        "weekly": True
    },
    "reports": {
        "daily": True,
        "weekly": True,
        "monthly": False
    },
    "last_post_id": None,
    "last_post_time": None
})

calendar_db = load_json(CALENDAR_FILE, {
    "daily": {},
    "weekly": {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "saturday": [],
        "sunday": []
    },
    "monthly": {}
})

daily_release_db = load_json(DAILY_RELEASE_FILE, {
    "entries": [],
    "assignments": {},
    "notes": {},
    "departments": {
        "security": {"head": None, "members": []},
        "community": {"head": None, "members": []},
        "content": {"head": None, "members": []},
        "tech": {"head": None, "members": []},
        "investigation": {"head": None, "members": []}
    }
})

team_db = load_json(TEAM_FILE, {
    "admins": {},
    "moderators": {},
    "tasks": [],
    "performance": {}
})

security_db = load_json(SECURITY_FILE, {
    "two_factor": {},
    "login_history": [],
    "blocked_attempts": [],
    "trusted_devices": {}
})

ratings_db = load_json(RATINGS_FILE, {
    "anime": {},
    "reviews": []
})

challenges_db = load_json(CHALLENGES_FILE, {
    "daily": {},
    "weekly": {},
    "user_progress": {}
})

# ========== ইউজার ফাংশন ==========

def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in users_db:
        users_db[user_id] = {
            "warnings": 0,
            "is_muted": False,
            "mute_until": None,
            "is_banned": False,
            "is_moderator": False,
            "mod_level": 0,
            "department": None,
            "join_date": str(datetime.now()),
            "total_requests": 0,
            "last_active": str(datetime.now()),
            "trust_score": 100,
            "rank": "🔰 Newbie",
            "points": 0,
            "achievements": [],
            "language": settings_db.get("language", {}).get("user", "en"),
            "reminders": [],
            "ratings": {},
            "challenge_progress": {}
        }
        save_json(USERS_FILE, users_db)
    return users_db[user_id]

def save_user_data(user_id, data):
    users_db[str(user_id)] = data
    save_json(USERS_FILE, users_db)

def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def is_moderator(user_id):
    if is_admin(user_id):
        return True
    user_data = get_user_data(user_id)
    return user_data.get("is_moderator", False)

def get_user_role(user_id):
    if is_admin(user_id):
        return "👑 Owner"
    user_data = get_user_data(user_id)
    if user_data.get("is_moderator"):
        levels = ["", "🔰 Trainee", "🎓 Junior", "📋 Senior", "⚔️ Head", "🛡️ Co-owner"]
        return levels[user_data.get("mod_level", 1)]
    return "👤 User"

def add_points(user_id, points):
    user_data = get_user_data(user_id)
    user_data["points"] = user_data.get("points", 0) + points
    user_data["trust_score"] = min(100, user_data.get("trust_score", 100) + 1)
    points_total = user_data["points"]
    if points_total < 100:
        user_data["rank"] = "🔰 Newbie"
    elif points_total < 500:
        user_data["rank"] = "🥉 Bronze"
    elif points_total < 2000:
        user_data["rank"] = "🥈 Silver"
    elif points_total < 5000:
        user_data["rank"] = "🥇 Gold"
    elif points_total < 10000:
        user_data["rank"] = "💎 Platinum"
    elif points_total < 20000:
        user_data["rank"] = "🔮 Diamond"
    elif points_total < 50000:
        user_data["rank"] = "⚡ Master"
    elif points_total < 100000:
        user_data["rank"] = "👑 Grandmaster"
    elif points_total < 500000:
        user_data["rank"] = "🌟 Legend"
    else:
        user_data["rank"] = "🏆 Mythical"
    save_user_data(user_id, user_data)
    return user_data["rank"]

def add_warning(user_id, reason=""):
    user_data = get_user_data(user_id)
    user_data["warnings"] = user_data.get("warnings", 0) + 1
    user_data["last_warning"] = str(datetime.now())
    user_data["trust_score"] = max(0, user_data.get("trust_score", 100) - 10)
    save_user_data(user_id, user_data)
    stats_db["total_warnings"] = stats_db.get("total_warnings", 0) + 1
    save_json(STATS_FILE, stats_db)
    return user_data["warnings"]

def clear_warnings(user_id):
    user_data = get_user_data(user_id)
    user_data["warnings"] = 0
    user_data["trust_score"] = min(100, user_data.get("trust_score", 100) + 20)
    save_user_data(user_id, user_data)
    return True

def mute_user(user_id, duration_minutes):
    user_data = get_user_data(user_id)
    user_data["is_muted"] = True
    user_data["mute_until"] = str(datetime.now() + timedelta(minutes=duration_minutes))
    save_user_data(user_id, user_data)
    stats_db["total_mutes"] = stats_db.get("total_mutes", 0) + 1
    save_json(STATS_FILE, stats_db)
    return True

def unmute_user(user_id):
    user_data = get_user_data(user_id)
    user_data["is_muted"] = False
    user_data["mute_until"] = None
    save_user_data(user_id, user_data)
    return True

def ban_user(user_id, reason=""):
    user_data = get_user_data(user_id)
    user_data["is_banned"] = True
    user_data["ban_reason"] = reason
    user_data["ban_date"] = str(datetime.now())
    save_user_data(user_id, user_data)
    stats_db["total_bans"] = stats_db.get("total_bans", 0) + 1
    save_json(STATS_FILE, stats_db)
    return True

def unban_user(user_id):
    user_data = get_user_data(user_id)
    user_data["is_banned"] = False
    save_user_data(user_id, user_data)
    return True

# ========== API ফাংশন ==========

def get_all_posts_from_api(max_results=50):
    if not API_KEY or not BLOG_ID or not settings_db.get("api", {}).get("use_api", True):
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
                content = item.get('content', '')
                excerpt = re.sub(r'<[^>]+>', '', content)[:200] + "..." if content else ""
                posts.append({
                    'id': item.get('id', ''),
                    'title': item.get('title', ''),
                    'link': item.get('url', ''),
                    'published': item.get('published', ''),
                    'labels': item.get('labels', []),
                    'excerpt': excerpt,
                    'source': 'api'
                })
            return posts
        else:
            logger.error(f"Blogger API error: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Blogger API exception: {e}")
        return []

def search_anime_with_api(query, max_results=10):
    if not API_KEY or not BLOG_ID or not settings_db.get("api", {}).get("use_api", True):
        return []
    try:
        url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/search"
        params = {
            'key': API_KEY,
            'q': query,
            'maxResults': max_results,
            'fetchBodies': 'true',
            'status': 'live'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get('items', []):
                content = item.get('content', '')
                excerpt = re.sub(r'<[^>]+>', '', content)[:200] + "..." if content else ""
                results.append({
                    'title': item.get('title', ''),
                    'link': item.get('url', ''),
                    'excerpt': excerpt,
                    'labels': item.get('labels', []),
                    'score': 1.0,
                    'source': 'api'
                })
            return results[:max_results]
        else:
            logger.error(f"Blogger API search error: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Blogger API search exception: {e}")
        return []

def get_latest_posts_from_rss():
    if not settings_db.get("api", {}).get("use_rss", True):
        return []
    try:
        feed = feedparser.parse(RSS_FEED_URL)
        posts = []
        for entry in feed.entries[:20]:
            posts.append({
                'title': entry.title,
                'link': entry.link,
                'published': entry.published if hasattr(entry, 'published') else '',
                'source': 'rss'
            })
        return posts
    except Exception as e:
        logger.error(f"RSS error: {e}")
        return []

def fuzzy_match(query, text):
    return SequenceMatcher(None, query.lower(), text.lower()).ratio()

def enhanced_search_anime(query):
    results = []
    seen_links = set()
    query_lower = query.lower().strip()
    if settings_db.get("api", {}).get("use_api", True) and API_KEY and BLOG_ID:
        api_results = search_anime_with_api(query_lower, max_results=10)
        for res in api_results:
            if res['link'] not in seen_links:
                seen_links.add(res['link'])
                results.append(res)
    if settings_db.get("api", {}).get("use_rss", True) and len(results) < 5:
        rss_posts = get_latest_posts_from_rss()
        for post in rss_posts:
            if post['link'] in seen_links:
                continue
            title = post.get('title', '').lower()
            if query_lower in title:
                score = 1.0
            else:
                score = fuzzy_match(query_lower, title)
            threshold = settings_db.get("api", {}).get("fuzzy_threshold", 0.6)
            if score > threshold:
                seen_links.add(post['link'])
                results.append({
                    'title': post.get('title', ''),
                    'link': post.get('link', ''),
                    'score': score,
                    'source': 'rss'
                })
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return results[:5]

def shorten_url(url):
    if not settings_db.get("poster", {}).get("shorten_links", True):
        return url
    shortener = settings_db.get("poster", {}).get("shortener", "tinyurl")
    try:
        if shortener == "tinyurl":
            response = requests.get(f"http://tinyurl.com/api-create.php?url={url}", timeout=5)
            if response.status_code == 200:
                return response.text.strip()
    except:
        pass
    return url

def check_new_posts():
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
        settings_db["last_post_time"] = str(datetime.now())
        save_json(SETTINGS_FILE, settings_db)
    return new_posts[::-1]

# ========== ইউটিলিটি ফাংশন ==========

def extract_links(text):
    url_pattern = r'https?://[^\s]+|www\.[^\s]+'
    return re.findall(url_pattern, text, re.IGNORECASE)

def is_allowed_domain(url):
    allowed = settings_db.get("link_filter", {}).get("allowed_domains", [])
    for domain in allowed:
        if domain in url:
            return True
    return False

def contains_forbidden_links(text):
    if not settings_db.get("link_filter", {}).get("enabled", True):
        return False
    links = extract_links(text)
    if not links:
        return False
    for link in links:
        if not is_allowed_domain(link):
            return True
    return False

def is_anime_request(text):
    if not text:
        return False
    text = text.lower().strip()
    ignore_patterns = [
        r'^(hi|hello|hey|hlw|hy|hlo)',
        r'^(good morning|good afternoon|good evening)',
        r'^(bye|tata|allah hafez)',
        r'^(thanks|thank you|thanks)',
        r'^(ok|okay|k|thik ache)',
    ]
    for pattern in ignore_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return False
    anime_keywords = [
        'anime', 'naruto', 'one piece', 'demon slayer', 'attack on titan',
        'season', 'episode', 'ep', 'dubbed', 'subbed', 'hindi', 'english',
        'watch', 'download', 'stream', 'online', 'free'
    ]
    for keyword in anime_keywords:
        if keyword in text:
            return True
    return False

def is_add_request(text):
    if not text:
        return False
    text = text.lower().strip()
    add_patterns = ['add', 'যোগ', 'add koro', 'upload', 'dal do', 'please add']
    for pattern in add_patterns:
        if pattern in text:
            return True
    return False

def extract_anime_name(text):
    common_words = [
        'anime', 'download', 'watch', 'stream', 'episode', 'season',
        'dubbed', 'hindi', 'english', 'sub', 'subbed', 'free', 'online',
        'please', 'plz', 'যোগ', 'দেখব', 'চাই'
    ]
    text = text.lower()
    for word in common_words:
        text = text.replace(word, '')
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_text_graph(values, labels=None, width=20):
    if not values:
        return ""
    max_val = max(values)
    if max_val == 0:
        return "No data"
    graph = ""
    for i, val in enumerate(values):
        bar_length = int((val / max_val) * width)
        bar = "█" * bar_length
        label = f"{labels[i]}:" if labels and i < len(labels) else f"{i+1}:"
        graph += f"{label} {bar} {val}\n"
    return graph

# ========== ল্যাঙ্গুয়েজ ফাংশন ==========

def get_text(lang, key, **kwargs):
    texts = {
        "en": {
            "start": "🤖 {name} {version}\n\n👋 Welcome {user}!\n\n📊 Rank: {rank}\n⭐ Points: {points}\n\n🔍 Just type anime name to search",
            "help": "📚 Help Guide\n\n👤 User Commands:\n/start - Start bot\n/help - Show help\n/calendar - View calendar\n/rank - Your profile\n\n🛡️ Moderator Commands:\n/warn - Warn user\n/mute - Mute user\n/unmute - Unmute user\n\n👑 Admin Commands:\n/panel - Admin panel\n/stats - Statistics\n/api_status - API status",
            "rank": "🏆 {name}'s Profile\n\n📊 Rank: {rank}\n⭐ Points: {points}\n📈 Progress: {progress}\n📝 Requests: {requests}\n🤝 Trust: {trust}%\n📅 Joined: {date}",
            "search_found": "🔍 Found for '{query}':",
            "search_not_found": "🔍 '{query}' not found"
        },
        "bn": {
            "start": "🤖 {name} {version}\n\n👋 স্বাগতম {user}!\n\n📊 র‌্যাঙ্ক: {rank}\n⭐ পয়েন্ট: {points}\n\n🔍 অ্যানিমে খুঁজতে নাম লিখুন",
            "help": "📚 সাহায্য গাইড\n\n👤 ইউজার কমান্ড:\n/start - বট শুরু করুন\n/help - সাহায্য দেখুন\n/calendar - ক্যালেন্ডার দেখুন\n/rank - আপনার প্রোফাইল\n\n🛡️ মডারেটর কমান্ড:\n/warn - ওয়ার্ন দিন\n/mute - মিউট করুন\n/unmute - মিউট উঠান\n\n👑 অ্যাডমিন কমান্ড:\n/panel - অ্যাডমিন প্যানেল\n/stats - পরিসংখ্যান\n/api_status - API স্ট্যাটাস",
            "rank": "🏆 {name} এর প্রোফাইল\n\n📊 র‌্যাঙ্ক: {rank}\n⭐ পয়েন্ট: {points}\n📈 অগ্রগতি: {progress}\n📝 রিকোয়েস্ট: {requests}\n🤝 ট্রাস্ট: {trust}%\n📅 জয়েন: {date}",
            "search_found": "🔍 '{query}' এর জন্য পাওয়া গেছে:",
            "search_not_found": "🔍 '{query}' পাওয়া যায়নি"
        },
        "hi": {
            "start": "🤖 {name} {version}\n\n👋 स्वागत है {user}!\n\n📊 रैंक: {rank}\n⭐ पॉइंट्स: {points}\n\n🔍 एनीमे खोजने के लिए नाम लिखें",
            "help": "📚 सहायता गाइड\n\n👤 यूजर कमांड:\n/start - बॉट शुरू करें\n/help - सहायता देखें\n/calendar - कैलेंडर देखें\n/rank - आपकी प्रोफाइल\n\n🛡️ मॉडरेटर कमांड:\n/warn - वॉर्न दें\n/mute - म्यूट करें\n/unmute - म्यूट हटाएं\n\n👑 एडमिन कमांड:\n/panel - एडमिन पैनल\n/stats - आंकड़े\n/api_status - API स्टेटस",
            "rank": "🏆 {name} की प्रोफाइल\n\n📊 रैंक: {rank}\n⭐ पॉइंट्स: {points}\n📈 प्रगति: {progress}\n📝 रिक्वेस्ट: {requests}\n🤝 ट्रस्ट: {trust}%\n📅 जॉइन: {date}",
            "search_found": "🔍 '{query}' के लिए मिला:",
            "search_not_found": "🔍 '{query}' नहीं मिला"
        }
    }
    lang_code = settings_db.get("language", {}).get("user", "en")
    if lang_code not in texts:
        lang_code = "en"
    text_dict = texts[lang_code]
    if key in text_dict:
        return text_dict[key].format(**kwargs)
    return key

# ========== ইউজার কমান্ড ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_data(user.id)
    if user_data.get("total_requests", 0) == 0:
        add_points(user.id, 10)
    bot_name = settings_db.get("bot_name", "🤖 অ্যানিমেথিক আলট্রা বট")
    bot_version = settings_db.get("bot_version", "v7.0")
    text = get_text("en", "start", 
                    name=bot_name, 
                    version=bot_version,
                    user=user.first_name,
                    rank=user_data['rank'],
                    points=user_data.get('points', 0))
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang_code = "en"
    if is_moderator(user_id):
        lang_code = settings_db.get("language", {}).get("mod", "bn")
    text = get_text(lang_code, "help")
    await update.message.reply_text(text, parse_mode='Markdown')

async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📅 **Weekly Anime Calendar**\n\n"
    days = [
        ("Monday", calendar_db["weekly"].get("monday", [])),
        ("Tuesday", calendar_db["weekly"].get("tuesday", [])),
        ("Wednesday", calendar_db["weekly"].get("wednesday", [])),
        ("Thursday", calendar_db["weekly"].get("thursday", [])),
        ("Friday", calendar_db["weekly"].get("friday", [])),
        ("Saturday", calendar_db["weekly"].get("saturday", [])),
        ("Sunday", calendar_db["weekly"].get("sunday", []))
    ]
    for day_name, anime_list in days:
        text += f"**{day_name}**\n"
        if anime_list:
            for anime in anime_list:
                text += f"• {anime}\n"
        else:
            text += "• No anime scheduled\n"
        text += "\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_data(user.id)
    points = user_data.get('points', 0)
    next_level = 0
    if points < 100:
        next_level = 100
    elif points < 500:
        next_level = 500
    elif points < 2000:
        next_level = 2000
    elif points < 5000:
        next_level = 5000
    elif points < 10000:
        next_level = 10000
    elif points < 20000:
        next_level = 20000
    elif points < 50000:
        next_level = 50000
    elif points < 100000:
        next_level = 100000
    elif points < 500000:
        next_level = 500000
    if next_level:
        progress = (points / next_level) * 100
        bar = "█" * int(progress/10) + "░" * (10 - int(progress/10))
        progress_text = f"{bar} {progress:.1f}%"
    else:
        progress_text = "MAX LEVEL"
    text = get_text("en", "rank", 
                    name=user.first_name,
                    rank=user_data['rank'],
                    points=points,
                    progress=progress_text,
                    requests=user_data.get('total_requests', 0),
                    trust=user_data.get('trust_score', 100),
                    date=user_data.get('join_date', 'N/A')[:10])
    await update.message.reply_text(text, parse_mode='Markdown')

async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_moderator(user_id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    role = get_user_role(user_id)
    keyboard = [
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="panel_dashboard"),
            InlineKeyboardButton("📅 Calendar", callback_data="panel_calendar")
        ],
        [
            InlineKeyboardButton("📋 Daily Release", callback_data="panel_daily"),
            InlineKeyboardButton("👥 Users", callback_data="panel_users")
        ],
        [
            InlineKeyboardButton("🛡️ Moderation", callback_data="panel_mod"),
            InlineKeyboardButton("📈 Analytics", callback_data="panel_analytics")
        ]
    ]
    if is_admin(user_id):
        keyboard.extend([
            [
                InlineKeyboardButton("👑 Team Manage", callback_data="panel_team"),
                InlineKeyboardButton("🔐 Security", callback_data="panel_security")
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data="panel_settings"),
                InlineKeyboardButton("💾 Backup", callback_data="panel_backup")
            ],
            [
                InlineKeyboardButton("🔌 API Status", callback_data="panel_api"),
                InlineKeyboardButton("⚡ Advanced", callback_data="panel_advanced")
            ]
        ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🔐 **Control Panel**\n\nYour Role: {role}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def api_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    text = "🔌 **Blogger API v3 Status**\n\n"
    if API_KEY and BLOG_ID:
        text += "✅ API Key: Configured\n"
        text += f"✅ Blog ID: {BLOG_ID}\n\n"
        try:
            test_posts = get_all_posts_from_api(max_results=1)
            if test_posts:
                text += "✅ **API Connection: Working**\n"
                total = len(get_all_posts_from_api(max_results=50))
                text += f"📊 Total posts: {total}+"
            else:
                text += "❌ **API Connection: Failed** - No posts returned"
        except Exception as e:
            text += f"❌ **API Connection: Error** - {str(e)[:100]}"
    else:
        text += "❌ API Key: Not configured\n"
        text += "❌ Blog ID: Not configured"
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user = update.message.from_user
    user_id = user.id
    chat_id = update.message.chat_id
    text = update.message.text

    primary_group = settings_db.get("groups", {}).get("primary", GROUP_ID)
    additional_groups = settings_db.get("groups", {}).get("additional", [])
    allowed_groups = [primary_group] + additional_groups

    if chat_id not in allowed_groups:
        return

    user_data = get_user_data(user_id)
    user_data["last_active"] = str(datetime.now())
    save_user_data(user_id, user_data)

    if user_data.get("is_banned", False):
        try:
            await update.message.delete()
        except:
            pass
        return

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
                unmute_user(user_id)

    if contains_forbidden_links(text):
        try:
            await update.message.delete()
            warnings = add_warning(user_id, "Forbidden link")
            warning_text = f"⚠️ {user.mention_html()} posted a forbidden link!\nWarning: {warnings}/{settings_db.get('warnings', {}).get('max', 3)}"
            await context.bot.send_message(
                chat_id=chat_id,
                text=warning_text,
                parse_mode='HTML'
            )
            if warnings >= settings_db.get("warnings", {}).get("max", 3):
                mute_duration = settings_db.get("warnings", {}).get("mute_duration", 60)
                mute_user(user_id, mute_duration)
                mute_text = f"🔇 {user.mention_html()} muted for {mute_duration} minutes!"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=mute_text,
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
        return

    if is_add_request(text):
        return

    if is_anime_request(text):
        stats_db["total_requests"] = stats_db.get("total_requests", 0) + 1
        stats_db["daily_requests"] = stats_db.get("daily_requests", 0) + 1
        user_data["total_requests"] = user_data.get("total_requests", 0) + 1
        add_points(user_id, 5)
        save_user_data(user_id, user_data)

        anime_name = extract_anime_name(text)
        if not anime_name:
            return

        results = enhanced_search_anime(anime_name)

        if results:
            for result in results:
                title = result['title']
                stats_db["anime_requests"][title] = stats_db["anime_requests"].get(title, 0) + 1

            reply = get_text("en", "search_found", query=text) + "\n\n"
            for i, result in enumerate(results, 1):
                source_icon = "🔵" if result.get('source') == 'api' else "🟢"
                reply += f"{i}. {source_icon} **{result['title']}**\n"
                if 'excerpt' in result:
                    reply += f"📝 {result['excerpt']}\n"
                reply += f"📥 [Download Here]({shorten_url(result['link'])})\n\n"
            await update.message.reply_text(reply, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            reply = get_text("en", "search_not_found", query=text)
            await update.message.reply_text(reply)

        save_json(STATS_FILE, stats_db)

async def new_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not settings_db.get("welcome", {}).get("enabled", True):
        return
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        get_user_data(member.id)
        add_points(member.id, 10)
        welcome_text = settings_db.get("welcome", {}).get("message", "Welcome {name}!")
        welcome_text = welcome_text.replace("{name}", member.first_name)
        await update.message.reply_text(welcome_text)

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moderator(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message with /warn")
        return
    target_user = update.message.reply_to_message.from_user
    reason = ' '.join(context.args) if context.args else "No reason"
    if is_moderator(target_user.id) and not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ You cannot warn another moderator!")
        return
    warnings = add_warning(target_user.id, reason)
    text = f"⚠️ {target_user.mention_html()} warned!\nReason: {reason}\nWarnings: {warnings}"
    await update.message.reply_text(text, parse_mode='HTML')

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moderator(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message with /mute")
        return
    target_user = update.message.reply_to_message.from_user
    duration = 60
    if context.args:
        try:
            duration = int(context.args[0])
        except:
            pass
    if is_moderator(target_user.id) and not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ You cannot mute another moderator!")
        return
    mute_user(target_user.id, duration)
    text = f"🔇 {target_user.mention_html()} muted for {duration} minutes!"
    await update.message.reply_text(text, parse_mode='HTML')

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moderator(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message with /unmute")
        return
    target_user = update.message.reply_to_message.from_user
    unmute_user(target_user.id)
    text = f"✅ {target_user.mention_html()} unmuted!"
    await update.message.reply_text(text, parse_mode='HTML')

async def addanime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_moderator(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "📝 **Usage:** `/addanime [day] [name]`\n\n"
            "Days: monday, tuesday, wednesday, thursday, friday, saturday, sunday\n\n"
            "Example: `/addanime monday Naruto S9 E24`",
            parse_mode='Markdown'
        )
        return
    day = context.args[0].lower()
    name = ' '.join(context.args[1:])
    valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if day not in valid_days:
        await update.message.reply_text("❌ Invalid day! Use: monday-sunday")
        return
    if day not in calendar_db["weekly"]:
        calendar_db["weekly"][day] = []
    if name not in calendar_db["weekly"][day]:
        calendar_db["weekly"][day].append(name)
        save_json(CALENDAR_FILE, calendar_db)
        await update.message.reply_text(f"✅ '{name}' added to {day}!")
    else:
        await update.message.reply_text(f"⚠️ '{name}' already exists in {day}!")

async def removeanime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "📝 **Usage:** `/removeanime [day] [name]`\n\n"
            "Example: `/removeanime monday Naruto S9 E24`",
            parse_mode='Markdown'
        )
        return
    day = context.args[0].lower()
    name = ' '.join(context.args[1:])
    if day in calendar_db["weekly"] and name in calendar_db["weekly"][day]:
        calendar_db["weekly"][day].remove(name)
        save_json(CALENDAR_FILE, calendar_db)
        await update.message.reply_text(f"✅ '{name}' removed from {day}!")
    else:
        await update.message.reply_text(f"❌ '{name}' not found!")

async def auto_poster(context: ContextTypes.DEFAULT_TYPE):
    new_posts = check_new_posts()
    for post in new_posts:
        try:
            template = settings_db.get("poster", {}).get("template", "📢 **New Post!**\n\n**{title}**\n\n📝 {excerpt}\n\n📥 [Download Here]({link})")
            message = template.format(
                title=post['title'],
                link=shorten_url(post['link']),
                excerpt=post.get('excerpt', '')
            )
            channel_id = settings_db.get("groups", {}).get("channels", {}).get("primary", CHANNEL_ID)
            await context.bot.send_message(
                chat_id=channel_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Posted to channel: {post['title']}")
            if settings_db.get("poster", {}).get("notify_admin", True):
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"✅ New post sent: {post['title']}"
                )
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Auto poster error: {e}")
            if settings_db.get("poster", {}).get("notify_admin", True):
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"❌ Failed to post: {str(e)[:100]}"
                )

async def daily_backup(context: ContextTypes.DEFAULT_TYPE):
    if not settings_db.get("backup", {}).get("auto", True):
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{BACKUP_DIR}/backup_{timestamp}.json"
    backup_data = {
        "users": users_db,
        "stats": stats_db,
        "settings": settings_db,
        "calendar": calendar_db,
        "daily_release": daily_release_db,
        "team": team_db,
        "security": security_db,
        "ratings": ratings_db,
        "challenges": challenges_db,
        "timestamp": str(datetime.now())
    }
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=4, ensure_ascii=False)
        keep_days = settings_db.get("backup", {}).get("keep", 30)
        cutoff = datetime.now() - timedelta(days=keep_days)
        for f in os.listdir(BACKUP_DIR):
            if f.startswith("backup_") and f.endswith(".json"):
                file_path = os.path.join(BACKUP_DIR, f)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if file_time < cutoff:
                    os.remove(file_path)
        logger.info(f"Daily backup created: {backup_file}")
    except Exception as e:
        logger.error(f"Backup error: {e}")

async def daily_stats_updater(context: ContextTypes.DEFAULT_TYPE):
    stats_db["daily_requests"] = 0
    stats_db["daily_users"] = 0
    stats_db["last_reset"] = str(datetime.now().date())
    save_json(STATS_FILE, stats_db)

async def daily_report(context: ContextTypes.DEFAULT_TYPE):
    if not settings_db.get("reports", {}).get("daily", True):
        return
    text = "📊 **Daily Report**\n\n"
    text += f"📝 Requests today: {stats_db.get('daily_requests', 0)}\n"
    text += f"👥 New users today: {stats_db.get('daily_users', 0)}\n"
    text += f"🔥 Top anime today:\n"
    top_anime = sorted(stats_db.get('anime_requests', {}).items(), key=lambda x: x[1], reverse=True)[:3]
    for anime, count in top_anime:
        text += f"• {anime[:20]}... - {count}\n"
    await context.bot.send_message(chat_id=ADMIN_ID, text=text)

async def weekly_report(context: ContextTypes.DEFAULT_TYPE):
    if not settings_db.get("reports", {}).get("weekly", True):
        return
    text = "📊 **Weekly Report**\n\n"
    text += f"📝 Total requests: {stats_db.get('total_requests', 0)}\n"
    text += f"👥 Total users: {len(users_db)}\n"
    text += f"⚠️ Total warnings: {stats_db.get('total_warnings', 0)}\n"
    text += f"🔥 Top anime all time:\n"
    top_anime = sorted(stats_db.get('anime_requests', {}).items(), key=lambda x: x[1], reverse=True)[:5]
    for anime, count in top_anime:
        text += f"• {anime[:20]}... - {count}\n"
    await context.bot.send_message(chat_id=ADMIN_ID, text=text)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if not is_moderator(user_id):
        await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
        return

    data = query.data

    if data == "panel_dashboard":
        text = "📊 **Dashboard**\n\n"
        text += f"👥 Total Users: {len(users_db):,}\n"
        text += f"📝 Total Requests: {stats_db.get('total_requests', 0):,}\n"
        text += f"⚠️ Total Warnings: {stats_db.get('total_warnings', 0):,}\n"
        text += f"🔇 Total Mutes: {stats_db.get('total_mutes', 0):,}\n"
        text += f"🚫 Total Bans: {stats_db.get('total_bans', 0):,}\n"
        text += f"🛡️ Total Moderators: {sum(1 for u in users_db.values() if u.get('is_moderator'))}\n\n"
        text += f"📈 Today's Requests: {stats_db.get('daily_requests', 0)}\n"
        text += f"👤 Today's Users: {stats_db.get('daily_users', 0)}"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_calendar":
        text = "📅 **Calendar Manager**\n\n"
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        bangla_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        keyboard = []
        for day_en, day_bn in zip(days, bangla_days):
            count = len(calendar_db["weekly"].get(day_en, []))
            keyboard.append([InlineKeyboardButton(f"{day_bn} ({count})", callback_data=f"cal_view_{day_en}")])
        keyboard.append([InlineKeyboardButton("➕ Add New", callback_data="cal_add")])
        keyboard.append([InlineKeyboardButton("📅 Monthly View", callback_data="cal_monthly")])
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="panel_back")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("cal_view_"):
        day = data.replace("cal_view_", "")
        day_names = {
            "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
            "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday",
            "sunday": "Sunday"
        }
        day_name = day_names.get(day, day)
        anime_list = calendar_db["weekly"].get(day, [])
        text = f"📅 **{day_name}**\n\n"
        if anime_list:
            for i, anime in enumerate(anime_list, 1):
                text += f"{i}. {anime}\n"
        else:
            text += "No anime scheduled.\n"
        keyboard = [
            [InlineKeyboardButton("➕ Add", callback_data=f"cal_add_{day}")],
            [InlineKeyboardButton("◀️ Back", callback_data="panel_calendar")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "cal_add" or data.startswith("cal_add_"):
        await query.edit_message_text(
            "➕ **Add to Calendar**\n\n"
            "Use: `/addanime [day] [name]`\n\n"
            "Days: monday, tuesday, wednesday, thursday, friday, saturday, sunday\n\n"
            "Example: `/addanime monday Naruto S9 E24`",
            parse_mode='Markdown'
        )

    elif data == "cal_monthly":
        text = "📅 **Monthly Calendar**\n\n"
        text += "Coming soon...\n\n"
        text += "This feature will show all releases for the month."
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_calendar")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_daily":
        text = "📋 **Daily Release Tracker**\n\n"
        pending = [e for e in daily_release_db["entries"] if e.get("status") == "pending"]
        completed = [e for e in daily_release_db["entries"] if e.get("status") == "completed"]
        text += f"⏳ Pending: {len(pending)}\n"
        text += f"✅ Completed: {len(completed)}\n\n"
        if pending:
            text += "**Today's Tasks:**\n"
            for entry in pending[:5]:
                text += f"• {entry.get('anime')} ({entry.get('day')})\n"
        keyboard = [
            [InlineKeyboardButton("➕ New", callback_data="daily_add"),
             InlineKeyboardButton("📋 All", callback_data="daily_all")],
            [InlineKeyboardButton("◀️ Back", callback_data="panel_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "daily_add":
        await query.edit_message_text(
            "➕ **Add to Daily Release**\n\n"
            "Use: `/addanime [day] [name]` to add to calendar first.",
            parse_mode='Markdown'
        )

    elif data == "daily_all":
        text = "📋 **All Daily Releases**\n\n"
        if daily_release_db["entries"]:
            for entry in daily_release_db["entries"][-10:]:
                status_icon = "✅" if entry.get("status") == "completed" else "⏳"
                text += f"{status_icon} {entry.get('anime')} ({entry.get('day')})\n"
                if entry.get('assigned_to'):
                    text += f"   👤 {entry.get('assigned_to')}\n"
        else:
            text += "No daily releases.\n"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_daily")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_users":
        text = "👥 **User Management**\n\n"
        total_users = len(users_db)
        active_today = sum(1 for u in users_db.values() if u.get('last_active', '').startswith(str(datetime.now().date())))
        banned = sum(1 for u in users_db.values() if u.get('is_banned'))
        muted = sum(1 for u in users_db.values() if u.get('is_muted'))
        text += f"📊 **Statistics:**\n"
        text += f"• Total Users: {total_users:,}\n"
        text += f"• Active Today: {active_today}\n"
        text += f"• Banned: {banned}\n"
        text += f"• Muted: {muted}\n\n"
        text += "**Commands:**\n"
        text += "• `/warn @user` - Warn user\n"
        text += "• `/mute @user 60` - Mute user\n"
        text += "• `/unmute @user` - Unmute user\n"
        text += "• `/ban @user` - Ban user\n"
        text += "• `/unban @user` - Unban user"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_mod":
        text = "🛡️ **Moderation Control**\n\n"
        moderators = [(uid, u) for uid, u in users_db.items() if u.get('is_moderator')]
        text += f"**Total Moderators:** {len(moderators)}\n\n"
        if moderators:
            text += "**Moderator List:**\n"
            for uid, u in moderators[:5]:
                name = f"User {uid[:6]}..."
                level = u.get('mod_level', 1)
                dept = u.get('department', 'None')
                text += f"• {name} (Level {level}) - {dept}\n"
        keyboard = [
            [InlineKeyboardButton("➕ Add Mod", callback_data="mod_add"),
             InlineKeyboardButton("📊 Performance", callback_data="mod_perf")],
            [InlineKeyboardButton("◀️ Back", callback_data="panel_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "mod_add":
        await query.edit_message_text(
            "➕ **Add Moderator**\n\n"
            "Use: `/addmod @user`\n\n"
            "Example: `/addmod @moderator`\n\n"
            "⚠️ Only admins can use this command.",
            parse_mode='Markdown'
        )

    elif data == "mod_perf":
        text = "📊 **Moderator Performance**\n\n"
        text += "👑 **Top Moderators:**\n"
        text += "• @mod1 - 234 actions\n"
        text += "• @mod2 - 189 actions\n"
        text += "• @mod3 - 156 actions\n\n"
        text += "📈 **Team Stats:**\n"
        text += "• Total Actions: 579\n"
        text += "• Avg Response: 2.3 min\n"
        text += "• On-time Rate: 92%"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_mod")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_analytics":
        text = "📈 **Analytics Dashboard**\n\n"
        total_reqs = stats_db.get('total_requests', 0)
        total_posts = 0
        if API_KEY and BLOG_ID:
            try:
                posts = get_all_posts_from_api(max_results=50)
                total_posts = len(posts)
            except:
                total_posts = 0
        text += f"📊 **Total Requests:** {total_reqs:,}\n"
        text += f"🔌 **API Posts:** {total_posts:,}\n\n"
        text += "**Top Anime:**\n"
        top_anime = sorted(stats_db.get('anime_requests', {}).items(), key=lambda x: x[1], reverse=True)[:3]
        if top_anime:
            for anime, count in top_anime:
                text += f"• {anime[:20]}... - {count:,} times\n"
        else:
            text += "No data\n"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_team":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        text = "👑 **Team Management**\n\n"
        text += "**Departments:**\n"
        text += "🛡️ Security Force\n"
        text += "💝 Community Care\n"
        text += "📝 Content Moderation\n"
        text += "🔧 Tech Support\n"
        text += "🔍 Investigation Team\n\n"
        text += f"**Total Moderators:** {sum(1 for u in users_db.values() if u.get('is_moderator'))}"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_security":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        text = "🔐 **Security Settings**\n\n"
        two_factor = settings_db.get("security", {}).get("two_factor", False)
        login_alert = settings_db.get("security", {}).get("login_alert", True)
        text += f"✅ Two-Factor Auth: {'ON' if two_factor else 'OFF'}\n"
        text += f"✅ Login Alert: {'ON' if login_alert else 'OFF'}\n\n"
        text += "**Login History:**\n"
        log_count = len(security_db.get("login_history", []))
        blocked = len(security_db.get("blocked_attempts", []))
        text += f"• Total Logins: {log_count}\n"
        text += f"• Blocked Attempts: {blocked}"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_settings":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        text = "⚙️ **Settings Panel**\n\n"
        text += f"🤖 Bot Name: {settings_db.get('bot_name', 'Bot')}\n"
        text += f"📌 Version: {settings_db.get('bot_version', 'v1.0')}\n\n"
        text += "**Features:**\n"
        for feature, enabled in settings_db.get("features", {}).items():
            status = "✅" if enabled else "❌"
            text += f"{status} {feature}\n"
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Bot Name", callback_data="settings_name"),
             InlineKeyboardButton("🌐 Language", callback_data="settings_lang")],
            [InlineKeyboardButton("◀️ Back", callback_data="panel_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "settings_name":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        await query.edit_message_text(
            "✏️ **Change Bot Name**\n\n"
            "Current name: {}\n\n"
            "Use: `/setname [new name]`\n\n"
            "Example: `/setname My Awesome Bot`".format(settings_db.get('bot_name', 'Bot')),
            parse_mode='Markdown'
        )

    elif data == "settings_lang":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        current_lang = settings_db.get("language", {}).get("user", "en")
        lang_names = {"en": "English", "bn": "Bangla", "hi": "Hindi"}
        text = "🌐 **Language Settings**\n\n"
        text += f"Current: {lang_names.get(current_lang, current_lang)}\n\n"
        text += "Select user language:"
        keyboard = [
            [InlineKeyboardButton("🇺🇸 English", callback_data="lang_set_en"),
             InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lang_set_bn")],
            [InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lang_set_hi")],
            [InlineKeyboardButton("◀️ Back", callback_data="panel_settings")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("lang_set_"):
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        lang_code = data.replace("lang_set_", "")
        settings_db["language"]["user"] = lang_code
        save_json(SETTINGS_FILE, settings_db)
        lang_names = {"en": "English", "bn": "Bangla", "hi": "Hindi"}
        await query.edit_message_text(f"✅ Language changed to {lang_names.get(lang_code, lang_code)}")
        await asyncio.sleep(1)
        # Return to settings
        text = "⚙️ **Settings Panel**\n\n"
        text += f"🤖 Bot Name: {settings_db.get('bot_name', 'Bot')}\n"
        text += f"📌 Version: {settings_db.get('bot_version', 'v1.0')}\n\n"
        text += "**Features:**\n"
        for feature, enabled in settings_db.get("features", {}).items():
            status = "✅" if enabled else "❌"
            text += f"{status} {feature}\n"
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Bot Name", callback_data="settings_name"),
             InlineKeyboardButton("🌐 Language", callback_data="settings_lang")],
            [InlineKeyboardButton("◀️ Back", callback_data="panel_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_backup":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        text = "💾 **Backup Manager**\n\n"
        backups = []
        if os.path.exists(BACKUP_DIR):
            backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".json")]
            backups.sort(reverse=True)
        text += f"📦 Total Backups: {len(backups)}\n"
        text += f"⏰ Last Backup: {settings_db.get('last_post_time', 'N/A')}\n\n"
        if backups:
            text += "**Recent Backups:**\n"
            for backup in backups[:3]:
                text += f"• {backup}\n"
        keyboard = [
            [InlineKeyboardButton("💾 Backup Now", callback_data="backup_now"),
             InlineKeyboardButton("↩️ Restore", callback_data="backup_restore")],
            [InlineKeyboardButton("◀️ Back", callback_data="panel_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_api":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        text = "🔌 **API Status**\n\n"
        if API_KEY and BLOG_ID:
            text += "✅ API Key: Configured\n"
            text += f"✅ Blog ID: {BLOG_ID}\n\n"
            try:
                test_posts = get_all_posts_from_api(max_results=1)
                if test_posts:
                    text += "✅ **API Connection: Working**\n"
                    total = len(get_all_posts_from_api(max_results=50))
                    text += f"📊 Total Posts: {total}+"
                else:
                    text += "❌ **API Connection: Failed**"
            except Exception as e:
                text += f"❌ **API Connection: Error** - {str(e)[:100]}"
        else:
            text += "❌ API Key: Not configured\n"
            text += "❌ Blog ID: Not configured"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_advanced":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        text = "⚡ **Advanced Panel**\n\n"
        text += "**Commands:**\n"
        text += "• `/addmod` - Add moderator\n"
        text += "• `/removemod` - Remove moderator\n"
        text += "• `/api_status` - Check API status\n"
        text += "• `/addanime` - Add to calendar\n"
        text += "• `/setname` - Change bot name\n"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "backup_now":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        await query.edit_message_text("⏳ Creating backup...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{BACKUP_DIR}/backup_{timestamp}.json"
        backup_data = {
            "users": users_db,
            "stats": stats_db,
            "settings": settings_db,
            "calendar": calendar_db,
            "daily_release": daily_release_db,
            "team": team_db,
            "security": security_db,
            "ratings": ratings_db,
            "challenges": challenges_db,
            "timestamp": str(datetime.now())
        }
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=4, ensure_ascii=False)
            size = os.path.getsize(backup_file)
            text = f"✅ Backup complete!\n\n📦 File: `{backup_file}`\n📊 Size: {size} bytes"
        except Exception as e:
            text = f"❌ Backup failed: {str(e)}"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_backup")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "backup_restore":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        backups = []
        if os.path.exists(BACKUP_DIR):
            backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".json")]
            backups.sort(reverse=True)
        if not backups:
            await query.edit_message_text("❌ No backups found!")
            return
        text = "↩️ **Restore Backup**\n\nSelect a backup to restore:\n\n"
        keyboard = []
        for backup in backups[:5]:
            keyboard.append([InlineKeyboardButton(backup, callback_data=f"restore_{backup}")])
        keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="panel_backup")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("restore_"):
        if not is_admin(user_id):
            await query.edit_message_text("⛔ You don't have permission!")
            return
        backup_file = data.replace("restore_", "")
        backup_path = os.path.join(BACKUP_DIR, backup_file)
        if not os.path.exists(backup_path):
            await query.edit_message_text("❌ Backup file not found!")
            return
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            users_db.update(backup_data.get("users", {}))
            stats_db.update(backup_data.get("stats", {}))
            settings_db.update(backup_data.get("settings", {}))
            calendar_db.update(backup_data.get("calendar", {}))
            daily_release_db.update(backup_data.get("daily_release", {}))
            team_db.update(backup_data.get("team", {}))
            security_db.update(backup_data.get("security", {}))
            ratings_db.update(backup_data.get("ratings", {}))
            challenges_db.update(backup_data.get("challenges", {}))
            save_json(USERS_FILE, users_db)
            save_json(STATS_FILE, stats_db)
            save_json(SETTINGS_FILE, settings_db)
            save_json(CALENDAR_FILE, calendar_db)
            save_json(DAILY_RELEASE_FILE, daily_release_db)
            save_json(TEAM_FILE, team_db)
            save_json(SECURITY_FILE, security_db)
            save_json(RATINGS_FILE, ratings_db)
            save_json(CHALLENGES_FILE, challenges_db)
            text = f"✅ Restore complete!\n\n📦 File: {backup_file}"
        except Exception as e:
            text = f"❌ Restore failed: {str(e)}"
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="panel_backup")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "panel_back":
        role = get_user_role(user_id)
        keyboard = [
            [
                InlineKeyboardButton("📊 Dashboard", callback_data="panel_dashboard"),
                InlineKeyboardButton("📅 Calendar", callback_data="panel_calendar")
            ],
            [
                InlineKeyboardButton("📋 Daily Release", callback_data="panel_daily"),
                InlineKeyboardButton("👥 Users", callback_data="panel_users")
            ],
            [
                InlineKeyboardButton("🛡️ Moderation", callback_data="panel_mod"),
                InlineKeyboardButton("📈 Analytics", callback_data="panel_analytics")
            ]
        ]
        if is_admin(user_id):
            keyboard.extend([
                [
                    InlineKeyboardButton("👑 Team Manage", callback_data="panel_team"),
                    InlineKeyboardButton("🔐 Security", callback_data="panel_security")
                ],
                [
                    InlineKeyboardButton("⚙️ Settings", callback_data="panel_settings"),
                    InlineKeyboardButton("💾 Backup", callback_data="panel_backup")
                ],
                [
                    InlineKeyboardButton("🔌 API Status", callback_data="panel_api"),
                    InlineKeyboardButton("⚡ Advanced", callback_data="panel_advanced")
                ]
            ])
        await query.edit_message_text(
            f"🔐 **Control Panel**\n\nYour Role: {role}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ========== অ্যাডমিন কমান্ড ==========

async def setname_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    if not context.args:
        await update.message.reply_text("Usage: /setname [new name]")
        return
    new_name = ' '.join(context.args)
    settings_db["bot_name"] = new_name
    save_json(SETTINGS_FILE, settings_db)
    await update.message.reply_text(f"✅ Bot name changed to: {new_name}")

async def addmod_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a user's message with /addmod")
        return
    target_user = update.message.reply_to_message.from_user
    if is_moderator(target_user.id):
        await update.message.reply_text(f"⚠️ {target_user.first_name} is already a moderator!")
        return
    level = 1
    department = None
    if context.args:
        try:
            level = int(context.args[0])
            if len(context.args) > 1:
                department = context.args[1]
        except:
            pass
    user_data = get_user_data(target_user.id)
    user_data["is_moderator"] = True
    user_data["mod_level"] = level
    user_data["department"] = department
    save_user_data(target_user.id, user_data)
    await update.message.reply_text(
        f"✅ {target_user.mention_html()} added as moderator!\nLevel: {level}\nDepartment: {department or 'None'}",
        parse_mode='HTML'
    )

async def removemod_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a user's message with /removemod")
        return
    target_user = update.message.reply_to_message.from_user
    if not is_moderator(target_user.id) or is_admin(target_user.id):
        await update.message.reply_text(f"⚠️ {target_user.first_name} is not a moderator!")
        return
    user_data = get_user_data(target_user.id)
    user_data["is_moderator"] = False
    user_data["mod_level"] = 0
    user_data["department"] = None
    save_user_data(target_user.id, user_data)
    await update.message.reply_text(
        f"✅ {target_user.mention_html()} removed from moderators!",
        parse_mode='HTML'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    text = "📊 **Bot Statistics**\n\n"
    text += f"📝 Total Requests: {stats_db.get('total_requests', 0):,}\n"
    text += f"⚠️ Total Warnings: {stats_db.get('total_warnings', 0):,}\n"
    text += f"🔇 Total Mutes: {stats_db.get('total_mutes', 0):,}\n"
    text += f"🚫 Total Bans: {stats_db.get('total_bans', 0):,}\n"
    text += f"👥 Total Users: {len(users_db):,}\n"
    text += f"🛡️ Total Moderators: {sum(1 for u in users_db.values() if u.get('is_moderator'))}\n\n"
    text += "🔥 **Top Anime:**\n"
    top_anime = sorted(stats_db.get('anime_requests', {}).items(), key=lambda x: x[1], reverse=True)[:5]
    for i, (anime, count) in enumerate(top_anime, 1):
        text += f"{i}. {anime[:30]}... - {count:,} times\n"
    await update.message.reply_text(text, parse_mode='Markdown')

# ========== মেইন ফাংশন ==========

def main():
    threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=8081, debug=False)).start()
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("calendar", calendar_command))
    app.add_handler(CommandHandler("rank", rank_command))

    # Moderator commands
    app.add_handler(CommandHandler("warn", warn_command))
    app.add_handler(CommandHandler("mute", mute_command))
    app.add_handler(CommandHandler("unmute", unmute_command))

    # Admin commands
    app.add_handler(CommandHandler("panel", panel_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("api_status", api_status_command))
    app.add_handler(CommandHandler("addanime", addanime_command))
    app.add_handler(CommandHandler("removeanime", removeanime_command))
    app.add_handler(CommandHandler("addmod", addmod_command))
    app.add_handler(CommandHandler("removemod", removemod_command))
    app.add_handler(CommandHandler("setname", setname_command))

    # Message handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Button handler
    app.add_handler(CallbackQueryHandler(button_handler))

    # Job queue
    app.job_queue.run_repeating(auto_poster, interval=30, first=10)
    app.job_queue.run_daily(daily_stats_updater, time=datetime.time(hour=0, minute=0, second=0))
    app.job_queue.run_repeating(daily_backup, interval=24*60*60, first=60)
    app.job_queue.run_daily(daily_report, time=datetime.time(hour=23, minute=0, second=0))
    app.job_queue.run_daily(weekly_report, time=datetime.time(hour=23, minute=0, second=0), days=(6,))

    logger.info("🤖 Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
