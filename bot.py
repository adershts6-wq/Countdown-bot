# bot.py
import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ChatMemberHandler,
    ContextTypes,
    filters,
)

# -------- CONFIG ----------
BOT_TOKEN ="8271513610:AAGnLvMUtIBnxRiNfOnIqRJOoy1xqwqtfio"
BOT_USERNAME ="Countdown00_bot"  
DATABASE_FILE = "countdown_data.sqlite"
DEFAULT_REMINDER_TIME = "06:00"
# --------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- SQLite helpers -----------------
def get_conn():
    # check_same_thread False because ApplicationBuilder uses multiple threads
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        chat_id TEXT PRIMARY KEY,
        lang TEXT DEFAULT 'en',
        reminder_time TEXT DEFAULT '',
        reminder_on INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT,
        name TEXT,
        date TEXT,
        UNIQUE(chat_id, name)
    )
    """)

    conn.commit()
    conn.close()


def ensure_chat_db(chat_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO chats (chat_id, lang, reminder_time, reminder_on) VALUES (?, ?, ?, ?)",
            (chat_id, "en", DEFAULT_REMINDER_TIME, 0)
        )
        conn.commit()
    conn.close()

def set_chat_lang(chat_id: str, lang: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE chats SET lang = ? WHERE chat_id = ?", (lang, chat_id))
    conn.commit()
    conn.close()

def set_chat_reminder_time(chat_id: str, time_str: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE chats SET reminder_time = ? WHERE chat_id = ?", (time_str, chat_id))
    conn.commit()
    conn.close()

def set_chat_reminder_on(chat_id: str, on: bool):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE chats SET reminder_on = ? WHERE chat_id = ?", (1 if on else 0, chat_id))
    conn.commit()
    conn.close()

def get_chat_info(chat_id: str) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"chat_id": chat_id, "lang": "en", "reminder_time": DEFAULT_REMINDER_TIME, "reminder_on": 0}

def add_event_db(chat_id: str, name: str, date_str: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR REPLACE INTO events (chat_id, name, date) VALUES (?, ?, ?)", (chat_id, name, date_str))
        conn.commit()
        return True
    except Exception as e:
        logger.exception("add_event_db error: %s", e)
        return False
    finally:
        conn.close()

def delete_event_db(chat_id: str, name: str) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM events WHERE chat_id = ? AND LOWER(name) = LOWER(?)", (chat_id, name))
    cnt = cur.rowcount
    conn.commit()
    conn.close()
    return cnt

def list_events_db(chat_id: str) -> List[Dict[str, str]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, date FROM events WHERE chat_id = ? ORDER BY date", (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_reminder_chats() -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT chat_id, lang, reminder_time FROM chats WHERE reminder_on = 1")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ----------------- Multilingual TEXTS -----------------
TEXTS = {
    "en": {
        "welcome": "🤖 *Smart Countdown Bot*\nManage your countdowns easily!",
        "add_event": "➕ Add Event",
        "show_events": "📅 Show Events",
        "delete_event": "❌ Delete Event",
        "set_time": "🕒 Set Reminder Time",
        "toggle_on": "⏰ Start Reminder",
        "toggle_off": "⏸ Stop Reminder",
        "change_lang": "🌐 Change Language",
        "refresh": "🔁 Refresh Bot",
        "add_group": "👥 Add to Group",
        "enter_event": "📝 Send event name and date in one line, e.g:\nBirthday 2025-12-25",
        "enter_time": "⏰ Please send reminder time in HH:MM format (e.g., 07:30)",
        "event_added": "✅ Event '{0}' saved for {1}",
        "invalid_date": "⚠️ Invalid format. Use: YYYY-MM-DD",
        "no_events": "📭 No events found.",
        "events_header": "📅 *Your Events:*",
        "event_future": "🎯 {0} – {1} days left ({2})",
        "event_today": "🎉 {0} is today!",
        "event_past": "⌛ {0} was {1} days ago ({2})",
        "time_set": "✅ Reminder time set to {0}",
        "reminder_started": "⏰ Daily reminders activated for this chat.",
        "reminder_stopped": "⏸ Daily reminders stopped for this chat.",
        "select_lang": "Please choose your language:",
        "lang_set": "✅ Language set to {0}",
        "thanks_added": "🙏 Thanks for adding me! I will send daily reminders here."
    },
    "ml": {
        "welcome": "🤖 *Smart Countdown Bot*\nനിങ്ങളുടെ കൗണ്ട്ഡൗൺ എളുപ്പത്തിൽ നിയന്ത്രിക്കൂ!",
        "add_event": "➕ ഇവന്റ് ചേർക്കുക",
        "show_events": "📅 ഇവന്റ് കാണുക",
        "delete_event": "❌ ഇവന്റ് നീക്കുക",
        "set_time": "🕒 റിമൈൻഡർ സമയം ക്രമീകരിക്കുക",
        "toggle_on": "⏰ റിമൈൻഡർ ആരംഭിക്കുക",
        "toggle_off": "⏸ റിമൈൻഡറു നിർത്തുക",
        "change_lang": "🌐 ഭാഷ മാറ്റുക",
        "refresh": "🔁 ബോട്ട് റിഫ്രഷ് ചെയ്യുക",
        "add_group": "👥 ഗ്രൂപ്പിലേക്ക് ചേർക്കുക",
        "enter_event": "📝 ഇവന്റ് പേര് + തീയതി ഒരേ വരിയിൽ അയയ്ക്കുക:\nBirthday 2025-12-25",
        "enter_time": "⏰ റിമൈൻഡർ സമയം HH:MM ഫോർമാറ്റിൽ അയക്കൂ (ഉദാ: 07:30)",
        "event_added": "✅ ഇവന്റ് '{0}' {1}-ന് ചേർത്തു",
        "invalid_date": "⚠️ തെറ്റായ ഫോർമാറ്റ്. ഉപയോഗിക്കുക: YYYY-MM-DD",
        "no_events": "📭 ഇവന്റ് ഒന്നുമില്ല.",
        "events_header": "📅 *നിങ്ങളുടെ ഇവന്റ്‌സ്:*",
        "event_future": "🎯 {0} – {1} ദിവസം ബാക്കി ({2})",
        "event_today": "🎉 {0} ഇന്ന് തന്നെയാണ്!",
        "event_past": "⌛ {0} കഴിഞ്ഞിട്ട് {1} ദിവസം ആയി ({2})",
        "time_set": "✅ റിമൈൻഡർ സമയം {0} ആയി സെറ്റ് ചെയ്തു",
        "reminder_started": "⏰ ദിവസം റിമൈൻഡറുകൾ സജീവമായി.",
        "reminder_stopped": "⏸ റിമൈൻഡർ നിർത്തി.",
        "select_lang": "ദയവായി നിങ്ങളുടെ ഭാഷ തിരഞ്ഞെടുക്കൂ:",
        "lang_set": "✅ ഭാഷ {0} ആയി സെറ്റ് ചെയ്തു",
        "thanks_added": "🙏 എനിക്ക് ഗ്രൂപ്പിൽ ചേർത്തതിന് നന്ദി! ഞാൻ ഇവിടെ ദിനേന റിമൈണ്ടറുകൾ അയക്കും."
    },
    "hi": {
        "welcome": "🤖 *Smart Countdown Bot*\nअपने काउंटडाउन को आसानी से मैनेज करें!",
        "add_event": "➕ इवेंट जोड़ें",
        "show_events": "📅 इवेंट दिखाएँ",
        "delete_event": "❌ इवेंट हटाएँ",
        "set_time": "🕒 रिमाइंडर समय सेट करें",
        "toggle_on": "⏰ रिमाइंडर चालू करें",
        "toggle_off": "⏸ रिमाइंडर बंद करें",
        "change_lang": "🌐 भाषा बदलें",
        "refresh": "🔁 बॉट रीफ्रेश करें",
        "add_group": "👥 ग्रुप में जोड़ें",
        "enter_event": "📝 इवेंट नाम और तारीख एक लाइन में भेजें:\nBirthday 2025-12-25",
        "enter_time": "⏰ कृपया HH:MM प्रारूप में समय भेजें (उदाहरण: 07:30)",
        "event_added": "✅ इवेंट '{0}' सेव किया गया {1}",
        "invalid_date": "⚠️ गलत फॉर्मेट. उपयोग करें: YYYY-MM-DD",
        "no_events": "📭 कोई इवेंट नहीं मिला।",
        "events_header": "📅 *आपके इवेंट्स:*",
        "event_future": "🎯 {0} – {1} दिन बचे ({2})",
        "event_today": "🎉 {0} आज है!",
        "event_past": "⌛ {0} {1} दिन पहले था ({2})",
        "time_set": "✅ रिमाइंडर समय सेट किया गया {0}",
        "reminder_started": "⏰ दैनिक रिमाइंडर सक्रिय किए गए।",
        "reminder_stopped": "⏸ दैनिक रिमाइंडर बंद किए गए।",
        "select_lang": "कृपया अपनी भाषा चुनें:",
        "lang_set": "✅ भाषा सेट की गई {0}",
        "thanks_added": "🙏 मुझे जोड़ने के लिए धन्यवाद! मैं यहाँ दैनिक रिमाइंडर भेजूँगा।"
    },
    "ta": {
        "welcome": "🤖 *Smart Countdown Bot*\nஉங்கள் கவுண்டவுன்களை எளிதாக நிர்வகிக்கவும்!",
        "add_event": "➕ நிகழ்வு சேர்",
        "show_events": "📅 நிகழ்வுகளை காட்டு",
        "delete_event": "❌ நிகழ்வை நீக்கு",
        "set_time": "🕒 நினைவூட்டல் நேரம் அமைக்கவும்",
        "toggle_on": "⏰ நினைவூட்டலை துவக்கவும்",
        "toggle_off": "⏸ நினைவூட்டலை நிறுத்தவும்",
        "change_lang": "🌐 மொழியை மாற்றவும்",
        "refresh": "🔁 பாட்டை புதுப்பிக்கவும்",
        "add_group": "👥 குழுவில் சேர்க்கவும்",
        "enter_event": "📝 நிகழ்வு பெயரும் தேதி ஒரு வரியில் அனுப்பவும்:\nBirthday 2025-12-25",
        "enter_time": "⏰ நினைவூட்டல் நேரத்தை HH:MM வடிவில் அனுப்பவும் (உதா: 07:30)",
        "event_added": "✅ நிகழ்வு '{0}' சேமிக்கப்பட்டது {1}",
        "invalid_date": "⚠️ தவறான வடிவம். பயன்ப/use: YYYY-MM-DD",
        "no_events": "📭 நிகழ்வுகள் எதுவும் இல்லை.",
        "events_header": "📅 *உங்கள் நிகழ்வுகள்:*",
        "event_future": "🎯 {0} – {1} நாட்கள் மீதி ({2})",
        "event_today": "🎉 {0} இன்று தான்!",
        "event_past": "⌛ {0} {1} நாட்கள் முன்பு ({2})",
        "time_set": "✅ நினைவூட்டல் நேரம் {0} என்று அமைக்கப்பட்டது",
        "reminder_started": "⏰ தினசரி நினைவூட்டல்கள் இயக்கம் ஆனது.",
        "reminder_stopped": "⏸ தினசரி நினைவூட்டல்கள் நிறுத்தப்பட்டன.",
        "select_lang": "தயவுசெய்து உங்கள் மொழியை தேர்வுசெய்யவும்:",
        "lang_set": "✅ மொழி {0} ஆக அமைக்கப்பட்டது",
        "thanks_added": "🙏 என்னை சேர்த்ததற்கு நன்றி! நான் இங்கு தினசரி நினைவூட்டல்களை அனுப்புவேன்."
    }
}

# ----------------- Helpers -----------------
def get_text_for(chat_id: str, key: str) -> str:
    ensure_chat_db(chat_id)
    row = get_chat_info_db(chat_id)
    lang = row.get("lang", "en")
    return TEXTS.get(lang, TEXTS["en"]).get(key, "")

def get_chat_info_db(chat_id: str) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {"chat_id": chat_id, "lang": "en", "reminder_time": DEFAULT_REMINDER_TIME, "reminder_on": 0}

# small wrapper reusing functions defined earlier
def ensure_chat_db_wrapper(chat_id: str):
    ensure_chat_db(chat_id)  # already defined earlier

# ----------------- UI / Handlers -----------------
def build_main_menu(chat_id: str) -> InlineKeyboardMarkup:
    ensure_chat_db(chat_id)
    info = get_chat_info_db(chat_id)
    lang = info.get("lang", "en")
    t = TEXTS.get(lang, TEXTS["en"])
    toggle_label = t["toggle_off"] if info.get("reminder_on", 0) else t["toggle_on"]

    kb = [
        [InlineKeyboardButton(t["add_event"], callback_data="add")],
        [InlineKeyboardButton(t["show_events"], callback_data="show")],
        [InlineKeyboardButton(t["delete_event"], callback_data="delete")],
        [InlineKeyboardButton(t["set_time"], callback_data="set_time")],
        [InlineKeyboardButton(toggle_label, callback_data="toggle_reminder")],
        [InlineKeyboardButton(t["change_lang"], callback_data="change_lang"),
         InlineKeyboardButton(t["refresh"], callback_data="refresh")],
        [InlineKeyboardButton(t["add_group"], url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
        [InlineKeyboardButton("👤 Owner", url="https://t.me/Adershts1"),
         InlineKeyboardButton("ℹ️ About", callback_data="about")]  # 👈 Added About button here
    ]

    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    ensure_chat_db(chat_id)
    text = get_text_for(chat_id, "welcome")
    await context.bot.send_message(chat_id=int(chat_id), text=text, reply_markup=build_main_menu(chat_id), parse_mode="Markdown")

# --- ABOUT COMMAND ---
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *About Smart Countdown Bot*\n\n"
        "Welcome to *Smart Countdown Bot*! 🎯\n\n"
        "This bot helps you easily manage and track all your important dates and events. "
        "You can create countdowns for birthdays, anniversaries, exams, meetings, or any other special occasion. "
        "Once you add events, the bot automatically sends *daily reminders* showing how many days are left. 🗓️\n\n"
        "✨ *Main Features:*\n"
        "• Add unlimited countdown events with one simple message (e.g., `Birthday 2025-12-25`).\n"
        "• View all your saved events in an organized list.\n"
        "• Delete or update events anytime.\n"
        "• Set your preferred daily reminder time (e.g., 06:00 or 07:30).\n"
        "• Works perfectly in *Private Chats* and *Groups*.\n"
        "• Sends an automatic welcome message when added to a group.\n"
        "• Supports multiple languages – English, Malayalam, Hindi, and Tamil.\n"
        "• Stores data safely in SQLite and works offline in Termux or online on Render.\n"
        "• Lightweight, fast, and optimized for 24×7 use. 🚀\n\n"
        "💡 *Usage Tips:*\n"
        "Use /start to open the interactive menu.\n"
        "Use /about anytime to learn more about the bot.\n"
        "Ensure the bot has message permission in groups.\n\n"
        "📘 *Version:* 1.0.0\n"
        "⚙️ *Powered by:* Python & Telegram Bot API\n\n"
        "👤 *Created by:* [@Adershts1](https://t.me/Adershts1)"
    )
    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
# When bot added to group -> send thank you & enable reminders by default for groups
async def my_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.my_chat_member
    old = result.old_chat_member
    new = result.new_chat_member
    chat = update.effective_chat
    chat_id = str(chat.id)
    try:
        # bot was added
        if new.status in ("member", "administrator") and old.status in ("left", "kicked"):
            print("✅ Bot added to group detected:", chat.title)
            ensure_chat_db(chat_id)
            set_chat_reminder_on(chat_id, True)
            message = (
                "🙏 Thanks for adding me to your group!\n\n"
                "I'm your *Smart Countdown Bot*. I'll help you manage events, "
                "show countdowns, and send daily reminders here automatically. 🚀\n\n"
                "Use /start anytime to open the menu."
            )
            await context.bot.send_message(chat_id=int(chat_id), text=message, parse_mode="Markdown")
    except Exception as e:
        logger.exception("my_chat_member error: %s", e)

async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat.id)
    ensure_chat_db(chat_id)
    data = query.data

    if data == "add":
        await query.message.reply_text(get_text_for(chat_id, "enter_event"))
        context.user_data["action"] = "add"
    elif data == "show":
        events = list_events_db(chat_id)
        if not events:
            await query.message.reply_text(get_text_for(chat_id, "no_events"))
        else:
            lines = [get_text_for(chat_id, "events_header")]
            for e in events:
                left = None
                try:
                    left = (datetime.strptime(e["date"], "%Y-%m-%d").date() - datetime.now().date()).days
                except:
                    pass
                if left is None:
                    continue
                if left > 0:
                    lines.append(TEXTS[get_chat_info_db(chat_id).get("lang", "en")]["event_future"].format(e["name"], left, e["date"]))
                elif left == 0:
                    lines.append(TEXTS[get_chat_info_db(chat_id).get("lang", "en")]["event_today"].format(e["name"]))
                else:
                    lines.append(TEXTS[get_chat_info_db(chat_id).get("lang", "en")]["event_past"].format(e["name"], abs(left), e["date"]))
            await query.message.reply_text("\n".join(lines), parse_mode="Markdown")
    elif data == "delete":
        await query.message.reply_text(get_text_for(chat_id, "invalid_date") if False else "Send event name to delete (exact name):")
        context.user_data["action"] = "delete"
    elif data == "set_time":
        await query.message.reply_text(get_text_for(chat_id, "enter_time"))
        context.user_data["action"] = "set_time"
    elif data == "toggle_reminder":
        info = get_chat_info_db(chat_id)
        curr = info.get("reminder_on", 0)
        set_chat_reminder_on(chat_id, not bool(curr))
        await query.message.reply_text(get_text_for(chat_id, "reminder_started") if not curr else get_text_for(chat_id, "reminder_stopped"))
        await query.message.reply_text(get_text_for(chat_id, "welcome"), reply_markup=build_main_menu(chat_id), parse_mode="Markdown")
    elif data == "change_lang":
        kb = [
            [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en")],
            [InlineKeyboardButton("Malayalam 🇮🇳", callback_data="lang_ml")],
            [InlineKeyboardButton("Hindi 🇮🇳", callback_data="lang_hi")],
            [InlineKeyboardButton("Tamil 🇮🇳", callback_data="lang_ta")]
        ]
        await query.message.reply_text(get_text_for(chat_id, "select_lang"), reply_markup=InlineKeyboardMarkup(kb))
    elif data and data.startswith("lang_"):
        new_lang = data.split("_", 1)[1]
        set_chat_lang(chat_id, new_lang)
        await query.message.reply_text(TEXTS.get(new_lang, TEXTS["en"]).get("lang_set", "Language updated").format(new_lang.upper()))
        await query.message.reply_text(get_text_for(chat_id, "welcome"), reply_markup=build_main_menu(chat_id), parse_mode="Markdown")
    elif data == "refresh":
        # reload DB is automatic (we read from sqlite each time). Just confirm to user.
        await query.message.reply_text("🔁 Bot refreshed!")
        await query.message.reply_text(get_text_for(chat_id, "welcome"), reply_markup=build_main_menu(chat_id), parse_mode="Markdown")
    elif data == "about":
        text = (
            "🤖 *About Smart Countdown Bot*\n\n"
            "Welcome to *Smart Countdown Bot*! 🎯\n\n"
            "This bot helps you easily manage and track all your important dates and events. "
            "You can create countdowns for birthdays, anniversaries, exams, meetings, or any other special occasion. "
            "Once you add events, the bot automatically sends *daily reminders* showing how many days are left. 🗓️\n\n"
            "✨ *Main Features:*\n"
            "• Add unlimited countdown events.\n"
            "• View, delete, and update events easily.\n"
            "• Set your daily reminder time.\n"
            "• Works in both private and group chats.\n"
            "• Sends welcome message automatically when added to a group.\n"
            "• Multilingual – English, Malayalam, Hindi, Tamil.\n"
            "• Uses SQLite for safe offline storage.\n"
            "• Runs on Termux or Render 24×7. 🚀\n\n"
            "📘 *Version:* 1.0.0\n"
            "⚙️ *Powered by:* Python & Telegram Bot API\n\n"
            "👤 *Created by:* [@Adershts1](https://t.me/Adershts1)"
        )
        await query.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.message.chat.id)
    ensure_chat_db(chat_id)
    action = context.user_data.get("action")
    text = update.message.text.strip()

    if action == "add":
        # Expect "Name YYYY-MM-DD"
        try:
            name, date_str = text.rsplit(" ", 1)
            datetime.strptime(date_str, "%Y-%m-%d")  # validate
            add_event_db(chat_id, name.strip(), date_str.strip())
            await update.message.reply_text(get_text_for(chat_id, "event_added").format(name.strip(), date_str.strip()))
        except Exception:
            await update.message.reply_text(get_text_for(chat_id, "invalid_date"))
        context.user_data["action"] = None
    elif action == "delete":
        name = text.strip()
        deleted = delete_event_db(chat_id, name)
        if deleted:
            await update.message.reply_text(get_text_for(chat_id, "deleted_event").format(name))
        else:
            await update.message.reply_text(get_text_for(chat_id, "no_events"))
        context.user_data["action"] = None
    elif action == "set_time":
        try:
            hh, mm = map(int, text.split(":"))
            if 0 <= hh < 24 and 0 <= mm < 60:
                tstr = f"{hh:02}:{mm:02}"
                set_chat_reminder_time(chat_id, tstr)
                await update.message.reply_text(get_text_for(chat_id, "time_set").format(tstr))
            else:
                raise ValueError()
        except Exception:
            await update.message.reply_text(get_text_for(chat_id, "enter_time"))
        context.user_data["action"] = None

# ---------------- Reminder job ----------------
async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now().strftime("%H:%M")
    chats = get_all_reminder_chats()
    for c in chats:
        try:
            chat_id = c["chat_id"]
            rem_time = c.get("reminder_time", DEFAULT_REMINDER_TIME)
            if rem_time == now:
                events = list_events_db(chat_id)
                if not events:
                    # optionally skip sending if no events
                    continue
                lang = c.get("lang", "en")
                texts = TEXTS.get(lang, TEXTS["en"])
                lines = [texts.get("events_header", "Daily Countdown:")]
                for e in events:
                    left = None
                    try:
                        left = (datetime.strptime(e["date"], "%Y-%m-%d").date() - datetime.now().date()).days
                    except:
                        continue
                    if left > 0:
                        lines.append(texts.get("event_future").format(e["name"], left, e["date"]))
                    elif left == 0:
                        lines.append(texts.get("event_today").format(e["name"]))
                msg = "\n".join(lines)
                try:
                    await context.bot.send_message(chat_id=int(chat_id), text=msg, parse_mode="Markdown")
                except Exception as exc:
                    logger.exception("Failed send reminder to %s : %s", chat_id, exc)
        except Exception as exc:
            logger.exception("Reminder loop error: %s", exc)

# ---------------- Status Command ----------------
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    ensure_chat_db(chat_id)
    info = get_chat_info_db(chat_id)
    events = list_events_db(chat_id)

    reminder_state = "✅ ON" if info.get("reminder_on", 0) else "⏸ OFF"
    reminder_time = info.get("reminder_time", DEFAULT_REMINDER_TIME)
    total_events = len(events)
    lang = info.get("lang", "en")

    msg = (
        f"📊 *Status Summary:*\n"
        f"⏰ Reminder: {reminder_state}\n"
        f"🕒 Time: {reminder_time}\n"
        f"📅 Total Events: {total_events}\n"
        f"🌐 Language: {lang.upper()}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")

# ---------------- Main -----------------
from flask import Flask
import threading, os, asyncio

def main():
    BOT_TOKEN = "8271513610:AAGnLvMUtIBnxRiNfOnIqRJOoy1xqwqtfio"

    if not BOT_TOKEN:
        print("❌ Please set BOT_TOKEN environment variable or edit script")
        return

    # Database initialize
    init_db()

    # Create bot
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    job_queue = app.job_queue

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CallbackQueryHandler(callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(ChatMemberHandler(my_chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

    # Reminder job
    if job_queue:
        job_queue.run_repeating(reminder_job, interval=60)

    print("✅ Bot is running... Press Ctrl+C to stop.")
    
    # Flask setup for Render
    web_app = Flask(__name__)

    @web_app.route('/')
    def home():
        return "Bot is running on Render!"

    # ✅ async-safe polling start
    async def run_tg():
        await app.initialize()
        await app.start()
        print("🤖 Bot polling started...")
        await app.updater.start_polling()
        await asyncio.Event().wait()  # keep alive

    def start_asyncio_loop():
        asyncio.run(run_tg())

    threading.Thread(target=start_asyncio_loop).start()

    # Flask port open for Render detection
    web_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


if __name__ == "__main__":
    main()
