#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Telegram Coding AI Bot
Developer: Ziaul Islam
Website: https://ziaulislam.top

Features:
- Gemini API integration
- JSON database for users & chats
- Admin panel (Flask web)
- Persistent conversation memory
- Commands: /start, /help, /ai, /code, /clear, /stats
- Bengali + English support
"""

import os
import json
import logging
import asyncio
import threading
from datetime import datetime
from functools import wraps

import requests
from flask import Flask, render_template, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ==========================================================
# CONFIGURATION
# ==========================================================

# Telegram Bot Token
TELEGRAM_TOKEN = "8930444022:AAGWUKNBRwch99iLOAknQidLbKfHFWAE444"

# Gemini API Key
GEMINI_API_KEY = "AIzaSyBcLfjPldRjpdvMafb8PRbMGGsW8D4b_Gw"

# Developer Info
DEVELOPER_NAME = "Ziaul Islam"
DEVELOPER_WEBSITE = "https://ziaulislam.top"

# Model name
MODEL_NAME = "gemini-1.5-flash"

# JSON Database files
USERS_DB = "telegram_users.json"
CHATS_DB = "telegram_chats.json"
SETTINGS_DB = "telegram_settings.json"

# Conversation memory for each user
user_memories = {}

# Max history per user
MAX_HISTORY = 20

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================================
# FLASK APP FOR ADMIN PANEL
# ==========================================================

flask_app = Flask(__name__)
flask_app.secret_key = "ziaul_islam_hacker_bot_secret_2026"

# ==========================================================
# JSON DATABASE FUNCTIONS
# ==========================================================

def init_databases():
    """Initialize JSON database files"""
    
    if not os.path.exists(USERS_DB):
        with open(USERS_DB, 'w', encoding='utf-8') as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
    
    if not os.path.exists(CHATS_DB):
        with open(CHATS_DB, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)
    
    if not os.path.exists(SETTINGS_DB):
        with open(SETTINGS_DB, 'w', encoding='utf-8') as f:
            json.dump({
                "bot_name": "Advanced Coding AI Bot",
                "total_users": 0,
                "total_chats": 0,
                "start_time": datetime.now().isoformat(),
                "developer": DEVELOPER_NAME,
                "website": DEVELOPER_WEBSITE
            }, f, indent=2, ensure_ascii=False)

def read_json(file_path):
    """Read data from JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(file_path, data):
    """Write data to JSON file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def save_user(user_id, username, first_name):
    """Save or update user information"""
    users = read_json(USERS_DB)
    
    if str(user_id) not in users:
        users[str(user_id)] = {
            "id": user_id,
            "username": username,
            "first_name": first_name,
            "joined": datetime.now().isoformat(),
            "chats_count": 0,
            "last_active": datetime.now().isoformat()
        }
        write_json(USERS_DB, users)
        
        # Update total users count
        settings = read_json(SETTINGS_DB)
        settings['total_users'] = len(users)
        write_json(SETTINGS_DB, settings)
    else:
        users[str(user_id)]['last_active'] = datetime.now().isoformat()
        if username:
            users[str(user_id)]['username'] = username
        write_json(USERS_DB, users)
    
    return users[str(user_id)]

def save_chat(user_id, user_message, ai_response):
    """Save chat history"""
    chats = read_json(CHATS_DB)
    chats.append({
        "user_id": str(user_id),
        "user_message": user_message,
        "ai_response": ai_response[:500],
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only last 1000 chats
    if len(chats) > 1000:
        chats = chats[-1000:]
    
    write_json(CHATS_DB, chats)
    
    # Update total chats count
    settings = read_json(SETTINGS_DB)
    settings['total_chats'] = len(chats)
    write_json(SETTINGS_DB, settings)

def get_user_memory(user_id):
    """Get or create user conversation memory"""
    if user_id not in user_memories:
        user_memories[user_id] = []
    return user_memories[user_id]

def add_to_memory(user_id, role, text):
    """Add message to user memory"""
    memory = get_user_memory(user_id)
    memory.append({
        "role": role,
        "text": text,
        "time": datetime.now().isoformat()
    })
    
    # Keep only last MAX_HISTORY messages
    if len(memory) > MAX_HISTORY:
        user_memories[user_id] = memory[-MAX_HISTORY:]

def clear_user_memory(user_id):
    """Clear user conversation memory"""
    if user_id in user_memories:
        user_memories[user_id] = []

# ==========================================================
# SYSTEM PROMPT (from your Termux code)
# ==========================================================

SYSTEM_PROMPT = """
তুমি একজন সিনিয়র সফটওয়্যার ইঞ্জিনিয়ার এবং ফুল-স্ট্যাক ডেভেলপার।

