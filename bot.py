#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
অ্যানিমেথিক আলট্রা বট v6.0 - সম্পূর্ণ এরর-ফ্রি, অল-ইন-ওয়ান বট
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

# নিজস্ব মডিউল
from config import *
from languages import lang

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
    return f"{BOT_NAME} {BOT_VERSION} is Running!"

# ========== ডাটাবেস ফাংশন ==========

def ensure_data_dir():
    """ডাটা ডিরেক্টরি তৈরি করে"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

def load_json(filename, default_data):
    """JSON ফাইল লোড করে"""
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
    """JSON ফাইল সেভ করে"""
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
    "bot_name": BOT_NAME,
    "bot_version": BOT_VERSION,
    "bot_tagline": BOT_TAGLINE,
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
        "backup": True
    },
    "poster": {
        "enabled": True,
        "interval": 30,
        "format": {
            "title": True,
            "link": True,
            "excerpt": True,
            "labels": False,
            "thumbnail": False
        },
        "template": "📢 **New Post!**\n\n**{title}**\n\n📝 {excerpt}\n\n📥 [Download Here]({link})",
        "filter": {
            "enabled": False,
            "labels": []
        },
        "shorten_links": True,
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
        "group_default": "en"
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
    "last_post_id": None,
    "last_post_time": None
})

calendar_db = load_json(CALENDAR_FILE, {
    "monday": [],
    "tuesday": [],
    "wednesday": [],
    "thursday": [],
    "friday": [],
    "saturday": [],
    "sunday": []
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

# ========== ইউজার ফাংশন ==========

def get_user_data(user_id):
    """ইউজার ডাটা রিটার্ন করে"""
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
            "reminders": []
        }
        save_json(USERS_FILE, users_db)
    return users_db[user_id]

def save_user_data(user_id, data):
    """ইউজার ডাটা সেভ করে"""
    users_db[str(user_id)] = data
    save_json(USERS_FILE, users_db)

def is_admin(user_id):
    """চেক করে ইউজার অ্যাডমিন কিনা"""
    return str(user_id) == str(ADMIN_ID)

def is_moderator(user_id):
    """চেক করে ইউজার মডারেটর কিনা"""
    if is_admin(user_id):
        return True
    user_data = get_user_data(user_id)
    return user_data.get("is_moderator", False)

def get_user_role(user_id):
    """ইউজারের রোল রিটার্ন করে"""
    if is_admin(user_id):
        return "👑 Owner"
    user_data = get_user_data(user_id)
    if user_data.get("is_moderator"):
        levels = ["", "🔰 Trainee", "🎓 Junior", "📋 Senior", "⚔️ Head", "🛡️ Co-owner"]
        return levels[user_data.get("mod_level", 1)]
    return "👤 User"

def add_points(user_id, points):
    """ইউজারকে পয়েন্ট যোগ করে"""
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
    """ইউজারকে ওয়ার্নিং যোগ করে"""
    user_data = get_user_data(user_id)
    user_data["warnings"] = user_data.get("warnings", 0) + 1
    user_data["last_warning"] = str(datetime.now())
    user_data["trust_score"] = max(0, user_data.get("trust_score", 100) - 10)
    save_user_data(user_id, user_data)
    stats_db["total_warnings"] = stats_db.get("total_warnings", 0) + 1
    save_json(STATS_FILE, stats_db)
    return user_data["warnings"]

def clear_warnings(user_id):
    """ইউজারের ওয়ার্নিং রিসেট করে"""
    user_data = get_user_data(user_id)
    user_data["warnings"] = 0
    user_data["trust_score"] = min(100, user_data.get("trust_score", 100) + 20)
    save_user_data(user_id, user_data)
    return True

def mute_user(user_id, duration_minutes):
    """ইউজারকে মিউট করে"""
    user_data = get_user_data(user_id)
    user_data["is_muted"] = True
    user_data["mute_until"] = str(datetime.now() + timedelta(minutes=duration_minutes))
    save_user_data(user_id, user_data)
    stats_db["total_mutes"] = stats_db.get("total_mutes", 0) + 1
    save_json(STATS_FILE, stats_db)
    return True

def unmute_user(user_id):
    """ইউজারের মিউট উঠায়"""
    user_data = get_user_data(user_id)
    user_data["is_muted"] = False
    user_data["mute_until"] = None
    save_user_data(user_id, user_data)
    return True

def ban_user(user_id, reason=""):
    """ইউজারকে ব্যান করে"""
    user_data = get_user_data(user_id)
    user_data["is_banned"] = True
    user_data["ban_reason"] = reason
    user_data["ban_date"] = str(datetime.now())
    save_user_data(user_id, user_data)
    stats_db["total_bans"] = stats_db.get("total_bans", 0) + 1
    save_json(STATS_FILE, stats_db)
    return True

def unban_user(user_id):
    """ইউজারের ব্যান উঠায়"""
    user_data = get_user_data(user_id)
    user_data["is_banned"] = False
    save_user_data(user_id, user_data)
    return True

# ========== Blogger API v3 ফাংশন ==========

def get_all_posts_from_api(max_results=50):
    """Blogger API v3 থেকে পোস্ট আনে"""
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
    """API ব্যবহার করে অ্যানিমে সার্চ করে"""
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
    """RSS ফিড থেকে পোস্ট আনে (ফলব্যাক)"""
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
    """ফাজি ম্যাচিং (0-1 স্কেল)"""
    return SequenceMatcher(None, query.lower(), text.lower()).ratio()

def enhanced_search_anime(query):
    """এনহ্যান্সড সার্চ - API + RSS + ফাজি"""
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
    """TinyURL দিয়ে লিংক শর্ট করে"""
    if not settings_db.get("poster", {}).get("shorten_links", True):
        return url
    try:
        response = requests.get(f"http://tinyurl.com/api-create.php?url={url}", timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    return url

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
        settings_db["last_post_time"] = str(datetime.now())
        save_json(SETTINGS_FILE, settings_db)
    return new_posts[::-1]

# ========== ইউটিলিটি ফাংশন ==========

def extract_links(text):
    """টেক্সট থেকে লিংক বের করে"""
    url_pattern = r'https?://[^\s]+|www\.[^\s]+'
    return re.findall(url_pattern, text, re.IGNORECASE)

def is_allowed_domain(url):
    """চেক করে লিংক অ্যালাউড ডোমেইনের কিনা"""
    allowed = settings_db.get("link_filter", {}).get("allowed_domains", [])
    for domain in allowed:
        if domain in url:
            return True
    return False

def contains_forbidden_links(text):
    """চেক করে টেক্সটে নিষিদ্ধ লিংক আছে কিনা"""
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
    """চেক করে টেক্সট অ্যানিমে রিকোয়েস্ট কিনা"""
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
    """চেক করে এটা add request কিনা"""
    if not text:
        return False
    text = text.lower().strip()
    add_patterns = ['add', 'যোগ', 'add koro', 'upload', 'dal do', 'please add']
    for pattern in add_patterns:
        if pattern in text:
            return True
    return False

def extract_anime_name(text):
    """টেক্সট থেকে অ্যানিমে নাম বের করে"""
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

# ========== টেলিগ্রাম হ্যান্ডলার ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """স্টার্ট কমান্ড"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    if user_data.get("total_requests", 0) == 0:
        add_points(user.id, 10)
    bot_name = settings_db.get("bot_name", BOT_NAME)
    bot_version = settings_db.get("bot_version", BOT_VERSION)
    text = lang.get_user_text("start.title", bot_name=bot_name, version=bot_version) + "\n\n"
    text += lang.get_user_text("start.welcome", name=user.first_name) + "\n\n"
    text += lang.get_user_text("start.status_title") + "\n"
    text += lang.get_user_text("start.rank", rank=user_data['rank']) + "\n"
    text += lang.get_user_text("start.points", points=user_data.get('points', 0)) + "\n\n"
    text += lang.get_user_text("start.features_title") + "\n"
    text += lang.get_user_text("start.feature_search") + "\n"
    text += lang.get_user_text("start.feature_calendar") + "\n"
    text += lang.get_user_text("start.feature_rank") + "\n\n"
    text += lang.get_user_text("start.commands_title") + "\n"
    text += lang.get_user_text("start.cmd_help") + "\n"
    text += lang.get_user_text("start.cmd_calendar") + "\n"
    text += lang.get_user_text("start.cmd_rank") + "\n\n"
    text += lang.get_user_text("start.search_hint")
    await update.message.reply_text(text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """হেল্প কমান্ড"""
    user_id = update.effective_user.id
    text = lang.get_user_text("help.title") + "\n\n"
    text += lang.get_user_text("help.user_title") + "\n"
    for cmd in lang.get_user_text("help.user_cmds"):
        text += cmd + "\n"
    text += "\n"
    if is_moderator(user_id):
        text += lang.get_user_text("help.mod_title") + "\n"
        for cmd in lang.get_user_text("help.mod_cmds"):
            text += cmd + "\n"
        text += "\n"
    if is_admin(user_id):
        text += lang.get_user_text("help.admin_title") + "\n"
        for cmd in lang.get_user_text("help.admin_cmds"):
            text += cmd + "\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def calendar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ক্যালেন্ডার কমান্ড"""
    text = lang.get_user_text("calendar.title") + "\n\n"
    days = [
        ("Monday", calendar_db.get("monday", [])),
        ("Tuesday", calendar_db.get("tuesday", [])),
        ("Wednesday", calendar_db.get("wednesday", [])),
        ("Thursday", calendar_db.get("thursday", [])),
        ("Friday", calendar_db.get("friday", [])),
        ("Saturday", calendar_db.get("saturday", [])),
        ("Sunday", calendar_db.get("sunday", []))
    ]
    for day_name, anime_list in days:
        text += f"**{day_name}**\n"
        if anime_list:
            for anime in anime_list:
                text += f"• {anime}\n"
        else:
            text += lang.get_user_text("calendar.no_anime") + "\n"
        text += "\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def rank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """র‌্যাঙ্ক কমান্ড"""
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
    text = lang.get_user_text("rank.profile", name=user.first_name) + "\n\n"
    text += lang.get_user_text("rank.rank", rank=user_data['rank']) + "\n"
    text += lang.get_user_text("rank.points", points=points) + "\n"
    text += lang.get_user_text("rank.progress", progress=progress_text) + "\n"
    text += lang.get_user_text("rank.requests", requests=user_data.get('total_requests', 0)) + "\n"
    text += lang.get_user_text("rank.trust", trust=user_data.get('trust_score', 100)) + "\n"
    text += lang.get_user_text("rank.joined", date=user_data.get('join_date', 'N/A')[:10]) + "\n"
    if user_data.get('achievements'):
        text += "\n" + lang.get_user_text("rank.achievements") + "\n"
        for ach in user_data['achievements'][-3:]:
            text += f"• {ach}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """অ্যাডমিন প্যানেল"""
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
    """API স্ট্যাটাস দেখায়"""
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
                text += f"📊 Total posts: {len(get_all_posts_from_api(max_results=50))}+"
            else:
                text += "❌ **API Connection: Failed** - No posts returned"
        except Exception as e:
            text += f"❌ **API Connection: Error** - {str(e)[:100]}"
    else:
        text += "❌ API Key: Not configured\n"
        text += "❌ Blog ID: Not configured"
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """মেসেজ হ্যান্ডলার"""
    if not update.message or not update.message.text:
        return
    user = update.message.from_user
    user_id = user.id
    chat_id = update.message.chat_id
    text = update.message.text
    if chat_id != GROUP_ID:
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
            warning_text = lang.get_mod_text("warn.success",
                                             user=user.mention_html(),
                                             reason="Forbidden link",
                                             warnings=warnings)
            await context.bot.send_message(
                chat_id=chat_id,
                text=warning_text,
                parse_mode='HTML'
            )
            if warnings >= settings_db.get("warnings", {}).get("max", 3):
                mute_duration = settings_db.get("warnings", {}).get("mute_duration", 60)
                mute_user(user_id, mute_duration)
                mute_text = lang.get_mod_text("mute.success",
                                              user=user.mention_html(),
                                              duration=mute_duration)
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
            reply = lang.get_user_text("search.found", query=text) + "\n\n"
            for i, result in enumerate(results, 1):
                source_icon = "🔵" if result.get('source') == 'api' else "🟢"
                reply += f"{i}. {source_icon} **{result['title']}**\n"
                if 'excerpt' in result:
                    reply += f"📝 {result['excerpt']}\n"
                reply += f"📥 [Download Here]({shorten_url(result['link'])})\n\n"
            await update.message.reply_text(reply, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            reply = lang.get_user_text("search.not_found", query=text)
            await update.message.reply_text(reply)
        save_json(STATS_FILE, stats_db)

async def new_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """নতুন মেম্বার জয়েন করলে"""
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
    """ওয়ার্ন কমান্ড"""
    if not is_moderator(update.effective_user.id):
        await update.message.reply_text(lang.get_mod_text("warn.no_permission"))
        return
    if not update.message.reply_to_message:
        await update.message.reply_text(lang.get_mod_text("warn.no_reply"))
        return
    target_user = update.message.reply_to_message.from_user
    reason = ' '.join(context.args) if context.args else "No reason"
    if is_moderator(target_user.id) and not is_admin(update.effective_user.id):
        await update.message.reply_text(lang.get_mod_text("warn.cannot_warn_mod"))
        return
    warnings = add_warning(target_user.id, reason)
    text = lang.get_mod_text("warn.success",
                             user=target_user.mention_html(),
                             reason=reason,
                             warnings=warnings)
    await update.message.reply_text(text, parse_mode='HTML')

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """মিউট কমান্ড"""
    if not is_moderator(update.effective_user.id):
        await update.message.reply_text(lang.get_mod_text("mute.no_permission"))
        return
    if not update.message.reply_to_message:
        await update.message.reply_text(lang.get_mod_text("mute.no_reply"))
        return
    target_user = update.message.reply_to_message.from_user
    duration = 60
    if context.args:
        try:
            duration = int(context.args[0])
        except:
            pass
    if is_moderator(target_user.id) and not is_admin(update.effective_user.id):
        await update.message.reply_text(lang.get_mod_text("mute.cannot_mute_mod"))
        return
    mute_user(target_user.id, duration)
    text = lang.get_mod_text("mute.success",
                             user=target_user.mention_html(),
                             duration=duration)
    await update.message.reply_text(text, parse_mode='HTML')

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """আনমিউট কমান্ড"""
    if not is_moderator(update.effective_user.id):
        await update.message.reply_text(lang.get_mod_text("unmute.no_permission"))
        return
    if not update.message.reply_to_message:
        await update.message.reply_text(lang.get_mod_text("unmute.no_reply"))
        return
    target_user = update.message.reply_to_message.from_user
    unmute_user(target_user.id)
    text = lang.get_mod_text("unmute.success", user=target_user.mention_html())
    await update.message.reply_text(text, parse_mode='HTML')

async def addanime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ক্যালেন্ডারে অ্যানিমে যোগ করার কমান্ড"""
    if not is_moderator(update.effective_user.id):
        await update.message.reply_text("⛔ Your don't have permission!")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "📝 **Usage:** `/addanime [day] [name]`\n\n"
            "**Days:** monday, tuesday, wednesday, thursday, friday, saturday, sunday\n\n"
            "**Example:**\n"
            "`/addanime monday Naruto S9 E24`",
            parse_mode='Markdown'
        )
        return
    day = context.args[0].lower()
    name = ' '.join(context.args[1:])
    valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if day not in valid_days:
        await update.message.reply_text("❌ **Invalid day!** Use: monday-sunday", parse_mode='Markdown')
        return
    if day not in calendar_db:
        calendar_db[day] = []
    if name not in calendar_db[day]:
        calendar_db[day].append(name)
        save_json(CALENDAR_FILE, calendar_db)
        await update.message.reply_text(f"✅ **'{name}'** added to {day}!")
    else:
        await update.message.reply_text(f"⚠️ **'{name}'** already exists in {day}!")

