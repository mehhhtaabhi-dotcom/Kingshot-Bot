import os
import discord
from discord.ext import commands, tasks
from google import genai
from google.genai import types
import asyncio
import time
import datetime as dt_lib
from datetime import datetime, time as dt_time, timezone, timedelta
from flask import Flask
from threading import Thread
import requests
from icalendar import Calendar

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

# --- 3. DYNAMIC CLOUD ROUTER, CALENDAR & CACHE ---
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
        return "files/m2vqx2bq57bu" # alliance_rule.txt
    elif any(w in msg for w in keywords_tactics):
        return "files/m2vqx2bq57bu" 
    elif any(w in msg for w in keywords_stats):
        return "files/0o9zm65f7mjg" # Base stats Structure.txt
    elif any(w in msg for w in keywords_skills):
        return "files/fz52aprh8rso" # Skill sets.txt
    elif any(w in msg for w in keywords_upgrade):
        return "files/gvsdjnjdb96b" # Upgrade requirements for heroes.txt
    elif any(w in msg for w in keywords_acquire):
        return "files/39vqs1sf1tch" # Acquisition Methods.txt
    elif any(w in msg for w in keywords_lore):
        return "files/hc1247j4ayzs" # Lore & Backstory.txt
    else:
        return "files/8d6uq3g9sbbc" # Kingshot_heroes.txt (Default)

