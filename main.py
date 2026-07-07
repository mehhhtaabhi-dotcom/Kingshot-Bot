import datetime
import os
import time
import sys
import aiohttp
import requests  # ---> ADDED FOR FUNCTION CALLING
from threading import Thread
import discord
from discord import app_commands
from discord.ext import tasks
from flask import Flask
from google import genai
from google.genai import types  # ---> ADDED FOR FUNCTION CALLING

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

# Configure the NEW AI Brain
ai_client = genai.Client(api_key=GEMINI_API_KEY)


# =======================================================
# --- GEMINI AI TOOLS (FUNCTION CALLING) ---
# =======================================================
def get_gift_codes() -> str:
    """Fetches all currently active KingShot gift codes and their expiration dates. Use this when asked for loot, codes, or rewards."""
    try:
        res = requests.get(f"{BASE_URL}/gift-codes")
        if res.status_code == 200:
            codes = res.json().get("data", {}).get("giftCodes", [])
            return str(codes) if codes else "No active codes right now."
        return "Failed to fetch codes."
    except Exception:
        return "API connection error."

def get_player_data(player_id: str) -> str:
    """Fetches live player data (name, kingdom, level) using their numerical KingShot Account ID. Use this to verify players."""
    try:
        res = requests.get(f"{BASE_URL}/player-info?playerId={player_id}")
        if res.status_code == 200:
            return str(res.json().get("data", {}))
        elif res.status_code == 429:
            return "Rate limited (Max 6 per minute). Tell the user to wait a moment."
        return "Player not found."
    except Exception:
        return "API connection error."

def get_kvk_history(kingdom_id: int) -> str:
    """Fetches the latest Kingdom vs Kingdom (KvK) war records for a specific server/kingdom number. Use this to check war history or castle captures."""
    try:
        res1 = requests.get(f"{BASE_URL}/kvk/matches?kingdom_a={kingdom_id}&limit=1")
        if res1.status_code == 200 and res1.json().get("data"):
            return str(res1.json()["data"][0])
            
        res2 = requests.get(f"{BASE_URL}/kvk/matches?kingdom_b={kingdom_id}&limit=1")
        if res2.status_code == 200 and res2.json().get("data"):
            return str(res2.json()["data"][0])
            
        return "No recent KvK match data found for that kingdom."
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
            self.knowledge_base = "No specific Kingshot data provided yet."

    async def setup_hook(self):
        self.check_game_events.start()

    async def on_ready(self):
        print(f"👑 Kingshot AI is online as {self.user}!")
        await self.tree.sync()

    # --- THE NEW AI CHAT ENGINE (WITH TOOLS) ---
    async def on_message(self, message):
        if message.author.bot:
            return

        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.user in message.mentions

        if is_dm or is_mentioned:
            user_text = message.content.replace(f'<@{self.user.id}>', '').strip()

            system_prompt = f"""
            You are Zeus, the official AI assistant for Commander Kratos and the KNG Spartan Rage alliance in Kingdom 1649 of the game Kingshot.
            Your tone is helpful, strategic, welcoming, and strictly loyal to the alliance. 
            You have access to live KingShot API tools. Use them if the user asks for active gift codes, player data, or KvK war history.
            Answer questions using ONLY your tools or the knowledge base provided below. 
            If you cannot find the answer, advise them to ask Commander Kratos.
            
            KNOWLEDGE BASE:
            {self.knowledge_base}
            """
            
            async with message.channel.typing():
                try:
                    response = ai_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_text,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            tools=[get_gift_codes, get_player_data, get_kvk_history],
                            temperature=0.7
                        )
                    )
                    await message.channel.send(response.text)
                except Exception as e:
                    await message.channel.send("❌ My connection to the knowledge matrix was interrupted. Try again in a moment.")
                    print(f"AI Error: {e}")

    # --- EVENT SCHEDULER & RALLY COMMANDS ---
    @tasks.loop(seconds=60)
    async def check_game_events(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        current_time_str = now.strftime("%H:%M") 

        for event in self.active_schedules[:]:
            if event["time"] == current_time_str:
                channel = self.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title=f"⏳ ALLIANCE EVENT ALERT: {event['name']}!",
                        description=f"The scheduled event **{event['name']}** is starting now! Prepare your marches.",
                        color=discord.Color.brand_green(),
                    )
                    await channel.send(content="@everyone", embed=embed)
                self.active_schedules.remove(event)

    @check_game_events.before_loop
    async def before_check(self):
        await self.wait_until_ready()