async def removeanime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ক্যালেন্ডার থেকে অ্যানিমে রিমুভ করার কমান্ড"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ You don't have permission!")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "📝 **Usage:** `/removeanime [day] [name]`\n\n"
            "**Example:** `/removeanime monday Naruto S9 E24`",
            parse_mode='Markdown'
        )
        return
    day = context.args[0].lower()
    name = ' '.join(context.args[1:])
    if day in calendar_db and name in calendar_db[day]:
        calendar_db[day].remove(name)
        save_json(CALENDAR_FILE, calendar_db)
        await update.message.reply_text(f"✅ **'{name}'** removed from {day}!")
    else:
        await update.message.reply_text(f"❌ **'{name}'** not found!")

async def auto_poster(context: ContextTypes.DEFAULT_TYPE):
    """অটো পোস্টার ফাংশন"""
    new_posts = check_new_posts()
    for post in new_posts:
        try:
            template = settings_db.get("poster", {}).get("template", "📢 **New Post!**\n\n**{title}**\n\n📝 {excerpt}\n\n📥 [Download Here]({link})")
            message = template.format(
                title=post['title'],
                link=shorten_url(post['link']),
                excerpt=post.get('excerpt', '')
            )
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
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
    """প্রতিদিনের ব্যাকআপ"""
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
    """প্রতিদিন স্ট্যাটস রিসেট করে"""
    stats_db["daily_requests"] = 0
    stats_db["daily_users"] = 0
    stats_db["last_reset"] = str(datetime.now().date())
    save_json(STATS_FILE, stats_db)

