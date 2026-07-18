import asyncio
import os
import re
import random
import urllib.request
import json
import time
import unicodedata 
import html
from collections import deque
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from flask import Flask
from threading import Thread

# ==========================================
# 📝 CUSTOM LIVE WEB LOGGER
# ==========================================
bot_logs = deque(maxlen=100)
bot_status = "🟢 Starting up..."

def log_msg(msg, is_error=False):
    global bot_status
    timestamp = datetime.now().strftime("%H:%M:%S")
    if is_error:
        bot_status = "🔴 Error Detected (See logs below)"
    elif "running" in msg.lower() or "unlocked" in msg.lower():
        bot_status = "🟢 Online & Listening"
        
    color = "#ff4444" if is_error else "#00ff00"
    safe_msg = html.escape(msg)
    formatted_msg = f"<span style='color: #888;'>[{timestamp}]</span> <span style='color: {color};'>{safe_msg}</span>"
    bot_logs.append(formatted_msg)
    print(msg, flush=True)

# ==========================================
# 📚 DICTIONARY & JSON INJECTION
# ==========================================
log_msg("📚 Downloading English dictionary for SHIYUK...") 
try:
    url = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    VALID_WORDS = {w.decode('utf-8').strip().lower() for w in response.read().splitlines() if w.decode('utf-8').strip().isalpha()}
    log_msg(f"✅ Loaded {len(VALID_WORDS)} base words into memory.")
except Exception as e:
    log_msg(f"⚠️ Failed to download dictionary: {e}", is_error=True)
    VALID_WORDS = set()

JSON_DB_FILE = "verified_database.json"
if os.path.exists(JSON_DB_FILE):
    try:
        with open(JSON_DB_FILE, "r") as f:
            custom_data = json.load(f)
            added_count = 0
            if isinstance(custom_data, dict):
                words_to_add = [w for w, valid in custom_data.items() if valid]
            else:
                words_to_add = custom_data
            for word in words_to_add:
                if word not in VALID_WORDS:
                    VALID_WORDS.add(word)
                    added_count += 1
        log_msg(f"🧬 Injected {added_count} custom verified words from {JSON_DB_FILE}.")
    except Exception as e:
        log_msg(f"⚠️ Failed to load custom JSON: {e}", is_error=True)

# ==========================================
# 🌐 LIVE DASHBOARD SERVER
# ==========================================
app = Flask(__name__)
latest_diagnostic_report = ""

@app.route('/')
@app.route('/logs')
def display_dashboard():
    logs_html = "<br>".join(bot_logs)
    return f"""
    <html>
    <head>
        <title>SHIYUK Bot Dashboard</title>
        <meta http-equiv="refresh" content="10">
    </head>
    <body style='background-color:#121212; color:#d4d4d4; font-family:monospace; padding:20px;'>
        <h2 style='color:#ffffff;'>🤖 SHIYUK Multi-Agent Bot Dashboard</h2>
        <h3 style='color:#a0a0a0;'>Status: {bot_status}</h3>
        <hr style='border-color:#333;'>
        <div style='background-color:#000000; padding:15px; border-radius:5px; height:60vh; overflow-y:auto; border: 1px solid #333;'>
            {logs_html if logs_html else "Waiting for operations to start..."}
        </div>
        <br>
        <div style='background-color:#1e1e1e; padding:15px; border-radius:5px; border: 1px solid #333; color: #ffaa00;'>
            <b>Last Game Diagnostic:</b><br>
            <pre style='white-space: pre-wrap; font-family:monospace;'>{html.escape(latest_diagnostic_report) if latest_diagnostic_report else "No game eliminated yet."}</pre>
        </div>
    </body>
    </html>
    """

def run_server():
    try:
        port = int(os.environ.get('PORT', 8080)) 
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        log_msg(f"ℹ️ Local Port Note: Web server failed to bind. Error: {e}", is_error=True)

Thread(target=run_server, daemon=True).start()