client = KingshotAllianceBot()


# =======================================================
# --- LIVE API ASYNC ENGINE ---
# =======================================================
async def fetch_active_codes():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BASE_URL}/gift-codes") as response:
                if response.status == 200:
                    json_data = await response.json()
                    return json_data.get("data", {}).get("giftCodes", [])
                return None
        except Exception as e:
            print(f"API Error: {e}")
            return None

async def fetch_player_data(player_id: str):
    async with aiohttp.ClientSession() as session:
        try:
            params = {"playerId": player_id}
            async with session.get(f"{BASE_URL}/player-info", params=params) as response:
                if response.status == 200:
                    json_data = await response.json()
                    return json_data.get("data", {})
                elif response.status == 429:
                    return "RATE_LIMIT"
                return None
        except Exception as e:
            print(f"API Error: {e}")
            return None

async def fetch_kvk_history(kingdom_id: int):
    async with aiohttp.ClientSession() as session:
        try:
            params = {"kingdom_a": kingdom_id, "limit": 1}
            async with session.get(f"{BASE_URL}/kvk/matches", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = data.get("data", [])
                    if matches:
                        return matches[0]
            
            params = {"kingdom_b": kingdom_id, "limit": 1}
            async with session.get(f"{BASE_URL}/kvk/matches", params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    matches = data.get("data", [])
                    if matches:
                        return matches[0]
            return None
        except Exception as e:
            print(f"API Error: {e}")
            return None


# =======================================================
# --- GLOBAL SLASH COMMAND INTERFACE ---
# =======================================================

@client.tree.command(name="schedule", description="Schedule an automatic alliance announcement ping.")
@app_commands.describe(event_name="Name of event (e.g. Bear Hunt)", time_utc="Time in 24h UTC format (e.g. 10:00)")
async def schedule(interaction: discord.Interaction, event_name: str, time_utc: str):
    if not interaction.permissions or not interaction.permissions.administrator:
        await interaction.response.send_message("❌ Only Alliance Leaders can schedule alerts.", ephemeral=True)
        return

    try:
        datetime.datetime.strptime(time_utc, "%H:%M")
    except ValueError:
        await interaction.response.send_message("❌ Invalid time format! Please use HH:MM 24-hour format.", ephemeral=True)
        return

    new_event = {"name": event_name, "time": time_utc}
    client.active_schedules.append(new_event)
    await interaction.response.send_message(f"✅ **Success!** I will ping `@everyone` for **{event_name}** at exactly **{time_utc} UTC**.")


@client.tree.command(name="rally", description="Issue an urgent coordinate alert to the entire alliance.")
@app_commands.describe(target="Who are we hitting?", coordinates="Coordinates (e.g., X:150 Y:340)")
async def rally(interaction: discord.Interaction, target: str, coordinates: str):
    if not interaction.permissions or not interaction.permissions.administrator:
        await interaction.response.send_message("❌ Only Alliance Leaders can use this command.", ephemeral=True)
        return

    await interaction.response.defer()
    embed = discord.Embed(
        title="⚔️ URGENT ALLIANCE RALLY SIGNAL!",
        description=f"**Target:** {target}\n**Coordinates:** `{coordinates}`\n\nDeploy immediately!",
        color=discord.Color.red(),
    )
    embed.set_footer(text=f"Issued by Commander {interaction.user.display_name}")
    await interaction.followup.send(content="@everyone", embed=embed)


# --- NEW COMPLEMENTARY API UTILITIES ---

@client.tree.command(name="giftcodes", description="Fetch all currently active KingShot gift codes!")
async def giftcodes(interaction: discord.Interaction):
    await interaction.response.defer() 
    codes = await fetch_active_codes()
    if not codes:
        await interaction.followup.send("❌ Failed to retrieve active codes. Try again later.")
        return
        
    embed = discord.Embed(title="⚔️ Active KingShot Gift Codes ⚔️", color=discord.Color.gold())
    for item in codes:
        code_str = item.get("code", "UNKNOWN")
        expires = item.get("expiresAt", "No Expiration Displayed")
        if expires and "T" in expires:
            expires = expires.split("T")[0]
        embed.add_field(name=f"🎁 Code: {code_str}", value=f"Expires: {expires}", inline=False)
        
    embed.set_footer(text="Make sure to redeem these inside your settings panel!")
    await interaction.followup.send(embed=embed)


@client.tree.command(name="verify-player", description="Look up a player's real-time level and verification profile.")
@app_commands.describe(player_id="The unique numerical in-game ID of the player")
async def verify_player(interaction: discord.Interaction, player_id: str):
    await interaction.response.defer()
    player = await fetch_player_data(player_id)
    
    if player == "RATE_LIMIT":
        await interaction.followup.send("⚠️ API rate limit reached (Max 6 checks/min). Wait a moment and try again.")
        return
    elif not player:
        await interaction.followup.send(f"❌ Could not find a KingShot player with ID: `{player_id}`.")
        return
        
    name = player.get("name", "Unknown")
    kingdom = player.get("kingdom", "Unknown")
    level = player.get("levelRenderedDetailed", f"Level {player.get('level', '??')}")
    avatar_url = player.get("profilePhoto")
    
    embed = discord.Embed(title=f"👤 Player Intel: {name}", color=discord.Color.blue())
    embed.add_field(name="Account ID", value=player_id, inline=True)
    embed.add_field(name="Home Kingdom", value=f"Server {kingdom}", inline=True)
    embed.add_field(name="Current Strength", value=level, inline=True)
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text="Data compiled live via KingShot API Core.")
    await interaction.followup.send(embed=embed)


@client.tree.command(name="kvk-report", description="Pull the latest Kingdom vs Kingdom battle records.")
@app_commands.describe(kingdom="The server number to check (Defaults to our home, 1649)")
async def kvk_report(interaction: discord.Interaction, kingdom: int = 1649):
    await interaction.response.defer()
    match = await fetch_kvk_history(kingdom)
    
    if not match:
        await interaction.followup.send(f"❌ No recent KvK match data found for Server {kingdom}.")
        return
        
    attacker = match.get("attacker", "Unknown")
    defender = match.get("defender", "Unknown")
    castle_winner = match.get("castle_winner", "Unknown")
    castle_captured = match.get("castle_captured", False)
    season_title = match.get("kvk_title", "Recent KvK")
    
    won_castle = (castle_winner == kingdom)
    status_emoji = "🏆" if won_castle else "💀"
    
    embed = discord.Embed(
        title=f"⚔️ KvK War Report: Server {kingdom} ⚔️",
        description=f"**Season:** {season_title}",
        color=discord.Color.green() if won_castle else discord.Color.red()
    )
    embed.add_field(name="Attacker", value=f"Server {attacker}", inline=True)
    embed.add_field(name="Defender", value=f"Server {defender}", inline=True)
    embed.add_field(name="Castle Status", value="Breached/Captured" if castle_captured else "Successfully Defended", inline=False)
    embed.add_field(name="Outcome", value=f"{status_emoji} Server {castle_winner} secured the Castle!", inline=False)
    embed.set_footer(text="Data compiled live via KingShot API Core.")
    await interaction.followup.send(embed=embed)


# =======================================================
# --- IGNITION SEQUENCE ---
# =======================================================
Thread(target=run_server).start()
client.run(TOKEN)