বিশেষ দক্ষতা:
- Python, JavaScript, TypeScript, HTML5, CSS3, Tailwind CSS
- React.js, Next.js, Node.js, Express.js
- PHP, Laravel, MySQL, PostgreSQL, MongoDB
- REST API, GraphQL, Docker, Linux, Termux, Git, GitHub

আচরণবিধি:
1. সর্বদা একজন পেশাদার সফটওয়্যার ডেভেলপারের মতো উত্তর দেবে।
2. কোড লিখলে সম্পূর্ণ, কার্যকর এবং production-ready কোড দেবে।
3. Mobile responsive, clean architecture এবং best practices অনুসরণ করবে।
4. Bug fix, refactor, optimization এবং security best practices প্রয়োগ করবে।
5. প্রয়োজন হলে step-by-step ব্যাখ্যা দেবে।
6. Markdown code block ব্যবহার করবে।
7. বাংলা বা ইংরেজি—যে ভাষায় প্রশ্ন করা হবে, সেই ভাষায় উত্তর দেবে।
8. UI/UX ডিজাইনের ক্ষেত্রে আধুনিক ও responsive design অনুসরণ করবে।
9. API integration এবং database schema স্পষ্টভাবে ব্যাখ্যা করবে।
10. অপ্রয়োজনীয় কথা বলবে না; সরাসরি কার্যকর সমাধান দেবে।

কোডিং নীতিমালা:
- Clean Code, SOLID Principles, DRY, KISS
- Security First, Performance Optimization
- Error Handling, Input Validation

উত্তরের কাঠামো:
- সংক্ষিপ্ত ব্যাখ্যা
- সম্পূর্ণ কোড
- ব্যবহারের নির্দেশনা
- প্রয়োজন হলে optimization tips

Developer: Ziaul Islam
Website: https://ziaulislam.top
"""

# ==========================================================
# GEMINI API FUNCTIONS
# ==========================================================

def build_prompt(user_message, memory):
    """Build prompt with system prompt and conversation history"""
    prompt = SYSTEM_PROMPT + "\n\n"
    
    for item in memory[-10:]:  # Last 10 messages for context
        if item["role"] == "user":
            prompt += f"User: {item['text']}\n"
        else:
            prompt += f"Assistant: {item['text']}\n"
    
    prompt += f"User: {user_message}\nAssistant:"
    return prompt

def get_ai_response(user_message, user_id):
    """Get response from Gemini API"""
    
    # Check if asking about developer
    dev_keywords = ["কে বানিয়েছে", "who made", "developer", "creator", "ziaul", "islam", 
                    "বানিয়েছে", "তৈরি করেছে", "কে তৈরি করেছে", "তোমার বাপ", "তোমার মালিক"]
    for keyword in dev_keywords:
        if keyword.lower() in user_message.lower():
            return f"""🤖 <b>আমি তৈরি করেছি {DEVELOPER_NAME}</b>

👨‍💻 <b>ডেভেলপার তথ্য:</b>
• নাম: {DEVELOPER_NAME}
• ওয়েবসাইট: {DEVELOPER_WEBSITE}
• দক্ষতা: Python, JavaScript, React, Node.js, PHP, Laravel, Cybersecurity
• বিশেষত্ব: Full-Stack Development, API Integration, Bot Development

🔗 <a href="{DEVELOPER_WEBSITE}">{DEVELOPER_WEBSITE}</a> এ ভিজিট করুন।

