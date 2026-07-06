import os
import discord
from discord import app_commands
from discord.ext import tasks
import datetime
from flask import Flask
from threading import Thread

# ==================== CONFIGURATION ====================
TOKEN = os.environ.get("DISCORD_TOKEN")
ANNOUNCEMENT_CHANNEL_ID = 1500543041625129122
# =======================================================

app = Flask('')
@app.route('/')
def home(): return "Kingshot Bot is awake!"
def run_server(): app.run(host='0.0.0.0', port=8080)

class KingshotAllianceBot(discord.Client):
    def __init__(self):
        # Enables intents so the bot can read DM messages smoothly
        intents = discord.Intents.default()
        intents.message_content = True 
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        
        # This list holds your dynamically scheduled alliance events
        self.active_schedules = [] 

    async def setup_hook(self):
        self.check_game_events.start()

    async def on_ready(self):
        print(f"👑 Kingshot Alliance Bot is online as {self.user}!")
        await self.tree.sync()

    # --- FEATURE 1: PRIVATE DM CHAT LOOKOUT ---
    async def on_message(self, message):
        # Ignore messages sent by the bot itself
        if message.author.bot:
            return

        # Check if the message is a private Direct Message (DM)
        if message.guild is None:
            user_text = message.content.lower()
            
            # Simple intelligent response routing
            if "hello" in user_text or "hi" in user_text:
                await message.author.send(f"Greetings, Commander {message.author.display_name}! ⚔️ How can I assist the alliance today?")
            elif "status" in user_text:
                await message.author.send(f"All systems operational. I currently have {len(self.active_schedules)} upcoming events scheduled.")
            else:
                await message.author.send("I am monitoring the realm. Use `/schedule` in the server to set an alliance reminder, or ask me for `status`!")

    # --- FEATURE 2: BACKGROUND CLOCK FOR SCHEDULED EVENTS ---
    @tasks.loop(seconds=60)
    async def check_game_events(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        current_time_str = now.strftime("%H:%M") # Format: "10:00"

        # Check our dynamic schedules list
        for event in self.active_schedules[:]:
            if event["time"] == current_time_str:
                channel = self.get_channel(ANNOUNCEMENT_CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title=f"⏳ ALLIANCE EVENT ALERT: {event['name']}!",
                        description=f"The scheduled event **{event['name']}** is starting now! Prepare your marches.",
                        color=discord.Color.brand_green()
                    )
                    await channel.send(content="@everyone", embed=embed)
                
                # Remove from list so it doesn't repeat automatically unless scheduled again
                self.active_schedules.remove(event)

    @check_game_events.before_loop
    async def before_check(self):
        await self.wait_until_ready()

client = KingshotAllianceBot()

# --- FEATURE 3: NEW DYNAMIC SCHEDULE COMMAND ---
@client.tree.command(name="schedule", description="Schedule an automatic alliance announcement ping.")
@app_commands.describe(event_name="Name of event (e.g. Bear Hunt)", time_utc="Time in 24h UTC format (e.g. 10:00)")
async def schedule(interaction: discord.Interaction, event_name: str, time_utc: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only Alliance Leaders can schedule alerts.", ephemeral=True)
        return

    # Basic time format verification
    try:
        datetime.datetime.strptime(time_utc, "%H:%M")
    except ValueError:
        await interaction.response.send_message("❌ Invalid time format! Please use HH:MM 24-hour format (e.g., `09:30` or `14:00`).", ephemeral=True)
        return

    # Add to our active tracking list
    new_event = {"name": event_name, "time": time_utc}
    client.active_schedules.append(new_event)

    await interaction.response.send_message(f"✅ **Success!** I will automatically ping `@everyone` for **{event_name}** at exactly **{time_utc} UTC** in the announcements channel.")

# --- FEATURE 4: EMERGENCY RALLY ---
@client.tree.command(name="rally", description="Issue an urgent coordinate alert to the entire alliance.")
@app_commands.describe(target="Who are we hitting?", coordinates="Coordinates (e.g., X:150 Y:340)")
async def rally(interaction: discord.Interaction, target: str, coordinates: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only Leaders can use this.", ephemeral=True)
        return

    await interaction.response.defer()
    embed = discord.Embed(
        title="⚔️ URGENT ALLIANCE RALLY SIGNAL!",
        description=f"**Target:** {target}\n**Coordinates:** `{coordinates}`\n\nDeploy immediately!",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Issued by Commander {interaction.user.display_name}")
    await interaction.followup.send(content="@everyone", embed=embed)

Thread(target=run_server).start()
client.run(TOKEN)

