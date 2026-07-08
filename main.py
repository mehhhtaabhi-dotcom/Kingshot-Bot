import os
import discord
from discord.ext import commands, tasks
from google import genai
from google.genai import types
import asyncio
import time
from datetime import datetime, time as dt_time, timezone
from flask import Flask
from threading import Thread

# --- 1. SECURE CONFIGURATION & CHANNEL MAPPING ---
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN or not GEMINI_API_KEY:
    print("❌ CRITICAL ERROR: Missing DISCORD_TOKEN or GEMINI_API_KEY in Render Environment Variables!")
    exit(1)

# Zeus's Internal Channel Directory
CHANNELS = {
    "guide": 1500550614889791730,
    "event_alert": 1522335245196726412,
    "alliance": 1500543041625129122,
    "alliance_events": 1500543041625129123,
    "gift_codes": 1500550108431781918
}

client = genai.Client()
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 2. THE UPTIMEROBOT WEB SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "👑 Zeus is awake and watching the gates!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- 3. THE DYNAMIC CLOUD ROUTER & MEMORY CACHE ---
# This dictionary acts as Zeus's short-term memory to protect API limits
response_cache = {}

def get_cloud_file_id(user_message):
    msg = user_message.lower()
    
    keywords_stats = ["stat", "attack", "defense", "def ", "health", "conquest", "expedition", "lethality"]
    keywords_skills = ["skill", "ability", "glorious mark", "combo", "passive", "special weapon", "stun", "aoe", "heal"]
    keywords_upgrade = ["upgrade", "star", "tier", "requirement", "table", "level up", "cost"]
    keywords_acquire = ["get", "acquire", "unlock", "find", "roulette", "governor", "recruitment", "pack", "shop", "shard"]
    keywords_lore = ["lore", "story", "backstory", "history", "background", "past", "who is"]
    keywords_tactics = ["bear", "hunt", "formation", "kvk", "tactic", "strategy"]
    
    if any(w in msg for w in ["alliance", "watchtower", "mission", "rule", "kratos"]):
        return "files/dk5ougy7c5qo" 
    elif any(w in msg for w in keywords_tactics):
        return "files/dk5ougy7c5qo" 
    elif any(w in msg for w in keywords_stats):
        return "files/y979bgfrjw1d" 
    elif any(w in msg for w in keywords_skills):
        return "files/qu4n6174euyr" 
    elif any(w in msg for w in keywords_upgrade):
        return "files/elwoka9a10b9" 
    elif any(w in msg for w in keywords_acquire):
        return "files/aat3flf0swyz" 
    elif any(w in msg for w in keywords_lore):
        return "files/m3g8qp0vn5p3" 
    else:
        return "files/v7n4tt3csbn3" 

# --- 4. THE TIMEKEEPER: AUTOMATED DAILY ALARMS ---
utc_warning = dt_time(hour=23, minute=50, tzinfo=timezone.utc)
utc_midnight = dt_time(hour=0, minute=0, tzinfo=timezone.utc)

@tasks.loop(time=utc_warning)
async def daily_reset_warning():
    target_channels = [CHANNELS["alliance"], CHANNELS["alliance_events"]]
    for channel_id in target_channels:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send("⚠️ **10-MINUTE WARNING!** The Global Day Reset is approaching (00:00 UTC). Wrap up your current missions!")

@tasks.loop(time=utc_midnight)
async def daily_reset_alert():
    target_channels = [CHANNELS["alliance"], CHANNELS["alliance_events"]]
    for channel_id in target_channels:
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(
                "🌅 **GLOBAL DAY RESET** 🌅\n"
                "Kingshot servers have refreshed (00:00 UTC). Daily Watchtower missions and events are now active. Get to work, Spartans!"
            )