আমি একটি অ্যাডভান্সড কোডিং অ্যাসিস্ট্যান্ট। আপনার যেকোনো প্রোগ্রামিং সমস্যা জানাতে পারেন!"""
    
    try:
        memory = get_user_memory(user_id)
        prompt = build_prompt(user_message, memory)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2000,
                "topP": 0.9,
                "topK": 40
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return "দুঃখিত, কোনো উত্তর পাওয়া যায়নি। আবার চেষ্টা করুন।"
        else:
            logger.error(f"API Error: {response.status_code}")
            return f"API Error: {response.status_code}\nPlease try again later."
            
    except requests.exceptions.Timeout:
        return "⏰ টাইমআউট! সার্ভার সাড়া দিচ্ছে না। পরে আবার চেষ্টা করুন।"
    except requests.exceptions.ConnectionError:
        return "🌐 নেটওয়ার্ক কানেকশন সমস্যা! ইন্টারনেট চেক করুন।"
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return f"❌ ত্রুটি: {str(e)[:100]}\nপরে আবার চেষ্টা করুন।"

# ==========================================================
# TELEGRAM BOT COMMANDS
# ==========================================================

async def post_init(application):
    """Set bot commands after initialization"""
    commands = [
        BotCommand("start", "🚀 বট চালু করুন"),
        BotCommand("help", "📚 সাহায্য ও কমান্ড তালিকা"),
        BotCommand("ai", "🤖 AI প্রশ্ন করুন"),
        BotCommand("code", "💻 কোড জেনারেট করুন"),
        BotCommand("clear", "🗑️ মেমরি ক্লিয়ার করুন"),
        BotCommand("stats", "📊 আপনার পরিসংখ্যান"),
        BotCommand("about", "ℹ️ বট সম্পর্কে"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot commands set")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    
    # Save user to database
    save_user(user_id, username, first_name)
    
    # Create inline keyboard
    keyboard = [
        [InlineKeyboardButton("🤖 AI চ্যাট", callback_data='ai_chat')],
        [InlineKeyboardButton("💻 কোড জেনারেট", callback_data='code_gen')],
        [InlineKeyboardButton("📊 আমার স্ট্যাটাস", callback_data='my_stats')],
        [InlineKeyboardButton("ℹ️ সাহায্য", callback_data='help')],
        [InlineKeyboardButton("👨‍💻 ডেভেলপার", callback_data='developer')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
╔══════════════════════════════════════╗
║   🚀 অ্যাডভান্সড কোডিং এআই বট 🚀   ║
╚══════════════════════════════════════╝

<b>👋 হ্যালো {first_name}!</b>

আমি একটি অ্যাডভান্সড কোডিং অ্যাসিস্ট্যান্ট। আমি সাহায্য করতে পারি:

<b>💡 যা করতে পারেন:</b>
• যেকোনো প্রোগ্রামিং ভাষায় কোড লিখতে
• বাগ ফিক্স এবং ডিবাগিং
• প্রোজেক্ট আইডিয়া এবং আর্কিটেকচার
• API ইন্টিগ্রেশন
• ডাটাবেস ডিজাইন
• ওয়েব ডেভেলপমেন্ট
• মোবাইল অ্যাপ ডেভেলপমেন্ট

<b>👨‍💻 ডেভেলপার:</b> {DEVELOPER_NAME}
<b>🌐 ওয়েবসাইট:</b> {DEVELOPER_WEBSITE}

নিচের বাটন ব্যবহার করুন বা / টাইপ করে কমান্ড দিন!
"""
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
╔══════════════════════════════════════╗
║        📚 কমান্ডের তালিকা 📚         ║
╚══════════════════════════════════════╝

<b>🤖 এআই কমান্ড:</b>
<code>/ai আপনার প্রশ্ন</code> - AI থেকে উত্তর
<code>/code আপনার প্রয়োজন</code> - কোড জেনারেট

<b>🗂️ মেমরি কমান্ড:</b>
<code>/clear</code> - কনভারসেশন মেমরি ক্লিয়ার

<b>📊 ইনফো কমান্ড:</b>
<code>/stats</code> - আপনার পরিসংখ্যান
<code>/about</code> - বট সম্পর্কে তথ্য
<code>/help</code> - এই সাহায্য

<b>💡 উদাহরণ:</b>
• <code>/ai পাইথনে একটি REST API কিভাবে তৈরি করব?</code>
• <code>/code React.js এ একটি টোডো অ্যাপ</code>
• <code>/ai Django vs Flask কোনটি ভাল?</code>

<b>⚠️ টিপস:</b>
• আমি আপনার পুরো কনভারসেশন মনে রাখি
• জটিল প্রশ্ন ভেঙে জিজ্ঞাসা করুন
• কোডের জন্য ভাষা উল্লেখ করুন

