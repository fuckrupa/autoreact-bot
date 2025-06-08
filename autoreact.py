import os
import requests
import json
import random
import threading
import time
from dotenv import load_dotenv

load_dotenv()

# ─── Load Environment Variables ────────────────────────────────────────────────

BOT_TOKENS = os.environ.get("BOT_TOKENS", "").split(",")
CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://t.me/example")
GROUP_URL = os.environ.get("GROUP_URL", "https://t.me/example_group")
EMOJIS = [
    "❤️", "👍", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉",
    "🤩", "🤮", "💩", "🙏", "👌", "🕊️", "🤡", "🥱", "🥴", "😍", "🐳", "❤️‍🔥",
    "🌚", "🌭", "💯", "🤣", "⚡", "🍌", "🏆", "💔", "🤨", "😐", "🍓", "🍾",
    "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈", "😇",
    "😨", "🤝", "✍️", "🤗", "🫡", "🎅", "🎄", "☃️", "💅", "🤪", "🗿", "🆒",
    "💘", "🙉", "🦄", "😘", "💊", "🙊", "😎", "👾", "🤷‍♂️", "🤷", "🤷‍♀️", "😡"
]

print(f"🔧 Loaded {len(BOT_TOKENS)} bot tokens")

# ─── Fetch Bot Username ────────────────────────────────────────────────────────

def get_bot_username(bot_token):
    try:
        print(f"📡 Fetching username for bot: {bot_token[:10]}...")
        resp = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=5)
        username = resp.json()["result"]["username"]
        print(f"✅ Bot username: @{username}")
        return username
    except Exception as e:
        print(f"❌ Failed to fetch username for token {bot_token[:10]}: {e}")
        return None

# ─── Setup Bot Command Menu ────────────────────────────────────────────────────

def set_commands(bot_token):
    commands = [{"command": "start", "description": "Show welcome message and commands"}]
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/setMyCommands",
            json={"commands": commands},
            timeout=5
        )
        print(f"✅ /start command set for bot {bot_token[:10]}")
    except Exception as e:
        print(f"❌ Error setting commands for bot {bot_token[:10]}: {e}")

# ─── Send /start Welcome Message ───────────────────────────────────────────────

def handle_start(bot_token, chat_id, bot_username):
    print(f"🚀 /start received in chat {chat_id} for @{bot_username}")
    text = (
        "👋 Hey there! I'm <b>ReactionBot</b>.\n\n"
        "I automatically react to messages in your group with fun and random emojis like ❤️🔥🎉👌.\n"
        "Just add me to your group and enjoy the reactions!\n"
        "P.S. I work best when I have a little admin magic 😉"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "Updates", "url": CHANNEL_URL},
                {"text": "Support", "url": GROUP_URL}
            ],
            [
                {
                    "text": "Add Me To Your Group",
                    "url": f"https://t.me/{bot_username}?startgroup=true"
                }
            ]
        ]
    }
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",  # Important to render <b>
        "reply_markup": keyboard
    }
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=5
        )
        print(f"✅ Welcome message sent to chat {chat_id}")
    except Exception as e:
        print(f"❌ Error sending start message for bot {bot_token[:10]}: {e}")

# ─── Reaction Logic ─────────────────────────────────────────────────────────────

def get_updates(bot_token, offset=None):
    params = {"timeout": 10, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    for attempt in range(3):
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{bot_token}/getUpdates",
                params=params,
                timeout=10
            )
            return r.json().get("result", [])
        except Exception as e:
            print(f"❌ Attempt {attempt+1}: Error fetching updates for bot {bot_token[:10]}: {e}")
            time.sleep(2)
    return []

def send_reaction(bot_token, chat_id, message_id, emoji):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reaction": json.dumps([{"type": "emoji", "emoji": emoji}])
    }
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/setMessageReaction",
            json=payload,
            timeout=5
        )
        print(f"✨ Reaction '{emoji}' sent to message {message_id} in chat {chat_id}")
    except Exception as e:
        print(f"❌ Failed to react: {e}")

def react_thread(bot_token, chat_id, message_id):
    emoji = random.choice(EMOJIS)
    print(f"🌀 Launching reaction thread with emoji: {emoji}")
    threading.Thread(
        target=send_reaction,
        args=(bot_token, chat_id, message_id, emoji),
        daemon=True
    ).start()

# ─── Worker for Each Bot ───────────────────────────────────────────────────────

def bot_worker(bot_token):
    bot_username = get_bot_username(bot_token)
    if not bot_username:
        print(f"⚠️ Skipping bot {bot_token[:10]} (username fetch failed)")
        return
    set_commands(bot_token)
    offset = None
    print(f"🤖 Bot @{bot_username} is running...")
    while True:
        updates = get_updates(bot_token, offset)
        for update in updates:
            offset = update.get("update_id", 0) + 1
            msg = update.get("message")
            if not msg:
                continue
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")
            message_id = msg.get("message_id")
            if text.strip().lower() == "/start":
                handle_start(bot_token, chat_id, bot_username)
                continue
            react_thread(bot_token, chat_id, message_id)
        time.sleep(0.1)

# ─── Main Loop ─────────────────────────────────────────────────────────────────

def main():
    threads = []
    for token in BOT_TOKENS:
        t = threading.Thread(
            target=bot_worker,
            args=(token.strip(),),
            daemon=True
        )
        t.start()
        threads.append(t)
        print(f"🧵 Started thread for bot {token[:10]}")
    for t in threads:
        t.join()

if __name__ == "__main__":
    main()