async def run_event_timer(channel_id, hours, event_name, dm_channel):
    target_channel = bot.get_channel(channel_id)
    if not target_channel:
        await dm_channel.send(f"❌ Error: Could not locate the target channel to post the alert.")
        return

    seconds_total = int(hours * 3600)
    warning_seconds = seconds_total - 600  
    target_time = int(time.time()) + seconds_total

    await dm_channel.send(f"✅ AI Parsed Successfully! Event '{event_name}' locked in for <t:{target_time}:R>.")

    await target_channel.send(
        f"@everyone 📅 **UPCOMING EVENT: {event_name.upper()}**\n"
        f"🌍 **Local Start Time:** <t:{target_time}:F>\n"
        f"⏳ **Countdown:** <t:{target_time}:R>\n"
        f"*I will sound the 10-minute preparation warning.*"
    )

    if warning_seconds > 0:
        await asyncio.sleep(warning_seconds)
        await target_channel.send(f"@everyone ⚠️ **10-MINUTE WARNING!** Prepare for {event_name}! (<t:{target_time}:R>)")
        await asyncio.sleep(600)
    else:
        await asyncio.sleep(seconds_total)

    await target_channel.send(f"@everyone 🔥 **IT IS TIME! {event_name.upper()} HAS BEGUN!** Charge!")

