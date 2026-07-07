import datetime
import os
import time
import sys
import aiohttp
import requests 
from threading import Thread
import discord
from discord import app_commands
from discord.ext import tasks
from flask import Flask
from google import genai
from google.genai import types 

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ANNOUNCEMENT_CHANNEL_ID = 1500543041625129122
BASE_URL = "https://kingshot.net/api"  
# =======================================================

app = Flask("")

@app.route("/")
def home():
    return "Kingshot AI Bot is awake!"

def run_server():
    app.run(host="0.0.0.0", port=8080)

# Configure the AI Brain
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# =======================================================
# --- GEMINI AI TOOLS (FUNCTION CALLING) ---
# =======================================================
def get_gift_codes() -> str:
    """Fetches all currently active KingShot gift codes."""
    try:
        res = requests.get(f"{BASE_URL}/gift-codes", timeout=5)
        if res.status_code == 200:
            codes = res.json().get("data", {}).get("giftCodes", [])
            return str(codes) if codes else "No active codes."
        return "Failed to fetch codes."
    except Exception:
        return "API connection error."

def get_player_data(player_id: str) -> str:
    """Fetches live player data by Account ID."""
    try:
        res = requests.get(f"{BASE_URL}/player-info?playerId={player_id}", timeout=5)
        if res.status_code == 200:
            return str(res.json().get("data", {}))
        return "Player not found."
    except Exception:
        return "API connection error."

def get_kvk_history(kingdom_id: int) -> str:
    """Fetches latest KvK war records for a kingdom."""
    try:
        res1 = requests.get(f"{BASE_URL}/kvk/matches?kingdom_a={kingdom_id}&limit=1", timeout=5)
        if res1.status_code == 200 and res1.json().get("data"):
            return str(res1.json()["data"][0])
        return "No recent KvK data."
    except Exception:
        return "API connection error."

class KingshotAllianceBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.active_schedules = []
        try:
            with open("spartan_knowledge.txt", "r") as f:
                self.knowledge_base = f.read()
        except FileNotFoundError:
            self.knowledge_base = "No knowledge base found."

    async def setup_hook(self):
        self.check_game_events.start()

    async def on_ready(self):
        print(f"👑 Kingshot AI is online as {self.user}!")
        # Syncing removed from here to prevent 429 errors. 
        # Manually sync only when adding new slash commands.

    async def on_message(self, message):
        if message.author.bot: return
        if self.user in message.mentions or isinstance(message.channel, discord.DMChannel):
            user_text = message.content.replace(f'<@{self.user.id}>', '').strip()
            async with message.channel.typing():
                try:
                    # Using the latest Gemini model
                    response = ai_client.models.generate_content(
                        model='gemini-2.0-flash-001',
                        contents=user_text,
                        config=types.GenerateContentConfig(
                            system_instruction=f"You are Zeus, AI for KNG Spartan Rage. Use tools: {self.knowledge_base}",
                            tools=[get_gift_codes, get_player_data, get_kvk_history],
                            temperature=0.7
                        )
                    )
                    await message.channel.send(response.text)
                except Exception as e:
                    await message.channel.send("❌ Connection interrupted.")
                    print(f"AI Error: {e}")

    @tasks.loop(seconds=60)
    async def check_game_events(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        for event in self.active_schedules[:]:
            if event["time"] == now.strftime("%H:%M"):
                channel = self.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                if channel: await channel.send(f"@everyone Event starting: {event['name']}")
                self.active_schedules.remove(event)

client = KingshotAllianceBot()

# --- IGNITION SEQUENCE ---
Thread(target=run_server, daemon=True).start()
client.run(TOKEN)