👨‍💻 <b>ডেভেলপার:</b> {DEVELOPER_NAME}
"""
    await update.message.reply_text(help_text, parse_mode='HTML')

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ai command"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ দয়া করে একটি প্রশ্ন লিখুন!\n\n"
            "উদাহরণ: <code>/ai পাইথন কি?</code>\n\n"
            "অথবা সরাসরি আপনার প্রশ্ন টাইপ করুন।",
            parse_mode='HTML'
        )
        return
    
    question = ' '.join(context.args)
    
    # Send typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Send processing message
    msg = await update.message.reply_text("🤔 চিন্তা করছি... দয়া করে অপেক্ষা করুন। ⏳")
    
    # Get AI response
    response = get_ai_response(question, str(user_id))
    
    # Add to memory
    add_to_memory(str(user_id), "user", question)
    add_to_memory(str(user_id), "assistant", response[:500])
    
    # Save to database
    save_chat(user_id, question, response)
    
    # Update user chat count
    users = read_json(USERS_DB)
    if str(user_id) in users:
        users[str(user_id)]['chats_count'] = users[str(user_id)].get('chats_count', 0) + 1
        write_json(USERS_DB, users)
    
    # Edit message with response
    await msg.edit_text(
        f"💬 <b>আপনার প্রশ্ন:</b>\n{question[:200]}\n\n"
        f"🤖 <b>উত্তর:</b>\n{response}",
        parse_mode='HTML'
    )

async def code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /code command - specialized for code generation"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "❌ দয়া করে আপনার প্রয়োজন লিখুন!\n\n"
            "উদাহরণ: <code>/code Python এ একটি ক্যালকুলেটর</code>\n\n"
            "অথবা: <code>/code React.js login form with validation</code>",
            parse_mode='HTML'
        )
        return
    
    requirement = ' '.join(context.args)
    
    # Enhance prompt for code generation
    enhanced_prompt = f"""Please provide complete, production-ready code for: {requirement}

Requirements:
- Full working code with error handling
- Include comments and explanations
- Follow best practices
- Make it responsive if web-based
- Provide usage instructions

Please respond in Bengali or English based on the query language."""
    
    await update.message.chat.send_action(action="typing")
    msg = await update.message.reply_text("💻 কোড জেনারেট করছি... দয়া করে অপেক্ষা করুন। ⚙️")
    
    response = get_ai_response(enhanced_prompt, str(user_id))
    
    add_to_memory(str(user_id), "user", f"[CODE REQUEST] {requirement}")
    add_to_memory(str(user_id), "assistant", response[:500])
    save_chat(user_id, f"CODE: {requirement}", response)
    
    await msg.edit_text(
        f"💻 <b>আপনার প্রয়োজন:</b>\n{requirement}\n\n"
        f"📝 <b>জেনারেটেড কোড:</b>\n{response}",
        parse_mode='HTML'
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clear command - clear conversation memory"""
    user_id = str(update.effective_user.id)
    clear_user_memory(user_id)
    await update.message.reply_text("🗑️ আপনার কনভারসেশন মেমরি সফলভাবে ক্লিয়ার করা হয়েছে!\n\nনতুন করে শুরু করতে পারেন।")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show user statistics"""
    user_id = update.effective_user.id
    users = read_json(USERS_DB)
    user_data = users.get(str(user_id), {})
    memory = get_user_memory(str(user_id))
    
    stats_text = f"""
╔══════════════════════════════════════╗
║        📊 আপনার পরিসংখ্যান 📊        ║
╚══════════════════════════════════════╝

<b>👤 প্রোফাইল:</b>
• নাম: {user_data.get('first_name', 'N/A')}
• ইউজার আইডি: <code>{user_id}</code>
• ইউজারনেম: @{user_data.get('username', 'N/A')}

<b>📈 কার্যকলাপ:</b>
• মোট চ্যাট: {user_data.get('chats_count', 0)}
• মেমরিতে মেসেজ: {len(memory)}
• জয়েন তারিখ: {user_data.get('joined', 'N/A')[:19]}

<b>💬 এই সেশনে:</b>
• মোট প্রশ্ন: {len([m for m in memory if m['role'] == 'user'])}
• মোট উত্তর: {len([m for m in memory if m['role'] == 'assistant'])}