# ==========================================
# 🤖 BOT CONFIGURATION & API KEYS
# ==========================================
API_ID = 27611951
API_HASH = '16c265ac1d31f819b7dd53ce3b3602af'
MY_USERNAME = "shiyuk"  

CHAIN_GAME_BOT = "on9wordchainbot"   
SEEK_GAME_BOT = "WordSeekBot"

SESSION_STRING = "1BVtsOKEBu5Jq4tjBq2uE0Sien_EERny55smk_vXPcLfiZwpB5yZpdB5kGvtEJSrQMG-wHELvXMrt10ogiUcTfxU55e7qjxlLOyKeRafQiqDM7ZiS73J_PhMHWKcSxJ3Mp_R4e5pFFqMlYkld079Um1gg9rqgTY-NRLQCmuYZ7gPq2aDaJePNwCZvyYmqOIdhTUZEEy07i1ctx46_MkYpLNRupujovUnZYD3aXsaLsvzi9L1GRl3m6v-8V8LtK04piu3GACe4iWEM606XuWnXW6JwfPJwGHy9kY-O-g9TSPw5ecB13rlGIJA7i_HRBk0JVxiHygjoikT0Rf1-E25U1OJlK0GhJ-o="

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==========================================
# 🟩 AGENT 1: WORDSEEK (V42 PASSIVE TRACKER)
# ==========================================
wordseek_state = {}

def get_wordseek_state(chat_id):
    if chat_id not in wordseek_state:
        wordseek_state[chat_id] = {
            "active": False,
            "length": 5,
            "pool": [],
            "processed_feedback": set(),
            "authorized": False,
            "last_auth_time": 0,
            "match_id": 0  # 🔥 Tracks exact match to prevent ghost guesses
        }
    return wordseek_state[chat_id]

def wipe_wordseek_memory(chat_id):
    wordseek_state[chat_id] = {
        "active": False,
        "length": 5,
        "pool": [],
        "processed_feedback": set(),
        "authorized": False,
        "last_auth_time": 0,
        "match_id": 0
    }

@client.on(events.NewMessage(outgoing=True))
async def user_command_monitor(event):
    chat_id = event.chat_id
    text = event.raw_text.strip().lower()
    
    if text in ["wait", "play"] or text.startswith("/new"):
        state = get_wordseek_state(chat_id)
        state["authorized"] = True
        state["last_auth_time"] = time.time()
        log_msg(f"🔓 WordSeek Gate Unlocked via trigger: '{text}'")

        # 🔥 INSTANT JOIN: If passive mode already shrunk the pool, guess immediately!
        if state["active"] and state["pool"]:
            next_guess = random.choice(state["pool"])
            log_msg(f"⚡ Instant Join! Using passive memory (Pool: {len(state['pool'])}). Guessing: {next_guess}")
            state["pool"].remove(next_guess)
            # Use a tiny 1-second delay because we are hijacking an active game
            asyncio.create_task(execute_wordseek_guess(chat_id, next_guess, 1.0, state["match_id"]))

    if text.startswith("/end") or text.startswith("/lock"):
        wipe_wordseek_memory(chat_id)
        log_msg(f"🔒 WordSeek Gate manually wiped & locked.")

def filter_wordseek_pool(pool, guess, feedback):
    new_pool = []
    for word in pool:
        valid = True
        word_chars = list(word)
        
        for i, (g_char, f) in enumerate(zip(guess, feedback)):
            if f == 'G':
                if word[i] != g_char:
                    valid = False
                    break
                word_chars[i] = None 
        
        if not valid: continue
        
        for i, (g_char, f) in enumerate(zip(guess, feedback)):
            if f == 'Y':
                if word[i] == g_char: 
                    valid = False
                    break
                if g_char in word_chars:
                    word_chars[word_chars.index(g_char)] = None 
                else:
                    valid = False 
                    break
                    
        if not valid: continue
        
        for i, (g_char, f) in enumerate(zip(guess, feedback)):
            if f == 'R':
                if g_char in word_chars: 
                    valid = False
                    break
                    
        if valid:
            new_pool.append(word)
            
    return new_pool