# --- 5. DISCORD BOT ACTIONS ---
@bot.event
async def on_ready():
    print(f"👑 Zeus is online, anchored on Render, with API Caching active.")
    if not daily_reset_warning.is_running():
        daily_reset_warning.start()
    if not daily_reset_alert.is_running():
        daily_reset_alert.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    is_private_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user in message.mentions

    if is_private_dm or is_mentioned:
        user_text = message.content.replace(f'<@{bot.user.id}>', '').strip()
            
        if user_text:
            # 1. Directory Interceptor
            meta_keywords = ["knowledge", "what can you do", "help", "menu", "who are you", "features"]
            if any(w in user_text.lower() for w in meta_keywords):
                menu = (
                    "🛡️ **ZEUS TACTICAL DATABANKS** 🛡️\n"
                    "I am the KNG Spartan Rage AI. To access my cloud databanks, ask me about:\n\n"
                    "• **Alliance Directives:** Ask about *rules, missions,* or *Kratos*.\n"
                    "• **Tactics:** Ask about *bear hunt, formations,* or *strategy*.\n"
                    "• **Hero Stats:** Ask about *health, attack, defense,* or *expedition*.\n"
                    "• **Hero Skills:** Ask about *skills, abilities, stuns,* or *heals*.\n"
                    "• **Upgrades:** Ask about *star levels, tiers,* or *upgrade costs*.\n"
                    "• **Acquisition:** Ask about *how to get, unlock,* or *recruit* heroes.\n"
                    "• **Lore:** Ask about a hero's *lore, backstory,* or *history*.\n\n"
                    "*(Commander Kratos can also DM me commands via natural language!)*\n\n"
                    "*Example:* `What are the upgrade requirements for Ava?`"
                )
                await message.channel.send(menu)
                return

            async with message.channel.typing():
                # 2. NLP Command Interceptor
                if is_private_dm and any(w in user_text.lower() for w in ["schedule", "event", "timer", "remind", "set", "broadcast", "announce", "send"]):
                    try:
                        current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                        nlp_sys_instruct = (
                            f"You are Zeus's internal command parser. The current time is {current_utc}. "
                            "Read the user's text and detect if they want to SCHEDULE a timer OR BROADCAST a live message. "
                            "1. IF SCHEDULING: Extract Event Name, Hours (as float), and Target Channel Key. Output STRICTLY: SCHEDULE|Event Name|Hours|ChannelKey \n"
                            "2. IF BROADCASTING: Extract the exact message they want to broadcast, and the Target Channel Keys (comma separated). Output STRICTLY: BROADCAST|Message to send|ChannelKey1,ChannelKey2 \n"
                            "Available channel keys: 'event_alert', 'alliance_events', 'alliance', 'guide', 'gift_codes'. "
                            "If they do not specify a channel, default to 'alliance'. "
                            "If the text is just a normal question and NOT a command, output NO_COMMAND."
                        )
                        
                        config = types.GenerateContentConfig(system_instruction=nlp_sys_instruct)
                        parse_response = await client.aio.models.generate_content(
                            model='gemini-2.5-flash-lite',
                            contents=user_text,
                            config=config
                        )
                        
                        bot_reply = parse_response.text.strip()
                        
                        if bot_reply.startswith("SCHEDULE|"):
                            parts = bot_reply.split("|")
                            event_name = parts[1]
                            hours = float(parts[2])
                            channel_key = parts[3].strip()
                            target_id = CHANNELS.get(channel_key, CHANNELS["event_alert"])
                            asyncio.create_task(run_event_timer(target_id, hours, event_name, message.channel))
                            return 
                            
                        elif bot_reply.startswith("BROADCAST|"):
                            parts = bot_reply.split("|")
                            message_to_send = parts[1]
                            channel_keys = parts[2].split(",")
                            
                            success_channels = []
                            for key in channel_keys:
                                key = key.strip()
                                target_id = CHANNELS.get(key, CHANNELS["alliance"])
                                target_channel = bot.get_channel(target_id)
                                if target_channel:
                                    await target_channel.send(f"📢 **ALLIANCE BROADCAST:**\n{message_to_send}")
                                    success_channels.append(key)
                                    
                            await message.channel.send(f"✅ Message successfully broadcasted to: {', '.join(success_channels)}")
                            return

                    except Exception as e:
                        print(f"NLP Parser Error: {e}")

                # 3. Conversational RAG & Search Processing (WITH MEMORY CACHE)
                try:
                    cache_key = user_text.lower()
                    time_sensitive_words = ["time", "reset", "when", "how long", "left", "until", "today", "now", "clock"]
                    is_time_sensitive = any(w in cache_key for w in time_sensitive_words)
                    
                    # If the question was asked before AND it is not about time, use the cache to save API limits!
                    if not is_time_sensitive and cache_key in response_cache:
                        await message.channel.send(response_cache[cache_key])
                        return

                    # Otherwise, query Google Cloud File
                    target_file_id = get_cloud_file_id(user_text)
                    uploaded_file = client.files.get(name=target_file_id)
                    
                    current_live_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    sys_instruct = (
                        f"You are Zeus, the loyal, cooperative, and conversational tactical AI assistant for KNG Spartan Rage. "
                        f"Speak naturally and politely like a helpful human alliance member, while keeping a loyal Spartan flavor. "
                        f"If a user says hello, greet them warmly. If they say they don't need help, reply naturally (e.g., 'Understood, let me know if you need anything!'). "
                        f"The current live server time is {current_live_utc}. The Kingshot global daily reset occurs at exactly 00:00 UTC. "
                        f"If asked, use the current time to calculate the exact hours and minutes remaining until the reset. "
                        f"IMPORTANT: Answer game queries accurately based on the provided document context. "
                        f"If the user asks a real-world question outside of game data, use the Google Search tool."
                    )
                    
                    config = types.GenerateContentConfig(
                        system_instruction=sys_instruct,
                        tools=[{"google_search": {}}]
                    )
                    
                    response = await client.aio.models.generate_content(
                        model='gemini-2.5-flash-lite',
                        contents=[uploaded_file, user_text],
                        config=config
                    )
                    
                    if response.text:
                        # Save the new answer to the Memory Cache
                        if not is_time_sensitive:
                            response_cache[cache_key] = response.text
                        await message.channel.send(response.text)
                    else:
                        await message.channel.send("⚠️ Zeus returned an empty response.")
                except Exception as e:
                    await message.channel.send(f"❌ Gemini API Error: {str(e)}")

# --- 6. IGNITION ---
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    bot.run(TOKEN)