👨‍💻 <b>ডেভেলপার:</b> {DEVELOPER_NAME}
"""
    await update.message.reply_text(stats_text, parse_mode='HTML')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command"""
    settings = read_json(SETTINGS_DB)
    
    about_text = f"""
╔══════════════════════════════════════╗
║        ℹ️ বট সম্পর্কে তথ্য ℹ️        ║
╚══════════════════════════════════════╝

<b>🤖 বট নাম:</b> {settings.get('bot_name')}
<b>🔢 ভার্সন:</b> 3.0.0
<b>🧠 এআই মডেল:</b> {MODEL_NAME}

<b>👨‍💻 ডেভেলপার:</b>
• নাম: {DEVELOPER_NAME}
• ওয়েবসাইট: {DEVELOPER_WEBSITE}

<b>📊 গ্লোবাল স্ট্যাটস:</b>
• মোট ইউজার: {settings.get('total_users', 0)}
• মোট চ্যাট: {settings.get('total_chats', 0)}
• সার্ভার চালু: {settings.get('start_time', 'N/A')[:19]}

<b>✨ ফিচারস:</b>
• Gemini AI Powered
• Persistent Memory
• Code Generation
• Multi-language Support
• JSON Database
• Admin Panel

<b>📝 লাইসেন্স:</b> MIT
"""
    await update.message.reply_text(about_text, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages (non-command)"""
    user_id = update.effective_user.id
    message = update.message.text.strip()
    
    if not message or len(message) < 2:
        return
    
    if message.startswith('/'):
        return
    
    await update.message.chat.send_action(action="typing")
    msg = await update.message.reply_text("🤔 চিন্তা করছি... ⏳")
    
    response = get_ai_response(message, str(user_id))
    
    add_to_memory(str(user_id), "user", message)
    add_to_memory(str(user_id), "assistant", response[:500])
    save_chat(user_id, message, response)
    
    # Update user chat count
    users = read_json(USERS_DB)
    if str(user_id) in users:
        users[str(user_id)]['chats_count'] = users[str(user_id)].get('chats_count', 0) + 1
        write_json(USERS_DB, users)
    
    await msg.edit_text(response, parse_mode='HTML')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'ai_chat':
        await query.edit_message_text(
            "🤖 <b>AI চ্যাট মোড</b>\n\n"
            "আপনার প্রশ্ন লিখুন এই ফরম্যাটে:\n"
            "<code>/ai আপনার প্রশ্ন</code>\n\n"
            "অথবা সরাসরি যেকোনো প্রশ্ন টাইপ করুন।\n\n"
            "<b>উদাহরণ:</b>\n"
            "• <code>/ai পাইথন এ ফাইল কিভাবে রিড করব?</code>\n"
            "• <code>/ai REST API এর best practices কি?</code>\n"
            "• <code>/ai ডাটাবেস নরমালাইজেশন কি?</code>",
            parse_mode='HTML'
        )
    
    elif query.data == 'code_gen':
        await query.edit_message_text(
            "💻 <b>কোড জেনারেটর</b>\n\n"
            "আপনার প্রয়োজন লিখুন এই ফরম্যাটে:\n"
            "<code>/code আপনার প্রয়োজন</code>\n\n"
            "<b>উদাহরণ:</b>\n"
            "• <code>/code Python এ একটি ক্যালকুলেটর</code>\n"
            "• <code>/code React.js login form with validation</code>\n"
            "• <code>/code Django REST API for blog</code>\n\n"
            "আমি production-ready কোড দিয়ে সাহায্য করব!",
            parse_mode='HTML'
        )
    
    elif query.data == 'my_stats':
        user_id = query.from_user.id
        users = read_json(USERS_DB)
        user_data = users.get(str(user_id), {})
        memory = get_user_memory(str(user_id))
        
        await query.edit_message_text(
            f"📊 <b>আপনার পরিসংখ্যান</b>\n\n"
            f"👤 নাম: {user_data.get('first_name', 'N/A')}\n"
            f"💬 মোট চ্যাট: {user_data.get('chats_count', 0)}\n"
            f"🧠 মেমরিতে মেসেজ: {len(memory)}\n"
            f"📅 জয়েন: {user_data.get('joined', 'N/A')[:19]}\n\n"
            f"👨‍💻 ডেভেলপার: {DEVELOPER_NAME}",
            parse_mode='HTML'
        )
    
    elif query.data == 'help':
        await query.edit_message_text(
            "📚 <b>সাহায্য ও কমান্ড</b>\n\n"
            "<code>/start</code> - বট চালু করুন\n"
            "<code>/help</code> - এই সাহায্য\n"
            "<code>/ai &lt;প্রশ্ন&gt;</code> - AI প্রশ্ন\n"
            "<code>/code &lt;প্রয়োজন&gt;</code> - কোড জেনারেট\n"
            "<code>/clear</code> - মেমরি ক্লিয়ার\n"
            "<code>/stats</code> - আপনার স্ট্যাটস\n"
            "<code>/about</code> - বট সম্পর্কে\n\n"
            "<b>💡 টিপস:</b>\n"
            "• আমি আপনার কনভারসেশন মনে রাখি\n"
            "• সরাসরি প্রশ্ন টাইপ করলেও উত্তর দেই\n"
            "• কোডের জন্য ভাষা উল্লেখ করুন",
            parse_mode='HTML'
        )
    
    elif query.data == 'developer':
        await query.edit_message_text(
            f"👨‍💻 <b>ডেভেলপার তথ্য</b>\n\n"
            f"<b>নাম:</b> {DEVELOPER_NAME}\n"
            f"<b>ওয়েবসাইট:</b> <a href='{DEVELOPER_WEBSITE}'>{DEVELOPER_WEBSITE}</a>\n\n"
            f"<b>দক্ষতা:</b>\n"
            f"• Python, JavaScript, TypeScript\n"
            f"• React.js, Next.js, Node.js\n"
            f"• PHP, Laravel, MySQL, PostgreSQL\n"
            f"• MongoDB, Docker, Linux, Git\n"
            f"• Cybersecurity, Bot Development\n\n"
            f"<b>যোগাযোগ:</b>\n"
            f"• ওয়েবসাইট ভিজিট করুন\n"
            f"• GitHub: @ziaulislam\n\n"
            f"<b>© 2024 - All Rights Reserved</b>",
            parse_mode='HTML',
            disable_web_page_preview=False
        )

# ==========================================================
# FLASK ADMIN PANEL
# ==========================================================

@flask_app.route('/')
def admin_panel():
    """Admin panel homepage"""
    users = read_json(USERS_DB)
    chats = read_json(CHATS_DB)
    settings = read_json(SETTINGS_DB)
    
    return f'''
    <!DOCTYPE html>
    <html lang="bn">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>এডমিন প্যানেল - {DEVELOPER_NAME}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            
            .header {{
                text-align: center;
                color: white;
                margin-bottom: 30px;
                padding: 20px;
            }}
            
            .header h1 {{
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            
            .stat-card {{
                background: rgba(255,255,255,0.95);
                border-radius: 15px;
                padding: 25px;
                text-align: center;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
            }}
            
            .stat-icon {{
                font-size: 3em;
                margin-bottom: 10px;
            }}
            
            .stat-number {{
                font-size: 2.5em;
                font-weight: bold;
                color: #667eea;
            }}
            
            .stat-label {{
                color: #666;
                margin-top: 5px;
                font-size: 1.1em;
            }}
            
            .card {{
                background: rgba(255,255,255,0.95);
                border-radius: 15px;
                padding: 25px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }}
            
            .card h2 {{
                margin-bottom: 20px;
                color: #333;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            
            th {{
                background: #667eea;
                color: white;
                font-weight: 600;
            }}
            
            tr:hover {{
                background: #f5f5f5;
            }}
            
            .developer-info {{
                text-align: center;
                padding: 25px;
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
                border-radius: 15px;
            }}
            
            .developer-info a {{
                color: white;
                text-decoration: none;
                border-bottom: 1px solid white;
            }}
            
            .badge {{
                display: inline-block;
                padding: 5px 15px;
                background: #4CAF50;
                color: white;
                border-radius: 20px;
                font-size: 0.9em;
                margin-top: 10px;
            }}
            
            @keyframes fadeIn {{
                from {{
                    opacity: 0;
                    transform: translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .animate {{
                animation: fadeIn 0.5s ease;
            }}
            
            .refresh-btn {{
                background: #667eea;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 10px;
                cursor: pointer;
                margin-bottom: 20px;
                font-size: 1em;
            }}
            
            .refresh-btn:hover {{
                background: #764ba2;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header animate">
                <h1>🤖 অ্যাডভান্সড কোডিং এআই বট</h1>
                <p>এডমিন কন্ট্রোল প্যানেল | টেলিগ্রাম বট ম্যানেজমেন্ট</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card animate">
                    <div class="stat-icon">👥</div>
                    <div class="stat-number">{len(users)}</div>
                    <div class="stat-label">মোট ইউজার</div>
                </div>
                <div class="stat-card animate">
                    <div class="stat-icon">💬</div>
                    <div class="stat-number">{len(chats)}</div>
                    <div class="stat-label">মোট চ্যাট</div>
                </div>
                <div class="stat-card animate">
                    <div class="stat-icon">📊</div>
                    <div class="stat-number">{settings.get('total_chats', 0)}</div>
                    <div class="stat-label">টোটাল ইন্টারঅ্যাকশন</div>
                </div>
                <div class="stat-card animate">
                    <div class="stat-icon">⏰</div>
                    <div class="stat-number" style="font-size: 1.2em;">{settings.get('start_time', 'N/A')[:19]}</div>
                    <div class="stat-label">সার্ভার চালু</div>
                </div>
            </div>
            
            <div class="card animate">
                <h2>📊 সর্বশেষ চ্যাট লগ</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr><th>ইউজার আইডি</th><th>মেসেজ</th><th>রেসপন্স</th><th>সময়</th></tr>
                        </thead>
                        <tbody>
                            {''.join([f'<tr><td>{chat["user_id"][:15]}...</td><td style="max-width: 200px; overflow: hidden;">{chat["user_message"][:50]}...</td><td style="max-width: 200px; overflow: hidden;">{chat["ai_response"][:50]}...</td><td>{chat["timestamp"][:19]}</td></tr>' for chat in chats[-20:]])}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="card animate">
                <h2>👥 নিবন্ধিত ইউজার লিস্ট</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr><th>ইউজার আইডি</th><th>ইউজারনেম</th><th>নাম</th><th>চ্যাট কাউন্ট</th><th>জয়েন</th></tr>
                        </thead>
                        <tbody>
                            {''.join([f'<tr><td>{uid[:15]}...</td><td>@{u.get("username", "N/A")}</td><td>{u.get("first_name", "N/A")}</td><td>{u.get("chats_count", 0)}</td><td>{u.get("joined", "N/A")[:19]}</td></tr>' for uid, u in list(users.items())[-30:]])}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="developer-info animate">
                <p>👨‍💻 <strong>ডেভেলপার: {DEVELOPER_NAME}</strong></p>
                <p>🌐 ওয়েবসাইট: <a href="{DEVELOPER_WEBSITE}" target="_blank">{DEVELOPER_WEBSITE}</a></p>
                <p>🤖 বট ইউজারনাম: @AdvancedCodingBot</p>
                <p>🧠 এআই মডেল: {MODEL_NAME}</p>
                <div class="badge">✅ বট অনলাইন ও সক্রিয়</div>
            </div>
        </div>
        
        <script>
            // Auto refresh every 30 seconds
            setTimeout(function() {{
                location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    '''

@flask_app.route('/api/stats')
def api_stats():
    """API endpoint for stats"""
    users = read_json(USERS_DB)
    chats = read_json(CHATS_DB)
    settings = read_json(SETTINGS_DB)
    
    return jsonify({
        'total_users': len(users),
        'total_chats': len(chats),
        'total_interactions': settings.get('total_chats', 0),
        'status': 'online',
        'developer': DEVELOPER_NAME,
        'website': DEVELOPER_WEBSITE
    })

def run_flask():
    """Run Flask admin panel"""
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ==========================================================
# MAIN FUNCTION
# ==========================================================

def main():
    """Main function to run the bot"""
    # Initialize databases
    init_databases()
    logger.info("📁 JSON databases initialized")
    
    # Start Flask admin panel in separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("🌐 Admin panel started on port 5000")
    
    # Create Telegram application
    application = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ai", ai_command))
    application.add_handler(CommandHandler("code", code_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Add callback handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler for non-command messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    logger.info("🚀 Starting Telegram bot...")
    logger.info(f"👨‍💻 Developer: {DEVELOPER_NAME}")
    logger.info(f"🌐 Website: {DEVELOPER_WEBSITE}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()