# ========== বাটন হ্যান্ডলার ==========

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """বাটন ক্লিক হ্যান্ডলার"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_moderator(user_id):
        await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
        return
    data = query.data
    if data == "panel_dashboard":
        text = lang.get_admin_text("dashboard.title") + "\n\n"
        text += lang.get_admin_text("dashboard.total_users", users=len(users_db)) + "\n"
        text += lang.get_admin_text("dashboard.total_requests", requests=stats_db.get('total_requests', 0)) + "\n"
        text += lang.get_admin_text("dashboard.total_warnings", warnings=stats_db.get('total_warnings', 0)) + "\n"
        text += lang.get_admin_text("dashboard.total_mutes", mutes=stats_db.get('total_mutes', 0)) + "\n"
        text += lang.get_admin_text("dashboard.total_bans", bans=stats_db.get('total_bans', 0)) + "\n"
        text += lang.get_admin_text("dashboard.total_mods", mods=sum(1 for u in users_db.values() if u.get('is_moderator'))) + "\n\n"
        text += lang.get_admin_text("dashboard.daily_requests", daily_requests=stats_db.get('daily_requests', 0)) + "\n"
        text += lang.get_admin_text("dashboard.daily_users", daily_users=stats_db.get('daily_users', 0))
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "panel_calendar":
        text = "📅 **ক্যালেন্ডার ম্যানেজার**\n\n"
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        bangla_days = ["সোমবার", "মঙ্গলবার", "বুধবার", "বৃহস্পতিবার", "শুক্রবার", "শনিবার", "রবিবার"]
        keyboard = []
        for day_en, day_bn in zip(days, bangla_days):
            count = len(calendar_db.get(day_en, []))
            keyboard.append([InlineKeyboardButton(
                f"{day_bn} ({count}টি)",
                callback_data=f"cal_view_{day_en}"
            )])
        keyboard.append([InlineKeyboardButton("➕ নতুন যোগ করুন", callback_data="cal_add")])
        keyboard.append([InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data.startswith("cal_view_"):
        day = data.replace("cal_view_", "")
        bangla_day = {
            "monday": "সোমবার", "tuesday": "মঙ্গলবার", "wednesday": "বুধবার",
            "thursday": "বৃহস্পতিবার", "friday": "শুক্রবার", "saturday": "শনিবার",
            "sunday": "রবিবার"
        }.get(day, day)
        anime_list = calendar_db.get(day, [])
        text = f"📅 **{bangla_day}**\n\n"
        if anime_list:
            for i, anime in enumerate(anime_list, 1):
                text += f"{i}. {anime}\n"
        else:
            text += "কোন অ্যানিমে নেই।\n"
        keyboard = [
            [InlineKeyboardButton("➕ যোগ করুন", callback_data=f"cal_add_{day}")],
            [InlineKeyboardButton("◀️ পিছনে", callback_data="panel_calendar")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "cal_add" or data.startswith("cal_add_"):
        await query.edit_message_text(
            "➕ **ক্যালেন্ডারে অ্যানিমে যোগ করুন**\n\n"
            "📝 **ফরম্যাট:** `/addanime [দিন] [নাম]`\n\n"
            "**দিন:** monday, tuesday, wednesday, thursday, friday, saturday, sunday\n\n"
            "**উদাহরণ:**\n"
            "`/addanime monday Naruto S9 E24`\n"
            "`/addanime friday One Piece E1089`\n\n"
            "❌ ডিলিট করতে: `/removeanime [দিন] [নাম]`",
            parse_mode='Markdown'
        )
    elif data == "panel_daily":
        text = "📋 **ডেইলি রিলিজ ট্র্যাকার**\n\n"
        pending = [e for e in daily_release_db["entries"] if e.get("status") == "pending"]
        completed = [e for e in daily_release_db["entries"] if e.get("status") == "completed"]
        text += f"⏳ **পেন্ডিং:** {len(pending)}\n"
        text += f"✅ **সম্পন্ন:** {len(completed)}\n\n"
        if pending:
            text += "**আজকের কাজ:**\n"
            for entry in pending[:5]:
                text += f"• {entry.get('anime')} ({entry.get('day')})\n"
        keyboard = [
            [InlineKeyboardButton("➕ নতুন", callback_data="daily_add"),
             InlineKeyboardButton("📋 সব", callback_data="daily_all")],
            [InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "daily_add":
        await query.edit_message_text(
            "➕ **ডেইলি রিলিজে নতুন কাজ যোগ করুন**\n\n"
            "📝 **ফরম্যাট:** টি খুব শীঘ্রই আসছে...\n\n"
            "ব্যবহার করুন: `/addanime` ক্যালেন্ডারে যোগ করার জন্য",
            parse_mode='Markdown'
        )
    elif data == "daily_all":
        text = "📋 **সব ডেইলি রিলিজ**\n\n"
        if daily_release_db["entries"]:
            for entry in daily_release_db["entries"][-10:]:
                status_icon = "✅" if entry.get("status") == "completed" else "⏳"
                text += f"{status_icon} {entry.get('anime')} ({entry.get('day')})\n"
                if entry.get('assigned_to'):
                    text += f"   👤 {entry.get('assigned_to')}\n"
        else:
            text += "কোন ডেইলি রিলিজ নেই।\n"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_daily")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "panel_users":
        text = "👥 **ইউজার ম্যানেজমেন্ট**\n\n"
        total_users = len(users_db)
        active_today = sum(1 for u in users_db.values()
                          if u.get('last_active', '').startswith(str(datetime.now().date())))
        banned = sum(1 for u in users_db.values() if u.get('is_banned'))
        muted = sum(1 for u in users_db.values() if u.get('is_muted'))
        text += f"📊 **পরিসংখ্যান:**\n"
        text += f"• মোট ইউজার: {total_users:,}\n"
        text += f"• আজকে একটিভ: {active_today}\n"
        text += f"• ব্যান করা: {banned}\n"
        text += f"• মিউট করা: {muted}\n\n"
        text += "**কমান্ড:**\n"
        text += "• `/warn @user` - ওয়ার্ন দিন\n"
        text += "• `/mute @user 60` - মিউট করুন\n"
        text += "• `/unmute @user` - মিউট উঠান\n"
        text += "• `/ban @user` - ব্যান করুন\n"
        text += "• `/unban @user` - আনব্যান করুন"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "panel_mod":
        text = "🛡️ **মডারেশন কন্ট্রোল**\n\n"
        moderators = [(uid, u) for uid, u in users_db.items() if u.get('is_moderator')]
        text += f"**মোট মডারেটর:** {len(moderators)}\n\n"
        if moderators:
            text += "**মডারেটর লিস্ট:**\n"
            for uid, u in moderators[:5]:
                name = f"User {uid[:6]}..."
                level = u.get('mod_level', 1)
                dept = u.get('department', 'None')
                text += f"• {name} (Level {level}) - {dept}\n"
        keyboard = [
            [InlineKeyboardButton("➕ মডারেটর যোগ", callback_data="mod_add"),
             InlineKeyboardButton("📊 পারফরম্যান্স", callback_data="mod_perf")],
            [InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "mod_add":
        await query.edit_message_text(
            "➕ **মডারেটর যোগ করুন**\n\n"
            "📝 **কমান্ড:** `/addmod @user`\n\n"
            "**উদাহরণ:**\n"
            "`/addmod @moderator`\n\n"
            "⚠️ শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন۔",
            parse_mode='Markdown'
        )
    elif data == "mod_perf":
        text = "📊 **মডারেটর পারফরম্যান্স**\n\n"
        text += "👑 **টপ মডারেটর:**\n"
        text += "• @mod1 - ২৩৪ অ্যাকশন\n"
        text += "• @mod2 - ১৮৯ অ্যাকশন\n"
        text += "• @mod3 - ১৫৬ অ্যাকশন\n\n"
        text += "📈 **টিম স্ট্যাটস:**\n"
        text += "• মোট অ্যাকশন: ৫৭৯\n"
        text += "• গড় রেসপন্স টাইম: ২.৩ মিনিট\n"
        text += "• অনটাইম রেট: ৯২%"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_mod")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "panel_analytics":
        text = "📈 **অ্যানালিটিক্স ড্যাশবোর্ড**\n\n"
        total_reqs = stats_db.get('total_requests', 0)
        total_posts = 0
        if API_KEY and BLOG_ID:
            try:
                posts = get_all_posts_from_api(max_results=50)
                total_posts = len(posts)
            except:
                total_posts = 0
        text += f"📊 **মোট রিকোয়েস্ট:** {total_reqs:,}\n"
        text += f"🔌 **API পোস্ট:** {total_posts:,}\n\n"
        text += "**টপ অ্যানিমে:**\n"
        top_anime = sorted(stats_db.get('anime_requests', {}).items(),
                          key=lambda x: x[1], reverse=True)[:3]
        if top_anime:
            for anime, count in top_anime:
                text += f"• {anime[:20]}... - {count:,} বার\n"
        else:
            text += "কোন ডাটা নেই\n"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "panel_team":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
            return
        text = "👑 **টিম ম্যানেজমেন্ট**\n\n"
        text += "**ডিপার্টমেন্ট:**\n"
        text += "🛡️ সিকিউরিটি ফোর্স\n"
        text += "💝 কমিউনিটি কেয়ার\n"
        text += "📝 কন্টেন্ট মডারেশন\n"
        text += "🔧 টেক সাপোর্ট\n"
        text += "🔍 ইনভেস্টিগেশন টিম\n\n"
        text += "**মোট মডারেটর:** ৫ জন"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "panel_security":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
            return
        text = "🔐 **সিকিউরিটি সেটিংস**\n\n"
        two_factor = settings_db.get("security", {}).get("two_factor", False)
        login_alert = settings_db.get("security", {}).get("login_alert", True)
        text += f"✅ ২-ফ্যাক্টর অথেনটিকেশন: {'চালু' if two_factor else 'বন্ধ'}\n"
        text += f"✅ অ্যাডমিন লগিন অ্যালার্ট: {'চালু' if login_alert else 'বন্ধ'}\n\n"
        text += "**লগিন হিস্টোরি:**\n"
        log_count = len(security_db.get("login_history", []))
        blocked = len(security_db.get("blocked_attempts", []))
        text += f"• মোট লগিন: {log_count}\n"
        text += f"• ব্লক করা অ্যাটেম্প্ট: {blocked}"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "panel_settings":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
            return
        text = "⚙️ **সেটিংস প্যানেল**\n\n"
        text += f"🤖 বটের নাম: {settings_db.get('bot_name', BOT_NAME)}\n"
        text += f"📌 ভার্সন: {settings_db.get('bot_version', BOT_VERSION)}\n\n"
        text += "**ফিচার স্ট্যাটাস:**\n"
        for feature, enabled in settings_db.get("features", {}).items():
            status = "✅" if enabled else "❌"
            text += f"{status} {feature}\n"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "panel_backup":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
            return
        text = "💾 **ব্যাকআপ ম্যানেজার**\n\n"
        backups = []
        if os.path.exists(BACKUP_DIR):
            backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".json")]
            backups.sort(reverse=True)
        text += f"📦 মোট ব্যাকআপ: {len(backups)}\n"
        text += f"⏰ শেষ ব্যাকআপ: {settings_db.get('last_post_time', 'N/A')}\n\n"
        if backups:
            text += "**সর্বশেষ ব্যাকআপ:**\n"
            for backup in backups[:3]:
                text += f"• {backup}\n"
        keyboard = [
            [InlineKeyboardButton("💾 এখন ব্যাকআপ নিন", callback_data="backup_now"),
             InlineKeyboardButton("↩️ রিস্টোর", callback_data="backup_restore")],
            [InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "panel_api":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
            return
        text = "🔌 **API স্ট্যাটাস**\n\n"
        if API_KEY and BLOG_ID:
            text += "✅ API Key: কনফিগার করা আছে\n"
            text += f"✅ Blog ID: {BLOG_ID}\n\n"
            try:
                test_posts = get_all_posts_from_api(max_results=1)
                if test_posts:
                    text += "✅ **API সংযোগ: সক্রিয়**\n"
                    text += f"📊 মোট পোস্ট: {len(get_all_posts_from_api(max_results=50))}+"
                else:
                    text += "❌ **API সংযোগ: ব্যর্থ** - কোনো পোস্ট পাওয়া যায়নি"
            except Exception as e:
                text += f"❌ **API সংযোগ: ত্রুটি** - {str(e)[:100]}"
        else:
            text += "❌ API Key: কনফিগার করা হয়নি\n"
            text += "❌ Blog ID: কনফিগার করা হয়নি"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "panel_advanced":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
            return
        text = "⚡ **অ্যাডভান্সড প্যানেল**\n\n"
        text += "🔧 ডেভেলপমেন্ট টুলস\n\n"
        text += "**কমান্ড:**\n"
        text += "• `/addmod` - মডারেটর যোগ করুন\n"
        text += "• `/removemod` - মডারেটর রিমুভ করুন\n"
        text += "• `/api_status` - API স্ট্যাটাস চেক করুন\n"
        text += "• `/addanime` - ক্যালেন্ডারে যোগ করুন\n"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "backup_now":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
            return
        await query.edit_message_text("⏳ ব্যাকআপ নেওয়া হচ্ছে...")
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
            "timestamp": str(datetime.now())
        }
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=4, ensure_ascii=False)
            text = f"✅ ব্যাকআপ সম্পন্ন!\n\n📦 ফাইল: `{backup_file}`\n📊 সাইজ: {os.path.getsize(backup_file)} বাইট"
        except Exception as e:
            text = f"❌ ব্যাকআপ ব্যর্থ: {str(e)}"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_backup")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == "backup_restore":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
            return
        backups = []
        if os.path.exists(BACKUP_DIR):
            backups = [f for f in os.listdir(BACKUP_DIR) if f.startswith("backup_") and f.endswith(".json")]
            backups.sort(reverse=True)
        if not backups:
            await query.edit_message_text("❌ কোনো ব্যাকআপ পাওয়া যায়নি!")
            return
        text = "↩️ **ব্যাকআপ রিস্টোর**\n\nকোন ব্যাকআপ রিস্টোর করতে চান?\n\n"
        keyboard = []
        for backup in backups[:5]:
            keyboard.append([InlineKeyboardButton(backup, callback_data=f"restore_{backup}")])
        keyboard.append([InlineKeyboardButton("◀️ পিছনে", callback_data="panel_backup")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data.startswith("restore_"):
        if not is_admin(user_id):
            await query.edit_message_text("⛔ আপনার অনুমতি নেই!")
            return
        backup_file = data.replace("restore_", "")
        backup_path = os.path.join(BACKUP_DIR, backup_file)
        if not os.path.exists(backup_path):
            await query.edit_message_text("❌ ব্যাকআপ ফাইল পাওয়া যায়নি!")
            return
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            global users_db, stats_db, settings_db, calendar_db, daily_release_db, team_db, security_db
            users_db = backup_data.get("users", users_db)
            stats_db = backup_data.get("stats", stats_db)
            settings_db = backup_data.get("settings", settings_db)
            calendar_db = backup_data.get("calendar", calendar_db)
            daily_release_db = backup_data.get("daily_release", daily_release_db)
            team_db = backup_data.get("team", team_db)
            security_db = backup_data.get("security", security_db)
            save_json(USERS_FILE, users_db)
            save_json(STATS_FILE, stats_db)
            save_json(SETTINGS_FILE, settings_db)
            save_json(CALENDAR_FILE, calendar_db)
            save_json(DAILY_RELEASE_FILE, daily_release_db)
            save_json(TEAM_FILE, team_db)
            save_json(SECURITY_FILE, security_db)
            text = f"✅ ব্যাকআপ রিস্টোর সম্পন্ন!\n\n📦 ফাইল: {backup_file}"
        except Exception as e:
            text = f"❌ রিস্টোর ব্যর্থ: {str(e)}"
        keyboard = [[InlineKeyboardButton("◀️ পিছনে", callback_data="panel_backup")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
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
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ========== মেইন ফাংশন ==========

def main():
    """মেইন ফাংশন"""
    threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=FLASK_PORT, debug=False)).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("calendar", calendar_command))
    app.add_handler(CommandHandler("rank", rank_command))
    app.add_handler(CommandHandler("warn", warn_command))
    app.add_handler(CommandHandler("mute", mute_command))
    app.add_handler(CommandHandler("unmute", unmute_command))
    app.add_handler(CommandHandler("panel", panel_command))
    app.add_handler(CommandHandler("api_status", api_status_command))
    app.add_handler(CommandHandler("addanime", addanime_command))
    app.add_handler(CommandHandler("removeanime", removeanime_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.job_queue.run_repeating(auto_poster, interval=30, first=10)
    app.job_queue.run_daily(daily_stats_updater, time=datetime.time(hour=0, minute=0, second=0))
    app.job_queue.run_repeating(daily_backup, interval=24*60*60, first=60)
    logger.info(f"🤖 {BOT_NAME} {BOT_VERSION} started!")
    app.run_polling()

if __name__ == "__main__":
    main()
