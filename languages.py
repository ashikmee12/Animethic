#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
অ্যানিমেথিক আলট্রা বট v6.0 - ল্যাঙ্গুয়েজ ম্যানেজার
"""

import json
import os

# ========== ল্যাঙ্গুয়েজ ডাটা ==========

# ইউজার ল্যাঙ্গুয়েজ (ইংরেজি)
USER_EN = {
    "start": {
        "title": "🤖 {bot_name} {version}",
        "welcome": "👋 Welcome {name}!",
        "status_title": "Your Status:",
        "rank": "🏆 Rank: {rank}",
        "points": "⭐ Points: {points}",
        "features_title": "✨ Special Features:",
        "feature_search": "• AI-Powered Anime Search",
        "feature_calendar": "• Weekly Anime Calendar",
        "feature_rank": "• Rank & Points System",
        "commands_title": "📋 Commands:",
        "cmd_help": "/help - Show help",
        "cmd_calendar": "/calendar - View calendar",
        "cmd_rank": "/rank - Your profile",
        "search_hint": "🔍 **To search:** Just type anime name (e.g., Naruto Season 9)"
    },
    "help": {
        "title": "📚 Help Guide",
        "user_title": "👤 User Commands:",
        "user_cmds": [
            "/start - Start the bot",
            "/help - Show this help",
            "/calendar - View anime calendar",
            "/rank - Your profile"
        ],
        "mod_title": "🛡️ Moderator Commands:",
        "mod_cmds": [
            "/warn @user - Warn user",
            "/mute @user [minutes] - Mute user",
            "/unmute @user - Unmute user"
        ],
        "admin_title": "👑 Admin Commands:",
        "admin_cmds": [
            "/panel - Admin panel",
            "/stats - View statistics",
            "/api_status - Check API status"
        ]
    },
    "calendar": {
        "title": "📅 Weekly Anime Calendar",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "no_anime": "• No anime scheduled",
        "add": "➕ Add",
        "back": "◀️ Back"
    },
    "rank": {
        "profile": "🏆 **{name}'s Profile**",
        "rank": "📊 Rank: {rank}",
        "points": "⭐ Points: {points:,}",
        "progress": "📈 Progress: {progress}",
        "requests": "📝 Total Requests: {requests:,}",
        "trust": "🤝 Trust Score: {trust}%",
        "joined": "📅 Joined: {date}",
        "achievements": "🏅 Achievements:"
    },
    "search": {
        "found": "🔍 **Found for '{query}':**",
        "not_found": "🔍 '{query}' not found.\n\n📞 Contact: @animethic_admin_bot",
        "source_api": "🔵",
        "source_rss": "🟢"
    }
}

# মডারেটর ল্যাঙ্গুয়েজ (বাংলা)
MOD_BN = {
    "warn": {
        "success": "⚠️ {user} কে ওয়ার্ন দেওয়া হয়েছে!\nকারণ: {reason}\nমোট ওয়ার্নিং: {warnings}",
        "no_permission": "⛔ আপনার অনুমতি নেই!",
        "no_reply": "⚠️ কোন মেসেজের রিপ্লাই হিসেবে /warn ব্যবহার করুন",
        "cannot_warn_mod": "⚠️ আপনি অন্য মডারেটরকে ওয়ার্ন দিতে পারবেন না!"
    },
    "mute": {
        "success": "🔇 {user} {duration} মিনিটের জন্য মিউট করা হয়েছে!",
        "no_permission": "⛔ আপনার অনুমতি নেই!",
        "no_reply": "⚠️ কোন মেসেজের রিপ্লাই হিসেবে /mute ব্যবহার করুন",
        "cannot_mute_mod": "⚠️ আপনি অন্য মডারেটরকে মিউট করতে পারবেন না!"
    },
    "unmute": {
        "success": "✅ {user} এর মিউট উঠানো হয়েছে!",
        "no_permission": "⛔ আপনার অনুমতি নেই!",
        "no_reply": "⚠️ কোন মেসেজের রিপ্লাই হিসেবে /unmute ব্যবহার করুন"
    }
}

# অ্যাডমিন প্যানেল (বাংলা)
ADMIN_BN = {
    "panel": {
        "title": "🔐 **কন্ট্রোল প্যানেল**",
        "role": "আপনার রোল: {role}",
        "buttons": {
            "dashboard": "📊 ড্যাশবোর্ড",
            "calendar": "📅 ক্যালেন্ডার",
            "daily": "📋 ডেইলি রিলিজ",
            "users": "👥 ইউজার",
            "mod": "🛡️ মডারেশন",
            "analytics": "📈 অ্যানালিটিক্স",
            "team": "👑 টিম ম্যানেজ",
            "security": "🔐 সিকিউরিটি",
            "settings": "⚙️ সেটিংস",
            "backup": "💾 ব্যাকআপ",
            "api": "🔌 API স্ট্যাটাস",
            "advanced": "⚡ অ্যাডভান্সড",
            "back": "◀️ পিছনে"
        }
    },
    "dashboard": {
        "title": "📊 **ড্যাশবোর্ড**",
        "total_users": "👥 মোট ইউজার: {users:,}",
        "total_requests": "📝 মোট রিকোয়েস্ট: {requests:,}",
        "total_warnings": "⚠️ মোট ওয়ার্নিং: {warnings:,}",
        "total_mutes": "🔇 মোট মিউট: {mutes:,}",
        "total_bans": "🚫 মোট ব্যান: {bans:,}",
        "total_mods": "🛡️ মোট মডারেটর: {mods}",
        "daily_requests": "📈 আজকের রিকোয়েস্ট: {daily_requests}",
        "daily_users": "👤 আজকের ইউজার: {daily_users}"
    }
}

# ========== ল্যাঙ্গুয়েজ ম্যানেজার ক্লাস ==========

class LanguageManager:
    """ল্যাঙ্গুয়েজ ম্যানেজার"""
    
    def __init__(self):
        self.user_lang = USER_EN
        self.mod_lang = MOD_BN
        self.admin_lang = ADMIN_BN
    
    def get_user_text(self, key, **kwargs):
        """ইউজারের জন্য টেক্সট রিটার্ন করে (ইংরেজি)"""
        keys = key.split('.')
        data = self.user_lang
        for k in keys:
            data = data.get(k, {})
        if isinstance(data, str):
            return data.format(**kwargs)
        return key
    
    def get_mod_text(self, key, **kwargs):
        """মডারেটরের জন্য টেক্সট রিটার্ন করে (বাংলা)"""
        keys = key.split('.')
        data = self.mod_lang
        for k in keys:
            data = data.get(k, {})
        if isinstance(data, str):
            return data.format(**kwargs)
        return key
    
    def get_admin_text(self, key, **kwargs):
        """অ্যাডমিনের জন্য টেক্সট রিটার্ন করে (বাংলা)"""
        keys = key.split('.')
        data = self.admin_lang
        for k in keys:
            data = data.get(k, {})
        if isinstance(data, str):
            return data.format(**kwargs)
        return key

# গ্লোবাল ল্যাঙ্গুয়েজ ম্যানেজার
lang = LanguageManager()