def get_upcoming_events():
    try:
        url = "https://calendar.google.com/calendar/ical/e6196c2703be23e87e027067c77f8990c4434a659a08fc9c3612f60c83b42c0e%40group.calendar.google.com/public/basic.ics"
        response = requests.get(url, timeout=5)
        cal = Calendar.from_ical(response.text)
        
        now = datetime.now(timezone.utc)
        events = []
        
        for component in cal.walk('vevent'):
            summary = str(component.get('summary'))
            start = component.get('dtstart').dt
            end = component.get('dtend').dt if component.get('dtend') else None
            
            # Unify date and datetime formats for safe comparison
            if type(start) is dt_lib.date:
                start = dt_lib.datetime.combine(start, dt_lib.datetime.min.time()).replace(tzinfo=timezone.utc)
            elif start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
                
            if end:
                if type(end) is dt_lib.date:
                    end = dt_lib.datetime.combine(end, dt_lib.datetime.min.time()).replace(tzinfo=timezone.utc)
                elif end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
            
            # Filter: Only keep active events or events in the next 14 days
            if end and end > now and (start - now).days <= 14:
                events.append({"name": summary, "start": start, "end": end})
            elif not end and start > now and (start - now).days <= 14:
                events.append({"name": summary, "start": start, "end": None})
        
        events.sort(key=lambda x: x['start'])
        
        output = []
        for e in events[:15]: 
            start_str = e['start'].strftime("%b %d, %H:%M UTC")
            end_str = e['end'].strftime("%b %d, %H:%M UTC") if e['end'] else "TBD"
            output.append(f"• {e['name']}: {start_str} to {end_str}")
            
        return "\n".join(output) if output else "No upcoming events scheduled in the next 14 days."
    except Exception as e:
        print(f"Calendar Fetch Error: {e}")
        return "Live calendar data is temporarily offline."

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
    print(f"👑 Zeus is online, anchored on Render.")
    print(f"⚡ Core: Gemini 2.5 Flash-Lite (250K TPM / 10 RPM limit active).")
    print(f"🛡️ Memory Cache & Event Feeds: ONLINE.")
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
            meta_keywords = ["knowledge", "what can you do", "help", "menu", "who are you", "features", "what model"]
            if any(w in user_text.lower() for w in meta_keywords):
                menu = (
                    "🛡️ **ZEUS TACTICAL DATABANKS** 🛡️\n"
                    "I am the KNG Spartan Rage AI, currently powered by the **Gemini 2.5 Flash-Lite** core.\n"
                    "To access my cloud databanks, ask me about:\n\n"
                    "• **Alliance Directives:** Ask about *rules, missions,* or *Kratos*.\n"
                    "• **Tactics & Schedules:** Ask about *events, calendars, formations,* or *strategy*.\n"
                    "• **Hero Stats:** Ask about *health, attack, defense,* or *expedition*.\n"
                    "• **Hero Skills:** Ask about *skills, abilities, stuns,* or *heals*.\n"
                    "• **Upgrades:** Ask about *star levels, tiers,* or *upgrade costs*.\n"
                    "• **Acquisition:** Ask about *how to get, unlock,* or *recruit* heroes.\n"
                    "• **Lore:** Ask about a hero's *lore, backstory,* or *history*.\n\n"
                    "*(Commander Kratos can also DM me commands via natural language!)*\n\n"
                    "*Example:* `What events are happening tomorrow?`"
                )
                await message.channel.send(menu)
                return

            async with message.channel.typing():
                if is_private_dm and any(w in user_text.lower() for w in ["schedule", "event timer", "remind", "set", "broadcast", "announce", "send"]):
                    try:
                        current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                        nlp_sys_instruct = (
                            f"You are Zeus's internal command parser running on Gemini 2.5 Flash-Lite. The current time is {current_utc}. "
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

                cache_key = user_text.lower()
                time_sensitive_words = ["time", "reset", "when", "how long", "left", "until", "today", "now", "clock", "event", "calendar", "upcoming", "tomorrow", "schedule"]
                is_time_sensitive = any(w in cache_key for w in time_sensitive_words)
                is_event_query = any(w in cache_key for w in ["event", "calendar", "upcoming", "tomorrow", "schedule"])
                
                if not is_time_sensitive and cache_key in response_cache:
                    await message.channel.send(response_cache[cache_key])
                    return

                try:
                    target_file_id = get_cloud_file_id(user_text)
                    uploaded_file = client.files.get(name=target_file_id)
                except Exception as e:
                    print(f"File Retrieval Error: {e}")
                    uploaded_file = None
                
                # Fetch calendar data silently if the user is asking about events
                calendar_context = ""
                if is_event_query:
                    cal_data = get_upcoming_events()
                    calendar_context = f"\n\nLIVE KINGSHOT EVENT CALENDAR DATA (Use this to answer scheduling questions):\n{cal_data}"
                
                current_live_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                sys_instruct = (
                    f"You are Zeus, the loyal, cooperative, and conversational tactical AI assistant for KNG Spartan Rage. "
                    f"Speak naturally and politely like a helpful human alliance member, while keeping a loyal Spartan flavor. "
                    f"If asked what model you are running on, confirm you are powered by the Gemini 2.5 Flash-Lite core. "
                    f"If a user says hello, greet them warmly. If they say they don't need help, reply naturally (e.g., 'Understood, let me know if you need anything!'). "
                    f"The current live server time is {current_live_utc}. The Kingshot global daily reset occurs at exactly 00:00 UTC. "
                    f"If asked, use the current time to calculate the exact hours and minutes remaining until the reset. "
                    f"IMPORTANT: Answer game queries accurately based on the provided document context. "
                    f"If the user asks a real-world question outside of game data, use the Google Search tool."
                    f"{calendar_context}"
                )
                
                config = types.GenerateContentConfig(
                    system_instruction=sys_instruct,
                    tools=[{"google_search": {}}],
                    safety_settings=[
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    ]
                )
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        contents_payload = [uploaded_file, user_text] if uploaded_file else [user_text]
                        
                        response = await client.aio.models.generate_content(
                            model='gemini-2.5-flash-lite',
                            contents=contents_payload,
                            config=config
                        )
                        
                        if response.text:
                            if not is_time_sensitive:
                                response_cache[cache_key] = response.text
                            await message.channel.send(response.text)
                        else:
                            await message.channel.send("⚠️ Zeus returned an empty response.")
                            
                        break  
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "503" in error_msg or "UNAVAILABLE" in error_msg:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2)
                                continue
                            else:
                                await message.channel.send("📡 **Comms Jammed:** Google's AI servers are currently overloaded. Please try again in a minute, Spartan.")
                                break
                        elif "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                            await message.channel.send("⏳ **Comms Jammed:** I am receiving too many tactical requests at once. Please wait 60 seconds and ask me again.")
                            break
                        else:
                            await message.channel.send(f"❌ Systems Error: {error_msg}")
                            break

# --- 6. IGNITION ---
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    bot.run(TOKEN)