async def execute_wordseek_guess(chat_id, guess, delay, match_id):
    try:
        # 1. Wait the human delay before acting
        await asyncio.sleep(delay)
        
        # 2. 🔥 GHOST CHECK: Did the game end or wipe while we were sleeping?
        state = get_wordseek_state(chat_id)
        if not state["active"] or state["match_id"] != match_id:
            log_msg(f"🛑 Aborted ghost guess '{guess}'. Match ended while sleeping.")
            return

        # 3. If still valid, type and send
        async with client.action(chat_id, 'typing'):
            await asyncio.sleep(1.0)
        await client.send_message(chat_id, guess)
    except Exception as e:
        log_msg(f"⚠️ Failed to send WordSeek guess: {e}", is_error=True)

@client.on(events.NewMessage(from_users=SEEK_GAME_BOT))
async def wordseek_handler(event):
    chat_id = event.chat_id
    text = unicodedata.normalize('NFKC', event.raw_text)
    state = get_wordseek_state(chat_id)
    
    # 🛑 1. WIN / END DETECTION (Checks this before doing any grid math)
    # 🔥 Expanded to match your screenshot perfectly ("guessed it correctly")
    end_triggers = [
        "game over", "won the game", "the word was", 
        "game ended", "ended the game", "time's up",
        "time is up", "guessed the word", "guessed it correctly",
        "congrats!", "correct word:"
    ]
    if any(trigger in text.lower() for trigger in end_triggers):
        log_msg("🛑 WordSeek Match Concluded. Wiping memory and killing tasks.")
        wipe_wordseek_memory(chat_id)
        return

    # 🧩 2. NEW MATCH DETECTION
    start_match = re.search(r'Guess the (\d+)-letter word', text, re.IGNORECASE)
    if start_match:
        time_since_auth = time.time() - state.get("last_auth_time", 0)
        if time_since_auth > 30:
            state["authorized"] = False

        length = int(start_match.group(1))
        state["active"] = True
        state["length"] = length
        state["pool"] = [w for w in VALID_WORDS if len(w) == length]
        state["processed_feedback"] = set()
        state["match_id"] = time.time() # 🔥 Assign unique ID to this match
        log_msg(f"🧩 WordSeek Match Detected! Target Length: {length}.")
        
        if not state["authorized"]:
            log_msg("🕵️ Passive Tracking Engaged. Tracking pool silently.")
            return
            
        first_guess = random.choice(state["pool"])
        state["pool"].remove(first_guess)
        
        human_delay = random.choice([1.0, 2.0, 3.0])
        asyncio.create_task(execute_wordseek_guess(chat_id, first_guess, human_delay, state["match_id"]))
        return

    # 📊 3. GRID & FEEDBACK PROCESSING (Passive Tracking is now allowed here)
    if "mode" in text.lower() and any(e in text for e in ['🟥', '🟨', '🟩']):
        if not state["active"]:
            lines = text.split('\n')
            for line in lines:
                if '🟥' in line or '🟨' in line or '🟩' in line:
                    words = re.findall(r'[a-zA-Z]+', line)
                    if words:
                        length = len(words[-1])
                        state["active"] = True
                        state["length"] = length
                        state["pool"] = [w for w in VALID_WORDS if len(w) == length]
                        state["processed_feedback"] = set()
                        state["match_id"] = time.time() # Bind ID if caught mid-game
                        break
        
        if not state["active"]: return

        if '🟩'*state["length"] in text:
            log_msg("🏆 WordSeek Grid Solved! Wiping memory.")
            wipe_wordseek_memory(chat_id) 
            return

        lines = [line.strip() for line in text.split('\n') if any(e in line for e in ['🟥', '🟨', '🟩'])]
        
        for line in lines:
            feedback = []
            for char in line:
                if char == '🟩': feedback.append('G')
                elif char == '🟨': feedback.append('Y')
                elif char == '🟥': feedback.append('R')
                
            words = re.findall(r'[a-zA-Z]+', line)
            if not words: continue
            guess_word = words[-1].lower()
            
            if len(feedback) != state["length"] or len(guess_word) != state["length"]: continue
            if guess_word in state["processed_feedback"]: continue 
            
            state["processed_feedback"].add(guess_word)
            state["pool"] = filter_wordseek_pool(state["pool"], guess_word, feedback)

        # 🚀 4. ACTION PHASE
        if state["pool"]:
            if state["authorized"]:
                next_guess = random.choice(state["pool"])
                log_msg(f"🎯 WordSeek Thinking... Pool reduced to {len(state['pool'])}. Guessing: {next_guess}")
                state["pool"].remove(next_guess) 
                human_delay = random.choice([1.0, 2.0, 3.0])
                asyncio.create_task(execute_wordseek_guess(chat_id, next_guess, human_delay, state["match_id"]))
            else:
                log_msg(f"🕵️ Passive Tracker: Pool reduced to {len(state['pool'])}.")
        else:
            if state["authorized"]:
                log_msg("❌ WordSeek Dictionary Exhausted!", is_error=True)
            wipe_wordseek_memory(chat_id)

