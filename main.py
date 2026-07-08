import os
import discord
from discord.ext import commands
from google import genai
from google.genai import types
import asyncio
import time
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION ---
TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLIANCE_CHANNEL_ID = 123456789012345678  # Paste your 18-digit channel ID here

if not TOKEN or not GEMINI_API_KEY:
    print("❌ CRITICAL ERROR: Missing DISCORD_TOKEN or GEMINI_API_KEY in Render Environment Variables!")
    exit(1)

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

# --- 3. THE DYNAMIC CLOUD ROUTER ---
def get_cloud_file_id(user_message):
    msg = user_message.lower()
    
    keywords_stats = ["stat", "attack", "defense", "def ", "health", "conquest", "expedition", "lethality"]
    keywords_skills = ["skill", "ability", "glorious mark", "combo", "passive", "special weapon", "stun", "aoe", "heal"]
    keywords_upgrade = ["upgrade", "star", "tier", "requirement", "table", "level up", "cost"]
    keywords_acquire = ["get", "acquire", "unlock", "find", "roulette", "governor", "recruitment", "pack", "shop", "shard"]
    keywords_lore = ["lore", "story", "backstory", "history", "background", "past", "who is"]
    keywords_tactics = ["bear", "hunt", "formation", "kvk", "tactic", "strategy"]
    
    if any(w in msg for w in ["alliance", "watchtower", "mission", "rule", "kratos"]):
        return "files/dk5ougy7c5qo" # alliance_rule.txt
    elif any(w in msg for w in keywords_tactics):
        return "files/dk5ougy7c5qo" # Temporarily routes to alliance_rules until Bear Hunt data is uploaded
    elif any(w in msg for w in keywords_stats):
        return "files/y979bgfrjw1d" # Base stats Structure.txt
    elif any(w in msg for w in keywords_skills):
        return "files/qu4n6174euyr" # Skill sets.txt
    elif any(w in msg for w in keywords_upgrade):
        return "files/elwoka9a10b9" # Upgrade requirements.txt
    elif any(w in msg for w in keywords_acquire):
        return "files/aat3flf0swyz" # Acquisition Methods.txt
    elif any(w in msg for w in keywords_lore):
        return "files/m3g8qp0vn5p3" # Lore & Backstory.txt
    else:
        return "files/v7n4tt3csbn3" # Kingshot_heroes.txt (Default)

# --- 4. DISCORD BOT ACTIONS ---
@bot.event
async def on_ready():
    print(f"👑 Zeus is online, routed to Google Cloud, and anchored on Render!")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(ALLIANCE_CHANNEL_ID)
    if channel:
        welcome_message = (
            f"🛡️ **Welcome to KNG Spartan Rage, {member.mention}!**\n"
            f"Prepare for battle. I am Zeus, the alliance AI. If you need to check our rules or hero profiles, just ping `@Zeus`!"
        )
        await channel.send(welcome_message)

@bot.command()
async def remind(ctx, hours: float, *, event_name: str):
    channel = bot.get_channel(ALLIANCE_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Error: Alliance Channel ID is missing or incorrect.")
        return

    seconds_total = int(hours * 3600)
    warning_seconds = seconds_total - 300
    target_time = int(time.time()) + seconds_total

    await channel.send(
        f"@everyone ⚔️ **ALLIANCE ALERT: {event_name.upper()}**\n"
        f"Event begins in **<t:{target_time}:R>**! (<t:{target_time}:t>)\n"
        f"*I will sound the 5-minute warning.*"
    )
    
    # Check if the command was sent in a DM or a server channel
    if isinstance(ctx.channel, discord.DMChannel):
        await ctx.send(f"✅ Timer set for {hours} hours. I will notify the alliance channel.")
    else:
        await ctx.send(f"✅ Timer set for {hours} hours.")

    if warning_seconds > 0:
        await asyncio.sleep(warning_seconds)
        await channel.send(f"@everyone ⚠️ **5-MINUTE WARNING!** Prepare for {event_name}! (<t:{target_time}:R>)")
        await asyncio.sleep(300)
    else:
        await asyncio.sleep(seconds_total)

    await channel.send(f"@everyone 🔥 **IT IS TIME! {event_name.upper()} HAS BEGUN!** Charge!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check if it is a Private DM OR if Zeus is mentioned in a server
    is_private_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user in message.mentions

    if is_private_dm or is_mentioned:
        # Clean the text if he was mentioned
        user_text = message.content.replace(f'<@{bot.user.id}>', '').strip()
        
        if user_text:
            # The Directory Interceptor
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
                    "*Example:* `What are the upgrade requirements for Ava?`"
                )
                await message.channel.send(menu)
                return

            async with message.channel.typing():
                try:
                    target_file_id = get_cloud_file_id(user_text)
                    uploaded_file = client.files.get(name=target_file_id)
                    
                    sys_instruct = (
                        "You are Zeus, the specialized tactical assistant for KNG Spartan Rage. "
                        "IMPORTANT: Answer the query accurately based ONLY on the provided document context. "
                        "Do not invent stats, rules, or tactics."
                    )
                    config = types.GenerateContentConfig(system_instruction=sys_instruct)
                    
                    response = await client.aio.models.generate_content(
                        model='gemini-2.5-flash-lite',
                        contents=[uploaded_file, user_text],
                        config=config
                    )
                    
                    if response.text:
                        await message.channel.send(response.text)
                    else:
                        await message.channel.send("⚠️ Zeus returned an empty response.")
                except Exception as e:
                    await message.channel.send(f"❌ Gemini API Error: {str(e)}")
    
    await bot.process_commands(message)

# --- 5. IGNITION ---
if __name__ == "__main__":
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    bot.run(TOKEN)
