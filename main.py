import datetime
import os
from threading import Thread
import discord
from discord import app_commands
from discord.ext import tasks
from flask import Flask
import google.generativeai as genai

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("DISCORD_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ANNOUNCEMENT_CHANNEL_ID = 1500543041625129122
# =======================================================

app = Flask("")

@app.route("/")
def home():
    return "Kingshot AI Bot is awake!"

def run_server():
    app.run(host="0.0.0.0", port=8080)

# Configure the AI Brain
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

class KingshotAllianceBot(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.active_schedules = []
        
        # Load the Spartan Knowledge Base when the bot starts
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

    # --- THE NEW AI CHAT ENGINE ---
    async def on_message(self, message):
        if message.author.bot:
            return

        # Trigger AI if the bot is DMed OR tagged (@Zeus) in the server
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = self.user in message.mentions

        if is_dm or is_mentioned:
            # Clean the tag out of the message if mentioned in a server
            user_text = message.content.replace(f'<@{self.user.id}>', '').strip()

            # The Master System Prompt that gives Zeus his identity
            ai_prompt = f"""
            You are Zeus, the official AI assistant for Commander Kratos and the KNG Spartan Rage alliance in Kingdom 1649 of the game Kingshot.
            Your tone is helpful, strategic, welcoming, and strictly loyal to the alliance. 
            Answer the user's question using ONLY the knowledge base provided below. If the answer is not in the knowledge base, advise them to ask Commander Kratos.
            
            KNOWLEDGE BASE:
            {self.knowledge_base}
            
            User's Message: {user_text}
            """
            
            # Show the "Zeus is typing..." indicator in Discord
            async with message.channel.typing():
                try:
                    response = model.generate_content(ai_prompt)
                    await message.channel.send(response.text)
                except Exception as e:
                    await message.channel.send("❌ My connection to the knowledge matrix was interrupted. Try again in a moment.")
                    print(f"AI Error: {e}")

    # --- FEATURE 2: BACKGROUND CLOCK FOR SCHEDULED EVENTS ---
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

# --- FEATURE 3: NEW DYNAMIC SCHEDULE COMMAND ---
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


# --- FEATURE 4: EMERGENCY RALLY ---
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

Thread(target=run_server).start()
client.run(TOKEN)