# ==========================================
# ⛓️ AGENT 2: WORDCHAIN ENGINE (FRIENDLY MODE)
# ==========================================
active_games = {}

def get_game_state(chat_id):
    if chat_id not in active_games:
        active_games[chat_id] = {
            "current_constraints": "",
            "used_words": set(),
            "last_submitted_word": "",
            "my_turn": False,
            "turn_start_time": 0,
            "diagnostic_reason": "Waiting for a game to start...", 
            "word_ledger": {} 
        }
    return active_games[chat_id]

def update_dashboard(chat_id, state):
    global latest_diagnostic_report
    report = f"❌ CAUSE OF DEATH: {state['diagnostic_reason']}\n\n📊 WORD LEDGER:\n"
    if not state["word_ledger"]: report += "> No words played.\n"
    else:
        for letter in sorted(state["word_ledger"].keys()):
            report += f"- [{letter.upper()}]: {', '.join(state['word_ledger'][letter])}\n"
    latest_diagnostic_report = report
    log_msg(f"💀 Elimination Logged: {state['diagnostic_reason']}", is_error=True)

async def submit_word(chat_id, constraints, state, is_retry=False):
    if not is_retry: state["turn_start_time"] = time.time()
        
    try:
        state["diagnostic_reason"] = "Processing rules and scanning local dictionaries."
        
        start_match = re.search(r'start with ([a-z])', constraints, re.IGNORECASE)
        length_matches = re.findall(r'at least (\d+) letters', constraints, re.IGNORECASE)
        include_match = re.search(r'(?:include|contain)\s+(?!at\s+least)([a-z,\s]+?)(?:\s+and|\.|$)', constraints, re.IGNORECASE)
        exclude_match = re.search(r'exclude\s+([a-z,\s]+?)(?:\s+and|\.|$)', constraints, re.IGNORECASE)

        s_char = start_match.group(1).lower() if start_match else ""
        min_len = int(length_matches[-1]) if length_matches else 1
        i_chars = set(re.findall(r'\b([a-z])\b', include_match.group(1).lower())) if include_match else set()
        e_chars = set(re.findall(r'\b([a-z])\b', exclude_match.group(1).lower())) if exclude_match else set()
        
        valid_options = []
        for w in VALID_WORDS:
            if s_char and not w.startswith(s_char): continue
            if len(w) < min_len: continue
            if i_chars and not all(c in w for c in i_chars): continue
            if e_chars and any(c in w for c in e_chars): continue
            if w in state["used_words"]: continue
            valid_options.append(w)
                
        if valid_options:
            preferred_len_limit = min_len + 3 
            casual_options = [w for w in valid_options if len(w) <= preferred_len_limit]
            
            if casual_options:
                word = random.choice(casual_options)
            else:
                word = random.choice(valid_options)

            delay = 1.0 if is_retry else random.choice([4.0, 5.0, 6.0])
            elapsed = time.time() - state["turn_start_time"]
            
            state["diagnostic_reason"] = f"TIMEOUT: Selected '{word}', ran out of time ({elapsed:.1f}s elapsed)."
            
            try:
                async with client.action(chat_id, 'typing'):
                    await asyncio.sleep(delay)
            except FloodWaitError as e:
                log_msg(f"⚠️ Telegram Rate Limit Hit: {e}", is_error=True)
                return

            state["last_submitted_word"] = word 
            state["diagnostic_reason"] = f"DELIVERY FAILURE: Sent '{word}', but Telegram failed to deliver."
            
            try:
                await client.send_message(chat_id, word)
                log_msg(f"🏹 PLAYED (Friendly): {word} (Len: {len(word)}, Ends: {word[-1].upper()})")
            except Exception as e:
                log_msg(f"⚠️ Failed to send WordChain guess: {e}", is_error=True)
                return
                
            letter_key = word[0].upper()
            if letter_key not in state["word_ledger"]: state["word_ledger"][letter_key] = []
            state["word_ledger"][letter_key].append(f"{word} (≥{min_len})")
            
            state["diagnostic_reason"] = f"GAME BOT DELAY: Sent '{word}'. Waiting for validation."
        else:
            state["diagnostic_reason"] = f"DICT EXHAUSTION: No valid words remain. Constraints: Start='{s_char}', Min={min_len}, Inc={i_chars}, Exc={e_chars}."
            log_msg(state["diagnostic_reason"], is_error=True)
            
    except Exception as e:
        state["diagnostic_reason"] = f"INTERNAL ENGINE CRASH: {e}"
        log_msg(state["diagnostic_reason"], is_error=True)

