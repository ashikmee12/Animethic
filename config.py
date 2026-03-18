#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
অ্যানিমেথিক আলট্রা বট v6.0 - কনফিগারেশন ফাইল
"""

import os

# ========== টেলিগ্রাম কনফিগ ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8763338417:AAHCzL74xO3YxG8ktSrGar3aUF7OzklS0Ko')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '7406197326'))
GROUP_ID = int(os.environ.get('GROUP_ID', '-1002248871056'))
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', '-1002225247609'))

# ========== বট কনফিগ ==========
BOT_NAME = os.environ.get('BOT_NAME', '🤖 অ্যানিমেথিক আলট্রা বট')
BOT_VERSION = os.environ.get('BOT_VERSION', 'v6.0')
BOT_TAGLINE = os.environ.get('BOT_TAGLINE', 'আপনার অ্যানিমে সহায়ক')

# ========== ওয়েবসাইট কনফিগ ==========
WEBSITE_URL = os.environ.get('WEBSITE_URL', 'https://www.animethic.in')
RSS_FEED_URL = os.environ.get('RSS_FEED_URL', 'https://www.animethic.in/feeds/posts/default')

# ========== Blogger API v3 কনফিগ ==========
BLOG_ID = os.environ.get('BLOG_ID', '6445429841925204092')
API_KEY = os.environ.get('API_KEY', 'AIzaSyBd-2MBVvEpJMH1J8xfhT8uzDbxARaDc6Q')

# ========== ফ্লাস্ক কনফিগ ==========
FLASK_PORT = int(os.environ.get('FLASK_PORT', 8081))

# ========== ডাটাবেস ফাইল পাথ ==========
DATA_DIR = 'data'
USERS_FILE = f'{DATA_DIR}/users.json'
STATS_FILE = f'{DATA_DIR}/stats.json'
SETTINGS_FILE = f'{DATA_DIR}/settings.json'
CALENDAR_FILE = f'{DATA_DIR}/calendar.json'
DAILY_RELEASE_FILE = f'{DATA_DIR}/daily_release.json'
TEAM_FILE = f'{DATA_DIR}/team.json'
SECURITY_FILE = f'{DATA_DIR}/security.json'
BACKUP_DIR = f'{DATA_DIR}/backup'