@client.on(events.NewMessage(from_users=CHAIN_GAME_BOT))
async def chain_game_handler(event):
    chat_id = event.chat_id
    state = get_game_state(chat_id)
    bot_text = event.raw_text.lower().replace('\n', ' ').replace('\r', ' ')
    
    if "is accepted." in bot_text:
        accepted_word = bot_text.split(" is accepted.")[0].split()[-1].strip()
        accepted_word = ''.join(filter(str.isalpha, accepted_word))
        state["used_words"].add(accepted_word)
        
    if "turn:" in bot_text:
        state["current_constraints"] = bot_text 
        target_phrase = f"turn: {MY_USERNAME.lower()}"
        
        if target_phrase in bot_text:
            state["my_turn"] = True
            log_msg(f"🔔 Turn Detected: Analyzing constraints...")
            asyncio.create_task(submit_word(chat_id, bot_text, state, is_retry=False))
        else:
            state["my_turn"] = False

    error_phrases = [
        "has been used", "not a valid word", "invalid", 
        "not in my list of words", "has less than",      
        "does not include", "does not contain", "banned letters", "contains banned", "does not start with"
    ]
    
    if any(phrase in bot_text for phrase in error_phrases):
        last_word = state.get("last_submitted_word", "").lower()
        if state["my_turn"] and last_word and last_word in bot_text:
            new_len_match = re.search(r'less than (\d+)', bot_text)
            if new_len_match:
                new_len = new_len_match.group(1)
                state["current_constraints"] += f" at least {new_len} letters"

            state["used_words"].add(last_word)
            state["diagnostic_reason"] = f"REJECTION LOOP: Bot rejected '{last_word}'. Attempting recovery."
            log_msg(f"⛔ Word Rejected: {last_word}. Attempting recovery...", is_error=True)
            state["last_submitted_word"] = "" 
            asyncio.create_task(submit_word(chat_id, state["current_constraints"], state, is_retry=True))

    if "eliminated" in bot_text or "game over" in bot_text or "winner" in bot_text:
        if MY_USERNAME.lower() in bot_text or "game over" in bot_text:
            update_dashboard(chat_id, state)
        state["used_words"].clear()
        state["last_submitted_word"] = ""
        state["word_ledger"].clear()
        state["my_turn"] = False
        log_msg("🏁 WordChain Game Concluded. Memory wiped.")

log_msg(f"🚀 V42 Passive Tracker Engine ({MY_USERNAME}) is running!")
client.start()
client.run_until_disconnected()
