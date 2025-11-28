# -------------------------------------
#
# BEDROCK RANKED DISCORD BOT, BY MA_EHY
#
# -------------------------------------


import asyncio
import time
import discord
from discord.ext import commands, tasks
import os
import random
import json
from dotenv import load_dotenv
from typing import Optional
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  
from io import BytesIO

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True  
intents.guilds = True

class CustomBot(commands.Bot):
    async def process_commands(self, message):
        if message.author == bot.user:
            return
        ctx = await self.get_context(message)
        if ctx.command is not None:
            await self.invoke(ctx)

bot = CustomBot(command_prefix="!", intents=intents, help_command=None)

reported_seeds_file = "reported.txt"

CUSTOM_EMOJIS = {
    'stronghold': '<:sh:1438457932889985044>',
    'bastion': '<:bastion:1438457977374900415>',
    'ruined_portal': '<:rp:1438532121940721717>',
    'warped': '<:warped:1438457958739742740>',
    '116': '<:116:1438532226336948316>',
    '118': '<:118:1438532174910586901>',
    'village': '<:vil:1441824598000668833>' 
}

# === ELO Role Configuration ===
ELO_ROLES = {
    (0, 500): 1436465095575208036,
    (500, 600): 1436465243311181905,
    (600, 700): 1436465394352390274,
    (700, 800): 1436465535456907356,
    (800, 900): 1436465608123482222,
    (900, 1000): 1436465683830669435,
    (1000, 1100): 1436465768954073118,
    (1100, 1200): 1436465966740668426,
    (1200, 1300): 1436466020406792294,
    (1300, 1400): 1436466059732586596,
    (1400, 1500): 1436466192515600484,
    (1500, 1600): 1436466403006742539,
    (1600, 1700): 1436466463161712650,
    (1700, 1800): 1436466834055364649,  # Now gets 2000-2100 role
    (1800, 1900): 1436466981627887738,  # Now gets 2100-2200 role
    (1900, 2000): 1436467025873731647,  # Now gets 2200-2300 role
    (2000, float('inf')): 1436467091409469603  # Now gets 2300+ role
}

# Role assignment message config
ROLE_MESSAGES = {
    1436650237920940175: 1436650117498146907,  # Original message -> role
    1437429031963463770: 1437429561423036466,  # New message 1 -> role 1
    1437429049910759496: 1437429706768121946   # New message 2 -> role 2
}
ROLE_EMOJI = "✅"

# Queue system
queue_116 = []  # Users in 1.16 queue
queue_118 = []  # Users in 1.18+ queue
queue_status_message_id = None 
leaderboard_message_id = None

# Match channels (in order of priority)
MATCH_CHANNELS = [
    1413925002280964100,  # match-1 - will create threads here
    1413928199859212318,  # match-2
    1413928249867899050,  # match-3
    1436774295274520647   # match-4
]

# DM/Queue channel
QUEUE_CHANNEL_ID = 1437179405326749770  # Set to your dedicated queue channel ID, or leave None for DMs

# Queue reminder tracking
queue_join_times = {}  # {user_id: timestamp}

# Active threads tracking
active_match_threads = {}  # {thread_id: [player1_id, player2_id]}

# === Seed Loading Functions ===
def load_seeds_from_file(filename):
    """Load seeds from a text file (one seed per line)"""
    try:
        filepath = os.path.join("seeds", filename)
        if not os.path.exists(filepath):
            print(f"⚠️ Warning: Seed file '{filepath}' not found!")
            return []
        
        with open(filepath, "r") as f:
            seeds = [line.strip() for line in f if line.strip()]
        print(f"✅ Loaded {len(seeds)} seeds from {filename}")
        return seeds
    except Exception as e:
        print(f"❌ Error loading {filename}: {e}")
        return []

def save_reported_seed(seed, mode):
    """Save a reported seed to reported.txt"""
    try:
        with open(reported_seeds_file, "a") as f:
            f.write(f"{seed} ({mode})\n")
        print(f"✅ Saved reported seed: {seed} ({mode})")
    except Exception as e:
        print(f"❌ Error saving reported seed: {e}")

# === Load all seed arrays from files ===
print("📂 Loading seed files...")
codici_116 = load_seeds_from_file("stronghold_116.txt")
rpcodici_116 = load_seeds_from_file("ruined_portal_116.txt")
village_116 = load_seeds_from_file("village.txt")
bastion_118 = load_seeds_from_file("bastion_118.txt")
warped_118 = load_seeds_from_file("warped_forest_118.txt")

# === ELO Role Management Functions ===
def get_role_for_elo(elo):
    """Get the appropriate role ID for a given ELO"""
    for (min_elo, max_elo), role_id in ELO_ROLES.items():
        if min_elo <= elo < max_elo:
            return role_id
    return None

async def update_user_roles(member, elo):
    """Update user's ELO-based roles"""
    try:
        target_role_id = get_role_for_elo(elo)
        if not target_role_id:
            return
        
        target_role = member.guild.get_role(target_role_id)
        if not target_role:
            print(f"⚠️ Could not find role {target_role_id}")
            return
        
        # Remove all other ELO roles
        all_elo_role_ids = set(ELO_ROLES.values())
        roles_to_remove = [r for r in member.roles if r.id in all_elo_role_ids and r.id != target_role_id]
        
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)
        
        # Add the correct role if they don't have it
        if target_role not in member.roles:
            await member.add_roles(target_role)
            print(f"✅ Updated {member.name}'s role to {target_role.name} (ELO: {elo})")
    except Exception as e:
        print(f"❌ Error updating roles for {member.name}: {e}")

@bot.event
async def on_ready():
    global queue_status_message_id
    print(f"Bot online: {bot.user}")
    print("Bot is ready to receive commands!")
    print(f"📊 Seed counts: Stronghold(1.16)={len(codici_116)}, Portal(1.16)={len(rpcodici_116)}, Village(1.16)={len(village_116)}, Bastion(1.18+)={len(bastion_118)}, Warped(1.18+)={len(warped_118)}")
    
    # Set up reaction roles on startup
    try:
        for guild in bot.guilds:
            for channel in guild.text_channels:
                for message_id in ROLE_MESSAGES.keys():
                    try:
                        message = await channel.fetch_message(message_id)
                        await message.add_reaction(ROLE_EMOJI)
                        print(f"✅ Found role message {message_id} in #{channel.name}, added reaction")
                    except discord.NotFound:
                        continue
                    except discord.Forbidden:
                        continue
    except Exception as e:
        print(f"⚠️ Could not set up reaction roles: {e}")
    
    # Initialize queue status message
    if QUEUE_CHANNEL_ID:
        try:
            queue_channel = bot.get_channel(QUEUE_CHANNEL_ID)
            if queue_channel:
                # Try to find existing queue status message
                async for message in queue_channel.history(limit=50):
                    if message.author == bot.user and "📊 QUEUE STATUS" in message.content:
                        queue_status_message_id = message.id
                        print(f"✅ Found existing queue status message")
                        break
                
                # If not found, create new one
                if queue_status_message_id is None:
                    initial_message = await queue_channel.send(
                        "📊 **QUEUE STATUS**\n\n"
                        f"{CUSTOM_EMOJIS['116']} **1.16 Queue:** `0 players`\n"
                        f"{CUSTOM_EMOJIS['118']} **1.18+ Queue:** `0 players`\n\n"
                        "*Use `!queue` to join/leave the queue*"
                    )
                    queue_status_message_id = initial_message.id
                    print(f"✅ Created new queue status message")
                else:
                    # Update existing message
                    await update_queue_status_message()
        except Exception as e:
            print(f"⚠️ Could not set up queue status message: {e}")
    
    # Start leaderboard auto-update
    if not update_leaderboard.is_running():
        update_leaderboard.start()

    # Start queue reminder checker
    if not check_queue_reminders.is_running():
        check_queue_reminders.start()

async def update_queue_status_message():
    """Update the persistent queue status message"""
    global queue_status_message_id
    
    if not QUEUE_CHANNEL_ID or queue_status_message_id is None:
        return
    
    try:
        queue_channel = bot.get_channel(QUEUE_CHANNEL_ID)
        if not queue_channel:
            return
        
        # Build status message (count only, no player names)
        status_text = "📊 **QUEUE STATUS**\n\n"
        status_text += f"{CUSTOM_EMOJIS['116']} **1.16 Queue:** `{len(queue_116)} player{'s' if len(queue_116) != 1 else ''}`\n"
        status_text += f"{CUSTOM_EMOJIS['118']} **1.18+ Queue:** `{len(queue_118)} player{'s' if len(queue_118) != 1 else ''}`\n"
        status_text += f"\n*Use `!queue` to join/leave the queue*\n"
        status_text += f"*Last updated: <t:{int(time.time())}:R>*"
        
        # Update the message
        message = await queue_channel.fetch_message(queue_status_message_id)
        await message.edit(content=status_text)
        
    except discord.NotFound:
        # Message was deleted, create new one
        try:
            queue_channel = bot.get_channel(QUEUE_CHANNEL_ID)
            new_message = await queue_channel.send(
                "📊 **QUEUE STATUS**\n\n"
                f"{CUSTOM_EMOJIS['116']} **1.16 Queue:** `0 players`\n"
                f"{CUSTOM_EMOJIS['118']} **1.18+ Queue:** `0 players`\n\n"
                "*Use `!queue` to join/leave the queue*"
            )
            queue_status_message_id = new_message.id
        except Exception as e:
            print(f"❌ Error recreating queue status message: {e}")
    except Exception as e:
        print(f"❌ Error updating queue status message: {e}")

@tasks.loop(minutes=5)
async def update_leaderboard():
    """Update leaderboard in specific channel every 5 minutes"""
    global leaderboard_message_id
    LEADERBOARD_CHANNEL_ID = 1436792328441430166
    
    try:
        channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
        if not channel:
            print(f"⚠️ Could not find leaderboard channel {LEADERBOARD_CHANNEL_ID}")
            return
        
        if not elo_data:
            return
        
        sorted_players = sorted(elo_data.items(), key=lambda x: x[1], reverse=True)
        
        # Create embed
        embed = discord.Embed(
            title="🏆 RANKED LEADERBOARD 🏆",
            description="Top Players by ELO Rating",
            color=0xFFD700,  # Gold color
            timestamp=discord.utils.utcnow()
        )
        
        # Medal emojis for top 3
        medal_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
        
        # Split into chunks for better readability (3 fields of ~17 players each)
        chunk_size = 17
        
        for chunk_idx in range(3):
            start_idx = chunk_idx * chunk_size
            end_idx = min(start_idx + chunk_size, len(sorted_players[:50]))
            
            if start_idx >= len(sorted_players[:50]):
                break
            
            field_text = ""
            
            for i in range(start_idx, end_idx):
                rank = i + 1
                user_id, user_elo = sorted_players[i]
                
                try:
                    user = await bot.fetch_user(int(user_id))
                    username = user.name[:15]  # Truncate long names
                except (discord.NotFound, discord.HTTPException, ValueError):
                    username = f"User {user_id[:8]}"
                
                # Get win/loss stats
                user_stats = stats_data.get(user_id)
                if user_stats and user_stats["total_games"] > 0:
                    wins = user_stats["wins"]
                    losses = user_stats["losses"]
                    total = wins + losses
                    if total > 0:
                        win_pct = (wins / total) * 100
                        wl_text = f"{win_pct:.0f}%"
                    else:
                        wl_text = "N/A"
                else:
                    wl_text = "N/A"
                
                # Add medal emoji for top 3
                rank_display = medal_emojis.get(rank, f"`{rank:2}`")
                
                # Format line
                field_text += f"{rank_display} **{username}** • `{user_elo}` ELO • {wl_text} Win Rate\n"
            
            # Add field (inline for side-by-side display)
            field_name = f"Rank {start_idx + 1}-{end_idx}" if chunk_idx > 0 else "Top Rankings"
            embed.add_field(
                name=field_name,
                value=field_text if field_text else "No players",
                inline=False
            )
        
        # Add footer with total players
        total_ranked = len(elo_data)
        embed.set_footer(
            text=f"Total Ranked Players: {total_ranked} • Updates every 5 minutes"
        )
        
        # Try to edit existing message, otherwise send new one
        if leaderboard_message_id:
            try:
                message = await channel.fetch_message(leaderboard_message_id)
                await message.edit(embed=embed)
                print(f"✅ Leaderboard edited in #{channel.name}")
            except discord.NotFound:
                # Message was deleted, send new one
                message = await channel.send(embed=embed)
                leaderboard_message_id = message.id
                print(f"✅ New leaderboard sent in #{channel.name}")
        else:
            # First time, send new message
            message = await channel.send(embed=embed)
            leaderboard_message_id = message.id
            print(f"✅ Leaderboard posted in #{channel.name}")
        
    except Exception as e:
        print(f"❌ Error updating leaderboard: {e}")

@tasks.loop(minutes=1)
async def check_queue_reminders():
    """Check if any users have been in queue for 1 hour and send reminder"""
    current_time = time.time()
    users_to_remind = []
    
    # Check all users in queue_join_times
    for user_id, join_time in list(queue_join_times.items()):
        # Check if user is still in any queue
        if user_id not in queue_116 and user_id not in queue_118:
            # User left queue, remove from tracking
            del queue_join_times[user_id]
            continue
        
        # Check if 1 hour has passed (3600 seconds)
        if current_time - join_time >= 3600:
            users_to_remind.append(user_id)
            # Remove from tracking so we don't spam reminders
            del queue_join_times[user_id]
    
    # Send reminders
    for user_id in users_to_remind:
        try:
            user = await bot.fetch_user(user_id)
            in_116 = user_id in queue_116
            in_118 = user_id in queue_118
            
            queues = []
            if in_116:
                queues.append("1.16")
            if in_118:
                queues.append("1.18+")
            
            await user.send(
                f"⏰ **Queue Reminder**\n"
                f"You've been in queue for 1 hour!\n"
                f"Queues: {', '.join(queues)}\n"
                f"**Current queue sizes:** 1.16: `{len(queue_116)}` | 1.18+: `{len(queue_118)}`\n"
                f"Use `!queue` again to leave the queue."
            )
            print(f"✅ Sent queue reminder to {user.name}")
        except Exception as e:
            print(f"❌ Error sending reminder to user {user_id}: {e}")

@check_queue_reminders.before_loop
async def before_queue_reminders():
    """Wait for bot to be ready before starting queue reminder loop"""
    await bot.wait_until_ready()
    print("🔄 Starting queue reminder checker (every 1 minute)")

@update_leaderboard.before_loop
async def before_leaderboard():
    """Wait for bot to be ready before starting leaderboard loop"""
    await bot.wait_until_ready()
    print("🔄 Starting leaderboard auto-update (every 5 minutes)")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    print(f"Received message: '{message.content}' from: {message.author} (Bot: {message.author.bot})")
    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload):
    """Handle reaction role assignment"""
    if payload.message_id not in ROLE_MESSAGES:
        return
    
    if str(payload.emoji) != ROLE_EMOJI:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return
    
    role_id = ROLE_MESSAGES[payload.message_id]
    role = guild.get_role(role_id)
    if not role:
        print(f"⚠️ Could not find role {role_id}")
        return
    
    try:
        await member.add_roles(role)
        print(f"✅ Gave role {role.name} to {member.name}")
    except Exception as e:
        print(f"❌ Error giving role to {member.name}: {e}")

@bot.event
async def on_raw_reaction_remove(payload):
    """Handle reaction role removal"""
    if payload.message_id not in ROLE_MESSAGES:
        return
    
    if str(payload.emoji) != ROLE_EMOJI:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return
    
    role_id = ROLE_MESSAGES[payload.message_id]
    role = guild.get_role(role_id)
    if not role:
        return
    
    try:
        await member.remove_roles(role)
        print(f"✅ Removed role {role.name} from {member.name}")
    except Exception as e:
        print(f"❌ Error removing role from {member.name}: {e}")












@bot.command()
async def steak(ctx):
    await ctx.send("What? I don't know what you are talking about...")

@bot.command()
async def ping(ctx):
    print(f"Ping command called by: {ctx.author}")
    await ctx.send("Pong!")

@bot.command()
async def dragoblu(ctx):
    await ctx.send("Forza Como")
    
@bot.command()
async def stocazzo(ctx):
    await ctx.send("no way what a sketcher!")

@bot.command()
async def hi(ctx):
    await ctx.send("hi")

@bot.command()
async def mobile(ctx, time_str: str):
    """
    Convert time to seconds, subtract 12%, and display result.
    Usage: !mobile 5:00, !mobile 12:11, etc.
    """
    try:
        if ':' not in time_str:
            await ctx.send("❌ Please use format MM:SS (e.g., 5:00, 12:11)")
            return

        parts = time_str.split(':')
        if len(parts) != 2:
            await ctx.send("❌ Please use format MM:SS (e.g., 5:00, 12:11)")
            return

        minutes = int(parts[0])
        seconds = int(parts[1])
        total_seconds = minutes * 60 + seconds
        reduced_seconds = total_seconds * 0.88
        final_minutes = int(reduced_seconds // 60)
        final_secs = int(reduced_seconds % 60)

        await ctx.send(f"The time is: {final_minutes}:{final_secs:02d}")

    except ValueError:
        await ctx.send("❌ Invalid time format. Please use MM:SS (e.g., 5:00, 12:11)")
    except Exception:
        await ctx.send("❌ Error processing time. Please use format MM:SS")

# === ELO Loading ===
if os.path.exists("elo.json"):
    with open("elo.json", "r") as f:
        elo_data = json.load(f)
else:
    elo_data = {}

# === ELO History Loading ===
if os.path.exists("elo_history.json"):
    with open("elo_history.json", "r") as f:
        elo_history = json.load(f)
else:
    elo_history = {}

def save_elo_history():
    """Save ELO history to file"""
    with open("elo_history.json", "w") as f:
        json.dump(elo_history, f, indent=2)

def record_elo_change(user_id, new_elo):
    """Record ELO change in history"""
    user_id_str = str(user_id)
    if user_id_str not in elo_history:
        elo_history[user_id_str] = []
    
    elo_history[user_id_str].append({
        "elo": new_elo,
        "timestamp": int(time.time())
    })

    if len(elo_history[user_id_str]) > 10000:
        elo_history[user_id_str] = elo_history[user_id_str][-100:]
    
    save_elo_history()

# === Stats Loading ===
if os.path.exists("stats.json"):
    with open("stats.json", "r") as f:
        stats_data = json.load(f)
else:
    stats_data = {}

def save_stats():
    """Save stats data to file"""
    with open("stats.json", "w") as f:
        json.dump(stats_data, f, indent=2)

def init_player_stats(user_id):
    """Initialize stats for a new player"""
    if str(user_id) not in stats_data:
        stats_data[str(user_id)] = {
            "total_games": 0,
            "games_since_reset": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "forfeits": 0,
            "peak_elo": 1000,
            "completion_times": [],  # NEW: Store all completion times
            "head_to_head": {},  # NEW: Track wins/losses against specific opponents
            "by_mode": {
                "stronghold_116": {"wins": 0, "losses": 0, "draws": 0, "times": []},
                "ruined_portal_116": {"wins": 0, "losses": 0, "draws": 0, "times": []},
                "village_116": {"wins": 0, "losses": 0, "draws": 0, "times": []},
                "bastion_118": {"wins": 0, "losses": 0, "draws": 0, "times": []},
                "warped_forest_118": {"wins": 0, "losses": 0, "draws": 0, "times": []}
            }
        }
    # Ensure peak_elo exists for existing players
    elif "peak_elo" not in stats_data[str(user_id)]:
        current_elo = elo_data.get(str(user_id), 1000)
        stats_data[str(user_id)]["peak_elo"] = current_elo
    # Ensure games_since_reset exists for existing players
    elif "games_since_reset" not in stats_data[str(user_id)]:
        stats_data[str(user_id)]["games_since_reset"] = 0
    # Ensure completion_times exists for existing players
    if "completion_times" not in stats_data[str(user_id)]:
        stats_data[str(user_id)]["completion_times"] = []
    # Ensure head_to_head exists for existing players
    if "head_to_head" not in stats_data[str(user_id)]:
        stats_data[str(user_id)]["head_to_head"] = {}
    # Ensure times exists in by_mode for existing players
    for mode in stats_data[str(user_id)]["by_mode"]:
        if "times" not in stats_data[str(user_id)]["by_mode"][mode]:
            stats_data[str(user_id)]["by_mode"][mode]["times"] = []

    # Ensure village_116 exists for existing players (backward compatibility)
    if "village_116" not in stats_data[str(user_id)]["by_mode"]:
        stats_data[str(user_id)]["by_mode"]["village_116"] = {"wins": 0, "losses": 0, "draws": 0, "times": []}
        save_stats()

def record_game_result(winner_id, loser_id, mode, is_draw=False, is_forfeit=False, winner_time=None):
    """Record game statistics"""
    init_player_stats(winner_id)
    init_player_stats(loser_id)
    
    winner_id_str = str(winner_id)
    loser_id_str = str(loser_id)
    
    # Update total games
    stats_data[winner_id_str]["total_games"] += 1
    stats_data[loser_id_str]["total_games"] += 1
    
    # Update games since reset
    stats_data[winner_id_str]["games_since_reset"] += 1
    stats_data[loser_id_str]["games_since_reset"] += 1
    
    # Store completion time for winner if provided
    if winner_time and not is_draw and not is_forfeit:
        stats_data[winner_id_str]["completion_times"].append(winner_time)
        if mode in stats_data[winner_id_str]["by_mode"]:
            stats_data[winner_id_str]["by_mode"][mode]["times"].append(winner_time)
    
    if is_draw:
        stats_data[winner_id_str]["draws"] += 1
        stats_data[loser_id_str]["draws"] += 1
        if mode in stats_data[winner_id_str]["by_mode"]:
            stats_data[winner_id_str]["by_mode"][mode]["draws"] += 1
            stats_data[loser_id_str]["by_mode"][mode]["draws"] += 1
    else:
        stats_data[winner_id_str]["wins"] += 1
        stats_data[loser_id_str]["losses"] += 1
        
        # Update head-to-head records
        if loser_id_str not in stats_data[winner_id_str]["head_to_head"]:
            stats_data[winner_id_str]["head_to_head"][loser_id_str] = {"wins": 0, "losses": 0}
        if winner_id_str not in stats_data[loser_id_str]["head_to_head"]:
            stats_data[loser_id_str]["head_to_head"][winner_id_str] = {"wins": 0, "losses": 0}
        
        stats_data[winner_id_str]["head_to_head"][loser_id_str]["wins"] += 1
        stats_data[loser_id_str]["head_to_head"][winner_id_str]["losses"] += 1
        
        if is_forfeit:
            stats_data[loser_id_str]["forfeits"] += 1
        
        if mode in stats_data[winner_id_str]["by_mode"]:
            stats_data[winner_id_str]["by_mode"][mode]["wins"] += 1
            stats_data[loser_id_str]["by_mode"][mode]["losses"] += 1
    
    save_stats()

# === Active Challenges Tracking ===
active_challenges = {}

# === Solo Command ===
solo_cooldowns = {}

@bot.command()
async def solo(ctx):
    """Solo practice - choose version and mode, no ELO change"""
    user_id = ctx.author.id
    now = time.time()

    if user_id in solo_cooldowns:
        elapsed = now - solo_cooldowns[user_id]
        if elapsed < 10:
            remaining = int(10 - elapsed)
            await ctx.send(f"⏳ You need to wait `{remaining}` more seconds before using `!solo` again.")
            return

    version_msg = await ctx.send(
        f"{ctx.author.mention}, choose your Minecraft version:\n"
        f"**Select version:**\n"
        f"{CUSTOM_EMOJIS['116']} - 1.16\n"
        f"{CUSTOM_EMOJIS['118']} - 1.18+\n\n"
        f"**React to continue!**"
    )

    await version_msg.add_reaction(CUSTOM_EMOJIS['116'])
    await version_msg.add_reaction(CUSTOM_EMOJIS['118'])

    def version_check(reaction, user):
        return (user.id == ctx.author.id and 
                str(reaction.emoji) in [CUSTOM_EMOJIS['116'], CUSTOM_EMOJIS['118']] and 
                reaction.message.id == version_msg.id)

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=version_check)
        chosen_version = str(reaction.emoji)

        if chosen_version == CUSTOM_EMOJIS['116']:
            mode_msg = await ctx.send(
                f"**Choose 1.16 game mode:**\n"
                f"{CUSTOM_EMOJIS['stronghold']} - Stronghold\n"
                f"{CUSTOM_EMOJIS['ruined_portal']} - Ruined Portal\n"
                f"{CUSTOM_EMOJIS['village']} - Village\n"
                f"🎲 - Random\n\n"
                f"**React to get your seed!**"
            )
            mode_options = {
                str(CUSTOM_EMOJIS['stronghold']): (codici_116, "1.16 Stronghold"),
                str(CUSTOM_EMOJIS['ruined_portal']): (rpcodici_116, "1.16 Ruined Portal"),
                str(CUSTOM_EMOJIS['village']): (village_116, "1.16 Village"),
                "🎲": "random_116"
            }
            mode_emojis = [CUSTOM_EMOJIS['stronghold'], CUSTOM_EMOJIS['ruined_portal'], CUSTOM_EMOJIS['village'], "🎲"] 
        else:
            mode_msg = await ctx.send(
                f"**Choose 1.18+ game mode:**\n"
                f"{CUSTOM_EMOJIS['bastion']} - Bastion\n"
                f"{CUSTOM_EMOJIS['warped']} - Warped Forest\n"
                f"🎲 - Random\n\n"
                f"**React to get your seed!**"
            )
            mode_options = {
                str(CUSTOM_EMOJIS['bastion']): (bastion_118, "1.18+ Bastion"),
                str(CUSTOM_EMOJIS['warped']): (warped_118, "1.18+ Warped Forest"),
                "🎲": "random_118"
            }
            mode_emojis = [CUSTOM_EMOJIS['bastion'], CUSTOM_EMOJIS['warped'], "🎲"]

        for emoji in mode_emojis:
            await mode_msg.add_reaction(emoji)

        def mode_check(reaction, user):
            return (user.id == ctx.author.id and 
                    str(reaction.emoji) in [str(e) for e in mode_emojis] and 
                    reaction.message.id == mode_msg.id)

        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=mode_check)
        
        choice = mode_options[str(reaction.emoji)]
        
        # Handle random selection
        if choice == "random_116":
            # Randomly choose between Stronghold and Ruined Portal
            random_choice = random.choice([
                (codici_116, "1.16 Stronghold"),
                (rpcodici_116, "1.16 Ruined Portal"),
                (village_116, "1.16 Village")
            ])
            seed_array, mode_name = random_choice
        elif choice == "random_118":
            # Randomly choose between Bastion and Warped Forest
            random_choice = random.choice([
                (bastion_118, "1.18+ Bastion"),
                (warped_118, "1.18+ Warped Forest")
            ])
            seed_array, mode_name = random_choice
        else:
            seed_array, mode_name = choice
        
        if not seed_array:
            await ctx.send(f"❌ No {mode_name.lower()} seeds available!")
            return
            
        seed = random.choice(seed_array)
        await ctx.send(f"🎮 Your **{mode_name}** solo seed is: `{seed}`")
        solo_cooldowns[user_id] = now

    except asyncio.TimeoutError:
        await ctx.send(f"{ctx.author.mention}, time's up! Use `!solo` again to get a seed.")
        return


# === Private Command (Multi-player support) ===
@bot.command()
async def private(ctx, *members: discord.Member):
    """Private match - choose version and mode, no ELO change. Supports 2+ players."""
    if len(members) == 0:
        await ctx.send("Please mention at least one other user! Usage: `!private @user1 @user2 ...`")
        return
    
    # Remove duplicates and ensure initiator isn't in the list
    members = list(set(members))
    if ctx.author in members:
        members.remove(ctx.author)
    
    if len(members) == 0:
        await ctx.send("You cannot play against yourself!")
        return

    challenger = ctx.author
    all_players = [challenger] + list(members)
    all_player_ids = [p.id for p in all_players]
    
    # Check if any player is already in a match
    for player in all_players:
        if player.id in active_challenges:
            await ctx.send(f"{player.mention} is already in a match.")
            return

    # Format player list for display
    player_mentions = " ".join([p.mention for p in all_players])
    
    version_msg = await ctx.send(
        f"**{len(all_players)}-Player Private Match**\n"
        f"Players: {player_mentions}\n\n"
        f"**Choose Minecraft version:**\n"
        f"{CUSTOM_EMOJIS['116']} - 1.16\n"
        f"{CUSTOM_EMOJIS['118']} - 1.18+\n\n"
        f"**All players must react with the same choice!**"
    )

    await version_msg.add_reaction(CUSTOM_EMOJIS['116'])
    await version_msg.add_reaction(CUSTOM_EMOJIS['118'])
    reactions_tracker = {p.id: {'version': None, 'mode': None} for p in all_players}
    
    def version_check(reaction, user):
        return (user.id in all_player_ids and 
                str(reaction.emoji) in [CUSTOM_EMOJIS['116'], CUSTOM_EMOJIS['118']] and 
                reaction.message.id == version_msg.id)

    try:
        # Wait for all players to choose version
        while any(reactions_tracker[p_id]['version'] is None for p_id in all_player_ids):
            reaction, user = await bot.wait_for("reaction_add", timeout=180.0, check=version_check)
            reactions_tracker[user.id]['version'] = str(reaction.emoji)
            
            # Build status display
            status_lines = []
            for player in all_players:
                status = "✅" if reactions_tracker[player.id]['version'] else "❌"
                status_lines.append(f"{player.mention}: {status}")
            
            await version_msg.edit(content=
                f"**{len(all_players)}-Player Private Match**\n"
                f"Players: {player_mentions}\n\n"
                f"**Choose Minecraft version:**\n"
                f"{CUSTOM_EMOJIS['116']} - 1.16\n"
                f"{CUSTOM_EMOJIS['118']} - 1.18+\n\n"
                f"**All players must react with the same choice!**\n"
                + " | ".join(status_lines)
            )

        # Check if all players chose the same version
        chosen_versions = [reactions_tracker[p_id]['version'] for p_id in all_player_ids]
        if len(set(chosen_versions)) > 1:
            await ctx.send("**Private match failed!** All players must choose the same version.")
            return

        chosen_version = chosen_versions[0]

        # Mode selection
        if chosen_version == CUSTOM_EMOJIS['116']:
            mode_msg = await ctx.send(
                f"**Choose 1.16 game mode:**\n"
                f"{CUSTOM_EMOJIS['stronghold']} - Stronghold\n"
                f"{CUSTOM_EMOJIS['ruined_portal']} - Ruined Portal\n\n"
                f"{CUSTOM_EMOJIS['village']} - Village\n"
                f"**All players must react with the same choice!**"
            )
            mode_emojis = [CUSTOM_EMOJIS['stronghold'], CUSTOM_EMOJIS['ruined_portal'], CUSTOM_EMOJIS['village']] 
        else:
            mode_msg = await ctx.send(
                f"**Choose 1.18+ game mode:**\n"
                f"{CUSTOM_EMOJIS['bastion']} - Bastion\n"
                f"{CUSTOM_EMOJIS['warped']} - Warped Forest\n\n"
                f"**All players must react with the same choice!**"
            )
            mode_emojis = [CUSTOM_EMOJIS['bastion'], CUSTOM_EMOJIS['warped']]

        for emoji in mode_emojis:
            await mode_msg.add_reaction(emoji)

        def mode_check(reaction, user):
            return (user.id in all_player_ids and 
                    str(reaction.emoji) in [str(e) for e in mode_emojis] and 
                    reaction.message.id == mode_msg.id)

        # Wait for all players to choose mode
        while any(reactions_tracker[p_id]['mode'] is None for p_id in all_player_ids):
            reaction, user = await bot.wait_for("reaction_add", timeout=180.0, check=mode_check)
            reactions_tracker[user.id]['mode'] = str(reaction.emoji)
            
            # Build status display
            status_lines = []
            for player in all_players:
                status = "✅" if reactions_tracker[player.id]['mode'] else "❌"
                status_lines.append(f"{player.mention}: {status}")
            
            if chosen_version == "🔷":
                mode_text = f"**Choose 1.16 game mode:**\n1️⃣ - Stronghold\n2️⃣ - Ruined Portal"
            else:
                mode_text = f"**Choose 1.18+ game mode:**\n1️⃣ - Bastion\n2️⃣ - Warped Forest"
            
            await mode_msg.edit(content=
                f"{mode_text}\n\n"
                f"**All players must react with the same choice!**\n"
                + " | ".join(status_lines)
            )

        # Check if all players chose the same mode
        chosen_modes = [reactions_tracker[p_id]['mode'] for p_id in all_player_ids]
        if len(set(chosen_modes)) > 1:
            await ctx.send("**Private match failed!** All players must choose the same game mode.")
            return

        chosen_mode = chosen_modes[0]
        
        # Determine game mode and seed array
        if chosen_version == "🔷":
            if chosen_mode == str(CUSTOM_EMOJIS['stronghold']):
                game_mode = "stronghold_116"
                seed_array = codici_116
                mode_display = "1.16 Stronghold"
            elif chosen_mode == str(CUSTOM_EMOJIS['village']): 
                game_mode = "village_116"
                seed_array = village_116
                mode_display = "1.16 Village"
            else:  # ruined_portal
                game_mode = "ruined_portal_116"
                seed_array = rpcodici_116
                mode_display = "1.16 Ruined Portal"
        else:
            if chosen_mode == str(CUSTOM_EMOJIS['bastion']):
                game_mode = "bastion_118"
                seed_array = bastion_118
                mode_display = "1.18+ Bastion"
            else:  # warped
                game_mode = "warped_forest_118"
                seed_array = warped_118
                mode_display = "1.18+ Warped Forest"
        
        if not seed_array:
            await ctx.send(f"❌ No {mode_display.lower()} seeds available!")
            return
            
        initial_seed = random.choice(seed_array)
        
        version_tag = "1.16" if chosen_version == "🔷" else "1.18+"
        
        # Create match state for all players
        # For multi-player matches, store all opponent IDs
        other_player_ids = [p.id for p in all_players]
        
        for player in all_players:
            opponents = [p_id for p_id in other_player_ids if p_id != player.id]
            active_challenges[player.id] = {
                'opponent_id': opponents[0] if len(opponents) == 1 else None,  # For backwards compatibility
                'opponent_ids': opponents,  # List of all opponents
                'all_players': other_player_ids,  # All players including self
                'version': version_tag,
                'mode': game_mode, 
                'seed': initial_seed,
                'ranked': False,
                'multi_player': True
            }
        
        emoji_map = {
            "stronghold_116": CUSTOM_EMOJIS['stronghold'],
            "ruined_portal_116": CUSTOM_EMOJIS['ruined_portal'],
            "village_116": CUSTOM_EMOJIS['village'],
            "bastion_118": CUSTOM_EMOJIS['bastion'],
            "warped_forest_118": CUSTOM_EMOJIS['warped']
        }
        
        await ctx.send(
            f"{emoji_map.get(game_mode, '🎮')} **{len(all_players)}-Player {mode_display} Private Match Started!**\n"
            f"Players: {player_mentions}\n"
            f"Seed: `{initial_seed}`\n"
            f"*This is an unranked match - no ELO will be affected*"
        )
            
    except asyncio.TimeoutError:
        await ctx.send("⏰ **Match setup expired!** Players took too long to make their selections.")

def update_elo(winner_id, loser_id):
    # Dynamic K-factor based on games played SINCE RESET and ELO rating
    def get_k_factor(user_id):
        user_elo = elo_data.get(str(user_id), 1000)
        
        # Players with ELO >= 1700 always have K = 40
        if user_elo >= 1700:
            return 40
        
        # For players below 1700, use games-based K-factor
        user_stats = stats_data.get(str(user_id))
        if not user_stats:
            games_played = 0
        else:
            # Use games_since_reset instead of total_games
            games_played = user_stats.get("games_since_reset", 0)
        
        # K = 100 - 1*(games played), minimum 40
        k = max(40, 100 - 1 * games_played)
        return k
    
    DENOMINATOR = 1000
    
    winner_elo = elo_data.get(str(winner_id), 1000)
    loser_elo = elo_data.get(str(loser_id), 1000)

    expected_winner = 1 / (1 + 10**((loser_elo - winner_elo) / DENOMINATOR))
    expected_loser = 1 - expected_winner

    # Get individual K-factors for each player
    winner_k = get_k_factor(winner_id)
    loser_k = get_k_factor(loser_id)

    winner_gain = round(winner_k * (1 - expected_winner))
    loser_loss = round(loser_k * (0 - expected_loser))
    
    # ELO LOSS PROTECTION: Cap losses based on ELO
    if loser_elo < 600:
        # Players under 600 ELO lose maximum 15 points
        loser_loss = max(loser_loss, -15)
    elif loser_elo < 800:
        # Players between 600-800 ELO lose maximum 25 points
        loser_loss = max(loser_loss, -25)
    else:
        # Players 800+ ELO lose maximum 50 points
        loser_loss = max(loser_loss, -50)
    
    new_winner_elo = winner_elo + winner_gain
    new_loser_elo = loser_elo + loser_loss

    elo_data[str(winner_id)] = new_winner_elo
    elo_data[str(loser_id)] = new_loser_elo

    with open("elo.json", "w") as f:
        json.dump(elo_data, f)
    
    # Record ELO history
    record_elo_change(winner_id, new_winner_elo)
    record_elo_change(loser_id, new_loser_elo)

    if new_winner_elo > stats_data[str(winner_id)]["peak_elo"]:
        stats_data[str(winner_id)]["peak_elo"] = new_winner_elo
        save_stats()
    
    if new_loser_elo > stats_data[str(loser_id)]["peak_elo"]:
        stats_data[str(loser_id)]["peak_elo"] = new_loser_elo
        save_stats()

# === Result Command (Multi-player support) ===
@bot.command()
async def result(ctx, arg=None, time_str: str = None):
    mentions = ctx.message.mentions
    user_id = ctx.author.id

    if user_id not in active_challenges:
        await ctx.send("You are not currently in a match. Use `!challenge @user` or `!private @user1 @user2...` first.")
        return

    if arg is None:
        await ctx.send("Use `!result @winner MM:SS` or `!result draw`.\n**Example:** `!result @player 6:45`")
        return
    
    # Parse time if provided
    completion_time = None
    if time_str and ':' in time_str:
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                await ctx.send("❌ Invalid time format. Use MM:SS (e.g., 6:45)")
                return
            minutes = int(parts[0])
            seconds = int(parts[1])
            if seconds >= 60 or seconds < 0 or minutes < 0:
                await ctx.send("❌ Invalid time. Seconds must be 0-59.")
                return
            completion_time = minutes * 60 + seconds  # Store as total seconds
        except (ValueError, IndexError):
            await ctx.send("❌ Invalid time format. Use MM:SS (e.g., 6:45)")
            return

    challenge_state = active_challenges.get(ctx.author.id)
    if not challenge_state:
        await ctx.send("Could not find your active match.")
        return
    
    is_ranked = challenge_state.get('ranked', False)
    is_multi_player = challenge_state.get('multi_player', False)
    game_mode = challenge_state['mode']
    thread_id = challenge_state.get('thread_id')
    
    # Handle multi-player matches
    if is_multi_player:
        all_player_ids = challenge_state.get('all_players', [])
        
        if arg.lower() == "draw":
            # Remove all players from active challenges
            for player_id in all_player_ids:
                active_challenges.pop(player_id, None)
            
            # Clean up thread tracking
            if thread_id:
                active_match_threads.pop(thread_id, None)
            
            await ctx.send(f"🏳️ Draw recorded for {len(all_player_ids)}-player match (unranked).")
            
            # Archive thread if it exists
            if thread_id:
                try:
                    thread = bot.get_channel(thread_id)
                    if thread:
                        await thread.edit(archived=True)
                except:
                    pass
            
            return
        
        if len(mentions) != 1:
            await ctx.send("Mention exactly one winner. **Example:** `!result @player 6:45`")
            return
        
        winner = mentions[0]
        
        if winner.id not in all_player_ids:
            await ctx.send("The winner must be one of the players in this match.")
            return
        
        # Remove all players from active challenges
        for player_id in all_player_ids:
            active_challenges.pop(player_id, None)
        
        # Clean up thread tracking
        if thread_id:
            active_match_threads.pop(thread_id, None)
        
        player_list = " ".join([f"<@{p_id}>" for p_id in all_player_ids])
        time_display = f" in `{time_str}`" if time_str else ""
        await ctx.send(
            f"🏆 **{winner.mention} wins the {len(all_player_ids)}-player match{time_display}!**\n"
            f"Players: {player_list}\n"
            f"*This was an unranked match - no ELO change*"
        )
        
        # Archive thread if it exists
        if thread_id:
            try:
                thread = bot.get_channel(thread_id)
                if thread:
                    await thread.edit(archived=True)
            except:
                pass
        
        return
    
    # Handle 2-player matches (original logic)
    opponent_id = challenge_state['opponent_id']

    if arg.lower() == "draw":
        # Ask both players to confirm draw
        opponent = await bot.fetch_user(opponent_id)
        
        draw_msg = await ctx.send(
            f"**Draw Request**\n"
            f"{ctx.author.mention} has requested a draw.\n"
            f"{opponent.mention}, react with ➡️ to agree to draw."
        )
        
        await draw_msg.add_reaction("➡️")
        
        def draw_check(reaction, user):
            return (user.id == opponent_id and 
                    str(reaction.emoji) == "➡️" and 
                    reaction.message.id == draw_msg.id)
        
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=draw_check)
            
            # Both players agreed to draw
            active_challenges.pop(ctx.author.id, None)
            active_challenges.pop(opponent_id, None)
            
            # Clean up thread tracking
            if thread_id:
                active_match_threads.pop(thread_id, None)
            
            opponent = await bot.fetch_user(opponent_id)
            
            if is_ranked:
                record_game_result(ctx.author.id, opponent_id, game_mode, is_draw=True)
                
                embed = discord.Embed(
                    title="🏳️ DRAW",
                    description="Match ended in a draw",
                    color=0x95a5a6  # Gray
                )
                
                embed.add_field(
                    name="Players",
                    value=f"{ctx.author.mention} vs {opponent.mention}",
                    inline=False
                )
                
                embed.add_field(
                    name="Result",
                    value="*No ELO change*",
                    inline=False
                )
                
                embed.set_footer(text="Match completed")
                embed.timestamp = discord.utils.utcnow()
                
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="🏳️ DRAW",
                    description="Match ended in a draw (unranked)",
                    color=0x95a5a6
                )
                
                embed.add_field(
                    name="Players",
                    value=f"{ctx.author.mention} vs {opponent.mention}",
                    inline=False
                )
                
                embed.set_footer(text="Match completed")
                embed.timestamp = discord.utils.utcnow()
                
                await ctx.send(embed=embed)
            
            # Archive thread if it exists
            if thread_id:
                try:
                    thread = bot.get_channel(thread_id)
                    if thread:
                        await thread.edit(archived=True)
                        print(f"✅ Archived thread {thread.name}")
                except Exception as e:
                    print(f"⚠️ Could not archive thread: {e}")
            
            return
            
        except asyncio.TimeoutError:
            await ctx.send(f"⏰ Draw request expired. {opponent.mention} did not agree in time.")
            return

    if len(mentions) != 1:
        await ctx.send("Mention exactly one winner. **Example:** `!result @player 6:45`")
        return

    winner = mentions[0]
    
    if winner.id == ctx.author.id:
        loser_id = opponent_id
    elif winner.id == opponent_id:
        loser_id = ctx.author.id
    else:
        await ctx.send("The winner must be one of the players in this match.")
        return
    
    # For ranked matches, require time
    if is_ranked and not completion_time:
        await ctx.send("⏱️ **Time required for ranked matches!**\nUse: `!result @winner MM:SS`\n**Example:** `!result @player 6:45`")
        return

    active_challenges.pop(winner.id, None)
    active_challenges.pop(loser_id, None)
    
    # Clean up thread tracking
    if thread_id:
        active_match_threads.pop(thread_id, None)

    if is_ranked:
        # Store OLD ELO values BEFORE updating
        old_winner_elo = elo_data.get(str(winner.id), 1000)
        old_loser_elo = elo_data.get(str(loser_id), 1000)
        
        record_game_result(winner.id, loser_id, game_mode, winner_time=completion_time)
        
        update_elo(winner.id, loser_id)
        
        # Get NEW ELO values AFTER updating
        winner_elo = elo_data.get(str(winner.id), 1000)
        loser_elo = elo_data.get(str(loser_id), 1000)

        if ctx.guild:
            winner_member = ctx.guild.get_member(winner.id)
            loser_member = ctx.guild.get_member(loser_id)
            
            if winner_member:
                await update_user_roles(winner_member, winner_elo)
            if loser_member:
                await update_user_roles(loser_member, loser_elo)

        # Get loser object
        loser = await bot.fetch_user(loser_id)
        
        # Calculate ELO changes
        winner_change = winner_elo - old_winner_elo
        loser_change = loser_elo - old_loser_elo
        
        # Get updated stats
        winner_stats = stats_data.get(str(winner.id))
        loser_stats = stats_data.get(str(loser_id))
        
        w_wins = winner_stats["wins"]
        w_losses = winner_stats["losses"]
        w_total = w_wins + w_losses
        
        l_wins = loser_stats["wins"]
        l_losses = loser_stats["losses"]
        l_total = l_wins + l_losses
        
        # Create result embed
        embed = discord.Embed(
            title="🏆 MATCH RESULT",
            description=f"**{winner.display_name}** wins!",
            color=0x2ecc71  # Green for victory
        )
        
        embed.set_thumbnail(url=winner.display_avatar.url)
        
        # Winner stats
        winner_value = (
            f"**ELO:** `{winner_elo}` *({winner_change:+d})*\n"
            f"**Record:** {w_wins}W - {w_losses}L"
        )
        if completion_time:
            mins = completion_time // 60
            secs = completion_time % 60
            winner_value += f"\n**Time:** `{mins}:{secs:02d}`"
        
        embed.add_field(
            name=f"👑 {winner.display_name}",
            value=winner_value,
            inline=True
        )
        
        # VS separator
        embed.add_field(
            name="\u200b",
            value="\u200b",
            inline=True
        )
        
        # Loser stats
        embed.add_field(
            name=f"{loser.display_name}",
            value=(
                f"**ELO:** `{loser_elo}` *({loser_change:+d})*\n"
                f"**Record:** {l_wins}W - {l_losses}L"
            ),
            inline=True
        )
        
        embed.set_footer(text="Match completed")
        embed.timestamp = discord.utils.utcnow()
        
        await ctx.send(embed=embed)
        
        # 5% chance to request recording from winner
        if random.random() < 0.05:
            if thread_id:
                try:
                    thread = bot.get_channel(thread_id)
                    if thread:
                        await thread.send(
                            f"🎥 **Recording Request**\n"
                            f"{winner.mention}, you've been randomly selected to submit a recording of your run!\n"
                            f"Please upload your recording here for verification purposes.\n"
                            f"*This helps maintain competitive integrity.*"
                        )
                        print(f"✅ Requested recording from {winner.name}")
                except Exception as e:
                    print(f"⚠️ Could not request recording: {e}")
    else:
        loser = await bot.fetch_user(loser_id)
        
        embed = discord.Embed(
            title="🏆 MATCH RESULT",
            description=f"**{winner.display_name}** wins!",
            color=0x95a5a6  # Gray for unranked
        )
        
        embed.set_thumbnail(url=winner.display_avatar.url)
        
        embed.add_field(
            name="Match Type",
            value="*Unranked - No ELO change*",
            inline=False
        )
        
        if completion_time:
            mins = completion_time // 60
            secs = completion_time % 60
            embed.add_field(
                name="Completion Time",
                value=f"`{mins}:{secs:02d}`",
                inline=False
            )
        
        embed.set_footer(text="Match completed")
        embed.timestamp = discord.utils.utcnow()
        
        await ctx.send(embed=embed)
    
    # Archive thread if it exists
    if thread_id:
        try:
            thread = bot.get_channel(thread_id)
            if thread:
                await thread.edit(archived=True)
                print(f"✅ Archived thread {thread.name}")
        except Exception as e:
            print(f"⚠️ Could not archive thread: {e}")

# === ELO Command ===
@bot.command()
async def elo(ctx, member: Optional[discord.Member] = None):
    if member is None:
        member = ctx.author
    user_elo = elo_data.get(str(member.id), 1000)
    
    # Update role when checking ELO
    if ctx.guild:
        await update_user_roles(member, user_elo)
    
    await ctx.send(f"📊 **{member.display_name}** ELO: `{user_elo}`")

# === Stats Command ===
@bot.command()
async def stats(ctx, member: Optional[discord.Member] = None):
    """Display detailed player statistics with pie chart"""
    if member is None:
        member = ctx.author
    
    user_id = str(member.id)
    init_player_stats(member.id)
    
    player_stats = stats_data.get(user_id)
    user_elo = elo_data.get(user_id, 1000)
    peak_elo = player_stats.get("peak_elo", user_elo)
    
    total_games = player_stats["total_games"]
    wins = player_stats["wins"]
    losses = player_stats["losses"]
    draws = player_stats["draws"]
    forfeits = player_stats["forfeits"]
    
    # Calculate win/loss ratio
    if losses > 0:
        wl_ratio = wins / losses
        ratio_text = f"{wl_ratio:.2f}"
    else:
        ratio_text = "∞" if wins > 0 else "N/A"
    
    # Get rank role for color
    role_id = get_role_for_elo(user_elo)
    role = ctx.guild.get_role(role_id) if ctx.guild and role_id else None
    embed_color = role.color if role else discord.Color.blue()
    
    # Create embed
    embed = discord.Embed(
        title=f"📊 Statistics for {member.display_name}",
        color=embed_color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    
    # Add ELO fields
    embed.add_field(name="Current ELO", value=f"`{user_elo}`", inline=True)
    embed.add_field(name="Peak ELO", value=f"`{peak_elo}`", inline=True)
    embed.add_field(name="Total Games", value=f"`{total_games}`", inline=True)
    
    # Add W/L/D fields
    embed.add_field(name="Wins", value=f"`{wins}`", inline=True)
    embed.add_field(name="Losses", value=f"`{losses}`", inline=True)
    embed.add_field(name="Draws", value=f"`{draws}`", inline=True)
    
    # Add streak information
    streak_info = calculate_streaks_from_elo_history(member.id)
    if streak_info['current_streak'] > 0:
        if streak_info['current_streak_type'] == 'win':
            streak_emoji = "🔥"
            streak_text = f"{streak_emoji} `{streak_info['current_streak']}` Win Streak"
        else:
            streak_emoji = "❄️"
            streak_text = f"{streak_emoji} `{streak_info['current_streak']}` Loss Streak"
    else:
        streak_text = "`No active streak`"
    
    embed.add_field(name="Current Streak", value=streak_text, inline=True)
    embed.add_field(name="Best Win Streak", value=f"🏆 `{streak_info['best_win_streak']}`", inline=True)
    embed.add_field(name="Worst Loss Streak", value=f"💀 `{streak_info['best_loss_streak']}`", inline=True)
    
    # Add additional stats
    embed.add_field(name="W/L Ratio", value=f"`{ratio_text}`", inline=True)
    embed.add_field(name="Forfeits", value=f"`{forfeits}`", inline=True)
    
    # Add average completion time
    completion_times = player_stats.get("completion_times", [])
    if completion_times:
        avg_time_seconds = sum(completion_times) / len(completion_times)
        avg_minutes = int(avg_time_seconds // 60)
        avg_seconds = int(avg_time_seconds % 60)
        embed.add_field(
            name="Avg Time",
            value=f"`{avg_minutes}:{avg_seconds:02d}`",
            inline=True
        )
    else:
        embed.add_field(
            name="Avg Time",
            value="`N/A`",
            inline=True
        )
    
    # Mode-specific stats
    mode_display = {
        "stronghold_116": "Stronghold (1.16)",
        "ruined_portal_116": "Ruined Portal (1.16)",
        "village_116": "Village (1.16)",
        "bastion_118": "Bastion (1.18+)",
        "warped_forest_118": "Warped Forest (1.18+)"
    }
    
    mode_stats_text = ""
    for mode, display_name in mode_display.items():
        mode_stats = player_stats["by_mode"][mode]
        mode_wins = mode_stats["wins"]
        mode_losses = mode_stats["losses"]
        mode_draws = mode_stats["draws"]
        mode_total = mode_wins + mode_losses + mode_draws
        
        # Calculate average time for this mode
        mode_times = mode_stats.get("times", [])
        if mode_times:
            avg_time = sum(mode_times) / len(mode_times)
            avg_min = int(avg_time // 60)
            avg_sec = int(avg_time % 60)
            time_str = f" | Avg: `{avg_min}:{avg_sec:02d}`"
        else:
            time_str = ""
        
        if mode_total > 0:
            mode_stats_text += f"**{display_name}**\nW:`{mode_wins}` L:`{mode_losses}` D:`{mode_draws}`{time_str}\n\n"
    
    if mode_stats_text:
        embed.add_field(name="Stats by Mode", value=mode_stats_text, inline=False)
    
    embed.set_footer(
        text=f"Stats requested by {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
    )
    
    # Create pie charts if player has games
    if total_games > 0:
        try:
            # Check if user has ELO history for progression graph
            user_id_str = str(member.id)
            has_elo_history = user_id_str in elo_history and len(elo_history[user_id_str]) > 1
            
            if has_elo_history:
                # Create 3 subplots if we have ELO history
                fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
            else:
                # Create 2 subplots if no ELO history
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            fig.patch.set_alpha(0)
            
            # Overall W/L/D Pie Chart
            overall_data = []
            overall_labels = []
            overall_colors = []
            
            if wins > 0:
                overall_data.append(wins)
                overall_labels.append(f'Wins ({wins})')
                overall_colors.append('#2ecc71')
            if losses > 0:
                overall_data.append(losses)
                overall_labels.append(f'Losses ({losses})')
                overall_colors.append('#e74c3c')
            if draws > 0:
                overall_data.append(draws)
                overall_labels.append(f'Draws ({draws})')
                overall_colors.append('#95a5a6')
            
            if overall_data:
                ax1.set_facecolor('none')
                ax1.pie(overall_data, labels=overall_labels, colors=overall_colors, 
                       autopct='%1.1f%%', startangle=90, textprops={'color': 'white'})
                ax1.set_title(f'Overall Record\n(Total: {total_games} games)', 
                             fontsize=12, fontweight='bold', color='white')
            
            # Mode distribution pie chart
            mode_data = []
            mode_labels = []
            mode_colors = []
            mode_colors_map = {
                "stronghold_116": '#3498db',
                "ruined_portal_116": '#e67e22',
                "village_116": '#f1c40f',
                "bastion_118": '#9b59b6',
                "warped_forest_118": '#1abc9c'
            }
            
            for mode, display_name in mode_display.items():
                mode_stats = player_stats["by_mode"][mode]
                mode_total = mode_stats["wins"] + mode_stats["losses"] + mode_stats["draws"]
                if mode_total > 0:
                    mode_data.append(mode_total)
                    mode_labels.append(f'{display_name}\n({mode_total})')
                    mode_colors.append(mode_colors_map[mode])
            
            if mode_data:
                ax2.set_facecolor('none')
                ax2.pie(mode_data, labels=mode_labels, colors=mode_colors,
                       autopct='%1.1f%%', startangle=90, textprops={'color': 'white'})
                ax2.set_title('Games by Mode', fontsize=12, fontweight='bold', color='white')
            
            # ELO Progression Line Chart (if history exists)
            if has_elo_history:
                ax3.set_facecolor('#2c2f33')
                
                history = elo_history[user_id_str]
                elo_values = [entry["elo"] for entry in history]
                match_numbers = list(range(1, len(elo_values) + 1))
                
                # Plot the line
                ax3.plot(match_numbers, elo_values, color='#5865f2', linewidth=2, marker='o', markersize=4)
                
                # Add a horizontal line at starting ELO (1000)
                ax3.axhline(y=1000, color='#99aab5', linestyle='--', linewidth=1, alpha=0.5)
                
                # Styling
                ax3.set_xlabel('Match Number', color='white', fontsize=10)
                ax3.set_ylabel('ELO Rating', color='white', fontsize=10)
                ax3.set_title('ELO Progression', fontsize=12, fontweight='bold', color='white')
                ax3.tick_params(colors='white', labelsize=8)
                ax3.grid(True, alpha=0.2, color='white')
                
                # Set integer ticks on x-axis
                ax3.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
                
                # Add current ELO annotation on last point
                if elo_values:
                    ax3.annotate(f'{elo_values[-1]}', 
                               xy=(match_numbers[-1], elo_values[-1]),
                               xytext=(5, 5), textcoords='offset points',
                               color='white', fontsize=9, fontweight='bold')
            
            plt.tight_layout()
            
            # Save to buffer with transparent background
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', 
                       transparent=True, facecolor='none')
            buffer.seek(0)
            plt.close()
            
            # Attach image to embed
            file = discord.File(buffer, filename='stats.png')
            embed.set_image(url="attachment://stats.png")
            
            # Send embed with image
            await ctx.send(embed=embed, file=file)
            
        except Exception as e:
            print(f"Error creating chart: {e}")
            await ctx.send(embed=embed)
            
    else:
        embed.add_field(name="No Games Yet", value="*Play your first match to see charts!*", inline=False)
        await ctx.send(embed=embed)

        
# === Leaderboard Command ===
@bot.command()
async def leaderboard(ctx):
    """Display ELO progression graph for top 10 players"""
    if not elo_data:
        await ctx.send("📊 No ELO data available yet.")
        return

    # Get players sorted by ELO, but only keep those with at least 10 games
    sorted_players = sorted(elo_data.items(), key=lambda x: x[1], reverse=True)
    
    # Filter to only players with at least 10 games and ELO history
    players_with_history = []
    for user_id, current_elo in sorted_players:
        user_id_str = str(user_id)
        if user_id_str in elo_history and len(elo_history[user_id_str]) >= 10:
            players_with_history.append((user_id, current_elo))
        if len(players_with_history) >= 10:
            break
    
    if not players_with_history:
        # Fallback to text leaderboard if no one has 10+ games
        leaderboard_text = "🏆 **ELO LEADERBOARD** 🏆\n```\n"
        leaderboard_text += "Not enough players with 10+ games for graph.\n\n"
        sorted_all = sorted(elo_data.items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (user_id, user_elo) in enumerate(sorted_all, 1):
            try:
                user = await bot.fetch_user(int(user_id))
                username = user.name
            except (discord.NotFound, discord.HTTPException, ValueError):
                username = f"User {user_id}"
            leaderboard_text += f"{i:2}. {username:<20} {user_elo:>4}\n"
        leaderboard_text += "```"
        await ctx.send(leaderboard_text)
        return
    
    try:
        # Create figure with dark theme
        fig, ax = plt.subplots(figsize=(16, 10))
        fig.patch.set_facecolor('#2c2f33')
        ax.set_facecolor('#2c2f33')
        
        # Color palette for different players (distinct colors)
        colors = [
            '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6',
            '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b'
        ]
        
        # Medal emojis for legend
        medal_emojis = {0: "🥇", 1: "🥈", 2: "🥉"}
        
        # Find the maximum number of games among selected players
        max_games = max(len(elo_history[str(user_id)]) for user_id, _ in players_with_history)
        
        # Plot each player's ELO progression
        for idx, (user_id, current_elo) in enumerate(players_with_history):
            user_id_str = str(user_id)
            history = elo_history[user_id_str]
            
            # Extract ELO values
            elo_values = [entry["elo"] for entry in history]
            num_games = len(elo_values)
            
            # Stretch the player's games proportionally across the full x-axis
            # Map from game indices [0, num_games-1] to x-axis [1, max_games]
            match_positions = [1 + (i / (num_games - 1)) * (max_games - 1) if num_games > 1 else 1 
                             for i in range(num_games)]
            
            # Get player name
            try:
                user = await bot.fetch_user(int(user_id))
                username = user.name[:15]  # Truncate long names
            except:
                username = f"User {user_id[:8]}"
            
            # Add medal emoji for top 3
            rank = idx + 1
            if rank <= 3:
                label = f"{medal_emojis[idx]} #{rank} {username} ({current_elo}) - {num_games} games"
            else:
                label = f"#{rank} {username} ({current_elo}) - {num_games} games"
            
            # Plot the line
            ax.plot(match_positions, elo_values, 
                   color=colors[idx % len(colors)], 
                   linewidth=2.5, 
                   marker='o', 
                   markersize=3,
                   label=label,
                   alpha=0.8)
        
        # Add horizontal line at starting ELO (1000)
        ax.axhline(y=1000, color='#99aab5', linestyle='--', linewidth=1.5, alpha=0.5, label='Starting ELO (1000)')
        
        # Styling
        ax.set_xlabel('Match Number', color='white', fontsize=14, fontweight='bold')
        ax.set_ylabel('ELO Rating', color='white', fontsize=14, fontweight='bold')
        ax.set_title('🏆 TOP 10 PLAYERS - ELO PROGRESSION 🏆', 
                    fontsize=18, fontweight='bold', color='white', pad=20)
        
        # Customize tick colors and grid
        ax.tick_params(colors='white', labelsize=11)
        ax.grid(True, alpha=0.2, color='white', linestyle='--')
        
        # Set integer ticks on x-axis
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        # Legend with dark background
        legend = ax.legend(loc='upper left', 
                          fontsize=10,
                          framealpha=0.9,
                          facecolor='#23272a',
                          edgecolor='white',
                          labelcolor='white')
        
        # Set legend text color
        for text in legend.get_texts():
            text.set_color('white')
        
        plt.tight_layout()
        
        # Save to buffer with transparent background
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='#2c2f33', edgecolor='none')
        buffer.seek(0)
        plt.close()
        
        # Create embed
        embed = discord.Embed(
            title="📊 Top 10 Players - ELO Progression",
            description=f"Showing ELO progression over time for the current top 10 ranked players (min. 10 games)",
            color=0xFFD700  # Gold
        )
        
        # Add current rankings as text
        rankings_text = ""
        for i, (user_id, user_elo) in enumerate(players_with_history, 1):
            try:
                user = await bot.fetch_user(int(user_id))
                username = user.name[:15]
            except:
                username = f"User {user_id[:8]}"
            
            medal = medal_emojis.get(i-1, f"`{i}`")
            num_games = len(elo_history[str(user_id)])
            rankings_text += f"{medal} **{username}** - `{user_elo}` ELO ({num_games} games)\n"
        
        embed.add_field(
            name="Current Rankings",
            value=rankings_text,
            inline=False
        )
        
        embed.set_footer(
            text=f"Total Ranked Players: {len(elo_data)} • Requested by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        embed.timestamp = discord.utils.utcnow()
        
        # Attach image
        file = discord.File(buffer, filename='leaderboard_progression.png')
        embed.set_image(url="attachment://leaderboard_progression.png")
        
        await ctx.send(embed=embed, file=file)
        
    except Exception as e:
        print(f"❌ Error creating leaderboard graph: {e}")
        # Fallback to text leaderboard
        leaderboard_text = "🏆 **ELO LEADERBOARD** 🏆\n```\n"
        for i, (user_id, user_elo) in enumerate(players_with_history, 1):
            try:
                user = await bot.fetch_user(int(user_id))
                username = user.name
            except (discord.NotFound, discord.HTTPException, ValueError):
                username = f"User {user_id}"
            leaderboard_text += f"{i:2}. {username:<20} {user_elo:>4}\n"
        leaderboard_text += "```"
        await ctx.send(leaderboard_text)

def calculate_streaks_from_elo_history(user_id):
    """Calculate current and best win/loss streaks from ELO history"""
    user_id_str = str(user_id)
    
    if user_id_str not in elo_history or len(elo_history[user_id_str]) < 2:
        return {
            'current_streak': 0,
            'current_streak_type': None,
            'best_win_streak': 0,
            'best_loss_streak': 0
        }
    
    history = elo_history[user_id_str]
    
    current_streak = 0
    current_streak_type = None  # 'win' or 'loss'
    best_win_streak = 0
    best_loss_streak = 0
    temp_win_streak = 0
    temp_loss_streak = 0
    
    # Start from second entry (index 1) since we need to compare with previous
    for i in range(1, len(history)):
        prev_elo = history[i-1]["elo"]
        curr_elo = history[i]["elo"]
        
        if curr_elo > prev_elo:
            # ELO went up = win
            temp_win_streak += 1
            temp_loss_streak = 0
            
            if temp_win_streak > best_win_streak:
                best_win_streak = temp_win_streak
            
            # Update current streak
            if current_streak_type == 'win':
                current_streak += 1
            else:
                current_streak = 1
                current_streak_type = 'win'
                
        elif curr_elo < prev_elo:
            # ELO went down = loss
            temp_loss_streak += 1
            temp_win_streak = 0
            
            if temp_loss_streak > best_loss_streak:
                best_loss_streak = temp_loss_streak
            
            # Update current streak
            if current_streak_type == 'loss':
                current_streak += 1
            else:
                current_streak = 1
                current_streak_type = 'loss'
        # If ELO stays same (draw), streaks reset
        else:
            temp_win_streak = 0
            temp_loss_streak = 0
            current_streak = 0
            current_streak_type = None
    
    return {
        'current_streak': current_streak,
        'current_streak_type': current_streak_type,
        'best_win_streak': best_win_streak,
        'best_loss_streak': best_loss_streak
    }

@bot.command()
async def compare(ctx, member1: discord.Member = None, member2: discord.Member = None):
    """Compare stats between two players. Usage: !compare @player1 @player2 or !compare @player (compares you vs that player)"""
    
    # If no arguments provided, show usage
    if member1 is None and member2 is None:
        await ctx.send("❌ Usage: `!compare @player1 @player2` or `!compare @player` (to compare yourself)")
        return
    
    # If only one member provided, compare ctx.author vs that member
    if member2 is None:
        member2 = member1
        member1 = ctx.author
    
    # Prevent comparing a player to themselves
    if member1.id == member2.id:
        await ctx.send("❌ Cannot compare a player to themselves!")
        return
    
    user1_id = str(member1.id)
    user2_id = str(member2.id)
    
    init_player_stats(member1.id)
    init_player_stats(member2.id)
    
    user1_stats = stats_data.get(user1_id)
    user2_stats = stats_data.get(user2_id)
    user1_elo = elo_data.get(user1_id, 1000)
    user2_elo = elo_data.get(user2_id, 1000)
    
    # Get head-to-head record (member1 vs member2)
    h2h_user1 = user1_stats.get("head_to_head", {}).get(user2_id, {"wins": 0, "losses": 0})
    
    user1_wins_vs_user2 = h2h_user1["wins"]
    user1_losses_vs_user2 = h2h_user1["losses"]
    total_matches = user1_wins_vs_user2 + user1_losses_vs_user2
    
    # Create comparison embed
    embed = discord.Embed(
        title="⚔️ HEAD-TO-HEAD COMPARISON",
        description=f"{member1.display_name} vs {member2.display_name}",
        color=0x3498db
    )
    
    # Head-to-head record
    if total_matches > 0:
        if user1_wins_vs_user2 > user1_losses_vs_user2:
            record_emoji = "🟢"
            record_color = 0x2ecc71
        elif user1_wins_vs_user2 < user1_losses_vs_user2:
            record_emoji = "🔴"
            record_color = 0xe74c3c
        else:
            record_emoji = "🟡"
            record_color = 0xf39c12
        
        embed.color = record_color
        embed.add_field(
            name=f"{record_emoji} {member1.display_name}'s Record vs {member2.display_name}",
            value=f"**{user1_wins_vs_user2}W - {user1_losses_vs_user2}L** ({total_matches} total matches)",
            inline=False
        )
        
        if total_matches > 0:
            win_rate = (user1_wins_vs_user2 / total_matches) * 100
            embed.add_field(
                name=f"{member1.display_name}'s Win Rate",
                value=f"`{win_rate:.1f}%`",
                inline=True
            )
    else:
        embed.add_field(
            name="⚪ No Matches Yet",
            value=f"{member1.display_name} and {member2.display_name} haven't played against each other yet!",
            inline=False
        )
    
    embed.add_field(name="\u200b", value="\u200b", inline=False)  # Spacer
    
    # Overall stats comparison
    user1_total = user1_stats["wins"] + user1_stats["losses"]
    user2_total = user2_stats["wins"] + user2_stats["losses"]
    
    user1_winrate = (user1_stats["wins"] / user1_total * 100) if user1_total > 0 else 0
    user2_winrate = (user2_stats["wins"] / user2_total * 100) if user2_total > 0 else 0
    
    # User 1 stats column
    embed.add_field(
        name=f"📊 {member1.display_name}",
        value=(
            f"**ELO:** `{user1_elo}`\n"
            f"**Record:** {user1_stats['wins']}W - {user1_stats['losses']}L\n"
            f"**Win Rate:** `{user1_winrate:.1f}%`\n"
            f"**Peak ELO:** `{user1_stats.get('peak_elo', user1_elo)}`"
        ),
        inline=True
    )
    
    # VS separator
    elo_diff = user1_elo - user2_elo
    if elo_diff > 0:
        diff_text = f"**+{elo_diff}** ELO\nahead"
    elif elo_diff < 0:
        diff_text = f"**{abs(elo_diff)}** ELO\nbehind"
    else:
        diff_text = "**Equal**\nELO"
    
    embed.add_field(
        name="⚔️",
        value=diff_text,
        inline=True
    )
    
    # User 2 stats column
    embed.add_field(
        name=f"📊 {member2.display_name}",
        value=(
            f"**ELO:** `{user2_elo}`\n"
            f"**Record:** {user2_stats['wins']}W - {user2_stats['losses']}L\n"
            f"**Win Rate:** `{user2_winrate:.1f}%`\n"
            f"**Peak ELO:** `{user2_stats.get('peak_elo', user2_elo)}`"
        ),
        inline=True
    )
    
    # Average completion time comparison
    user1_times = user1_stats.get("completion_times", [])
    user2_times = user2_stats.get("completion_times", [])
    
    if user1_times and user2_times:
        user1_avg = sum(user1_times) / len(user1_times)
        user2_avg = sum(user2_times) / len(user2_times)
        
        user1_min = int(user1_avg // 60)
        user1_sec = int(user1_avg % 60)
        user2_min = int(user2_avg // 60)
        user2_sec = int(user2_avg % 60)
        
        time_diff = user1_avg - user2_avg
        if time_diff < 0:
            time_diff_text = f"{member1.display_name} is `{abs(int(time_diff))}s` faster ⚡"
        elif time_diff > 0:
            time_diff_text = f"{member2.display_name} is `{int(time_diff)}s` faster ⚡"
        else:
            time_diff_text = "Same average time"
        
        embed.add_field(
            name="⏱️ Average Completion Time",
            value=(
                f"**{member1.display_name}:** `{user1_min}:{user1_sec:02d}`\n"
                f"**{member2.display_name}:** `{user2_min}:{user2_sec:02d}`\n"
                f"{time_diff_text}"
            ),
            inline=False
        )
    
    embed.set_footer(
        text=f"Comparison requested by {ctx.author.display_name}",
        icon_url=ctx.author.display_avatar.url
    )
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)

# === Ranking Command ===
@bot.command()
async def ranking(ctx, member: Optional[discord.Member] = None):
    """Show your ranking position out of all players"""
    if member is None:
        member = ctx.author
    
    if not elo_data:
        await ctx.send("📊 No ELO data available yet.")
        return
    
    user_id = str(member.id)
    user_elo = elo_data.get(user_id, 1000)
    
    # Sort players by ELO
    sorted_players = sorted(elo_data.items(), key=lambda x: x[1], reverse=True)
    total_players = len(sorted_players)
    
    # Find user's position
    position = None
    for i, (player_id, player_elo) in enumerate(sorted_players, 1):
        if player_id == user_id:
            position = i
            break
    
    if position is None:
        # User not in rankings yet
        await ctx.send(f"📊 **{member.display_name}** is unranked (Default ELO: `{user_elo}`)")
        return
    
    # Calculate percentile
    percentile = ((total_players - position) / total_players) * 100
    
    # Determine rank emoji
    if position == 1:
        rank_emoji = "🥇"
    elif position == 2:
        rank_emoji = "🥈"
    elif position == 3:
        rank_emoji = "🥉"
    elif position <= 10:
        rank_emoji = "🏆"
    else:
        rank_emoji = "📊"
    
    # Show players around them (±2 positions)
    context_start = max(0, position - 3)
    context_end = min(len(sorted_players), position + 2)
    
    ranking_text = f"{rank_emoji} **Ranking for {member.display_name}**\n\n"
    ranking_text += f"**Position:** `#{position}` out of `{total_players}` players\n"
    ranking_text += f"**ELO:** `{user_elo}`\n"
    ranking_text += f"**Percentile:** Top `{100 - percentile:.1f}%`\n\n"
    
    # Show nearby players
    ranking_text += "```\n"
    for i in range(context_start, context_end):
        rank = i + 1
        player_id, player_elo = sorted_players[i]
        
        try:
            player = await bot.fetch_user(int(player_id))
            player_name = player.name[:18]
        except:
            player_name = f"User {player_id[:8]}"
        
        # Highlight current user
        if player_id == user_id:
            ranking_text += f"→ {rank:2}. {player_name:<18} {player_elo:>4}\n"
        else:
            ranking_text += f"  {rank:2}. {player_name:<18} {player_elo:>4}\n"
    
    ranking_text += "```"
    
    await ctx.send(ranking_text)


@bot.command()
async def change(ctx):
    """Request a new seed during an active match - requires opponent approval"""
    user_id = ctx.author.id
    
    if user_id not in active_challenges:
        await ctx.send("❌ You can only use !change during an active match. Start with `!challenge @user` or `!private @user1 @user2...` first.")
        return
    
    challenge_state = active_challenges[user_id]
    mode = challenge_state['mode']
    current_seed = challenge_state['seed']
    
    seed_map = {
        'stronghold_116': (codici_116, "1.16 Stronghold"),
        'ruined_portal_116': (rpcodici_116, "1.16 Ruined Portal"),
        'village_116': (village_116, "1.16 Village"),
        'bastion_118': (bastion_118, "1.18+ Bastion"),
        'warped_forest_118': (warped_118, "1.18+ Warped Forest")
    }
    
    seed_array, mode_display = seed_map.get(mode, ([], "Unknown"))
    
    if not seed_array:
        await ctx.send(f"❌ No {mode_display.lower()} seeds available!")
        return

    # Get opponent(s)
    if challenge_state.get('multi_player', False):
        all_player_ids = challenge_state.get('all_players', [])
        opponent_ids = [p_id for p_id in all_player_ids if p_id != user_id]
    else:
        opponent_ids = [challenge_state['opponent_id']]
    
    # Create change request message
    opponent_mentions = " ".join([f"<@{o_id}>" for o_id in opponent_ids])
    change_msg = await ctx.send(
        f"🔁 **Seed Change Request**\n"
        f"{ctx.author.mention} wants to change the seed.\n"
        f"{opponent_mentions}, react with ✅ to accept or ❌ to decline."
    )
    
    await change_msg.add_reaction("✅")
    await change_msg.add_reaction("❌")
    
    # Track reactions from all opponents
    reactions_tracker = {o_id: None for o_id in opponent_ids}
    
    def change_check(reaction, user):
        return (user.id in opponent_ids and 
                str(reaction.emoji) in ["✅", "❌"] and 
                reaction.message.id == change_msg.id)
    
    try:
        # Wait for all opponents to react (60 second timeout)
        start_time = time.time()
        while any(v is None for v in reactions_tracker.values()):
            if time.time() - start_time > 60:
                raise asyncio.TimeoutError
                
            reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=change_check)
            reactions_tracker[user.id] = str(reaction.emoji)
            
            # Update message with status
            status_lines = []
            for o_id in opponent_ids:
                try:
                    opponent = await bot.fetch_user(o_id)
                    status = "✅" if reactions_tracker[o_id] == "✅" else "❌" if reactions_tracker[o_id] == "❌" else "⏳"
                    status_lines.append(f"{opponent.mention}: {status}")
                except:
                    pass
            
            await change_msg.edit(content=
                f"🔁 **Seed Change Request**\n"
                f"{ctx.author.mention} wants to change the seed.\n"
                f"{opponent_mentions}, react with ✅ to accept or ❌ to decline.\n\n"
                + " | ".join(status_lines)
            )
        
        # Check if all opponents accepted
        if all(v == "✅" for v in reactions_tracker.values()):
            # All accepted - now ask about reporting
            report_msg = await ctx.send(
                f"📝 **Report Current Seed?**\n"
                f"Current seed: `{current_seed}` ({mode_display})\n"
                f"Should this seed be reported as problematic?\n"
                f"**All players must agree:**\n"
                f"🚩 - Report seed\n"
                f"⏭️ - Skip (just get new seed)\n"
            )
            
            await report_msg.add_reaction("🚩")
            await report_msg.add_reaction("⏭️")
            
            # Reset tracker for all players (including initiator)
            all_player_ids = [user_id] + opponent_ids
            report_tracker = {p_id: None for p_id in all_player_ids}
            
            def report_check(reaction, user):
                return (user.id in all_player_ids and 
                        str(reaction.emoji) in ["🚩", "⏭️"] and 
                        reaction.message.id == report_msg.id)
            
            try:
                # Wait for all players to react (60 second timeout)
                start_time = time.time()
                while any(v is None for v in report_tracker.values()):
                    if time.time() - start_time > 60:
                        raise asyncio.TimeoutError
                        
                    reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=report_check)
                    report_tracker[user.id] = str(reaction.emoji)
                    
                    # Update message with status
                    status_lines = []
                    for p_id in all_player_ids:
                        try:
                            player = await bot.fetch_user(p_id)
                            status = "🚩" if report_tracker[p_id] == "🚩" else "⏭️" if report_tracker[p_id] == "⏭️" else "⏳"
                            status_lines.append(f"{player.mention}: {status}")
                        except:
                            pass
                    
                    await report_msg.edit(content=
                        f"📝 **Report Current Seed?**\n"
                        f"Current seed: `{current_seed}` ({mode_display})\n"
                        f"Should this seed be reported as problematic?\n"
                        f"**All players must agree:**\n"
                        f"🚩 - Report seed\n"
                        f"⏭️ - Skip (just get new seed)\n\n"
                        + " | ".join(status_lines)
                    )
                
                # Check if all agreed to report
                if all(v == "🚩" for v in report_tracker.values()):
                    save_reported_seed(current_seed, mode_display)
                    report_result = f"🚩 Seed `{current_seed}` has been reported!"
                else:
                    report_result = f"⏭️ Seed not reported."
                
            except asyncio.TimeoutError:
                report_result = f"⏰ Report vote timed out. Seed not reported."
            
            # Get new seed
            new_seed = random.choice(seed_array)
            
            # Update seed for all players in the match
            if challenge_state.get('multi_player', False):
                all_player_ids = challenge_state.get('all_players', [])
                for player_id in all_player_ids:
                    if player_id in active_challenges:
                        active_challenges[player_id]['seed'] = new_seed
            else:
                # 2-player match
                opponent_id = challenge_state['opponent_id']
                active_challenges[user_id]['seed'] = new_seed
                if opponent_id in active_challenges:
                    active_challenges[opponent_id]['seed'] = new_seed
            
            await ctx.send(
                f"✅ Seed change accepted!\n"
                f"{report_result}\n"
                f"New {mode_display} seed: `{new_seed}`"
            )
        else:
            # At least one declined
            await ctx.send(f"❌ Seed change declined. Continuing with current seed.")
        
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Seed change request expired. Continuing with current seed.")

@bot.command()
async def cancel(ctx):
    """Request to cancel the current match - requires opponent approval"""
    user_id = ctx.author.id
    
    if user_id not in active_challenges:
        await ctx.send("❌ You are not currently in a match!")
        return
    
    challenge_state = active_challenges[user_id]
    is_ranked = challenge_state.get('ranked', False)
    is_multi_player = challenge_state.get('multi_player', False)
    thread_id = challenge_state.get('thread_id')
    
    # Get opponent(s)
    if is_multi_player:
        all_player_ids = challenge_state.get('all_players', [])
        opponent_ids = [p_id for p_id in all_player_ids if p_id != user_id]
    else:
        opponent_ids = [challenge_state['opponent_id']]
    
    # Create cancel request message
    opponent_mentions = " ".join([f"<@{o_id}>" for o_id in opponent_ids])
    cancel_msg = await ctx.send(
        f"🚫 **Match Cancellation Request**\n"
        f"{ctx.author.mention} wants to cancel the match.\n"
        f"{opponent_mentions}, react with ✅ to agree or ❌ to decline.\n"
        f"*No ELO or stats will be recorded*"
    )
    
    await cancel_msg.add_reaction("✅")
    await cancel_msg.add_reaction("❌")
    
    # Track reactions from all opponents
    reactions_tracker = {o_id: None for o_id in opponent_ids}
    
    def cancel_check(reaction, user):
        return (user.id in opponent_ids and 
                str(reaction.emoji) in ["✅", "❌"] and 
                reaction.message.id == cancel_msg.id)
    
    try:
        # Wait for all opponents to react (60 second timeout)
        start_time = time.time()
        while any(v is None for v in reactions_tracker.values()):
            if time.time() - start_time > 60:
                raise asyncio.TimeoutError
                
            reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=cancel_check)
            reactions_tracker[user.id] = str(reaction.emoji)
            
            # Update message with status
            status_lines = []
            for o_id in opponent_ids:
                try:
                    opponent = await bot.fetch_user(o_id)
                    status = "✅" if reactions_tracker[o_id] == "✅" else "❌" if reactions_tracker[o_id] == "❌" else "⏳"
                    status_lines.append(f"{opponent.mention}: {status}")
                except:
                    pass
            
            await cancel_msg.edit(content=
                f"🚫 **Match Cancellation Request**\n"
                f"{ctx.author.mention} wants to cancel the match.\n"
                f"{opponent_mentions}, react with ✅ to agree or ❌ to decline.\n"
                f"*No ELO or stats will be recorded*\n\n"
                + " | ".join(status_lines)
            )
        
        # Check if all opponents agreed
        if all(v == "✅" for v in reactions_tracker.values()):
            # All agreed to cancel - just remove from active challenges
            
            if is_multi_player:
                all_player_ids = challenge_state.get('all_players', [])
                for player_id in all_player_ids:
                    active_challenges.pop(player_id, None)
            else:
                active_challenges.pop(user_id, None)
                active_challenges.pop(opponent_ids[0], None)
            
            # Clean up thread tracking and archive
            if thread_id:
                active_match_threads.pop(thread_id, None)
                try:
                    thread = bot.get_channel(thread_id)
                    if thread:
                        await thread.edit(archived=True)
                        print(f"✅ Archived thread after cancellation")
                except Exception as e:
                    print(f"⚠️ Could not archive thread: {e}")
            
            await ctx.send(
                f"🚫 **Match cancelled by mutual agreement!**\n"
                f"*No ELO changes or stats recorded*"
            )
        else:
            # At least one declined
            await ctx.send(f"❌ Match cancellation declined. Match continues.")
        
    except asyncio.TimeoutError:
        await ctx.send(f"⏰ Cancellation request expired. Match continues.")

@bot.command()
async def forfeit(ctx):
    """Forfeit the current ranked match (only for ranked matches)"""
    user_id = ctx.author.id
    
    if user_id not in active_challenges:
        await ctx.send("❌ You are not currently in a match!")
        return
    
    challenge_state = active_challenges[user_id]
    is_ranked = challenge_state.get('ranked', False)
    
    if not is_ranked:
        await ctx.send("❌ You can only forfeit ranked matches! Use `!cancel` for unranked matches.")
        return
    
    is_multi_player = challenge_state.get('multi_player', False)
    
    if is_multi_player:
        await ctx.send("❌ Forfeit is not available for multi-player matches. Use `!cancel` instead.")
        return
    
    opponent_id = challenge_state['opponent_id']
    game_mode = challenge_state['mode']
    thread_id = challenge_state.get('thread_id')
    
    # Remove both players from active challenges
    active_challenges.pop(user_id, None)
    active_challenges.pop(opponent_id, None)
    
    # Clean up thread tracking
    if thread_id:
        active_match_threads.pop(thread_id, None)
    
    # Get player objects
    forfeiter = ctx.author
    opponent = await bot.fetch_user(opponent_id)
    
    # Store OLD ELO values BEFORE updating
    old_forfeiter_elo = elo_data.get(str(user_id), 1000)
    old_opponent_elo = elo_data.get(str(opponent_id), 1000)
    
    # Record forfeit result (opponent wins, forfeiter loses)
    record_game_result(opponent_id, user_id, game_mode, is_forfeit=True)
    
    # Update ELO
    update_elo(opponent_id, user_id)
    
    # Get NEW ELO values AFTER updating
    forfeiter_elo = elo_data.get(str(user_id), 1000)
    opponent_elo = elo_data.get(str(opponent_id), 1000)
    
    # Update roles
    if ctx.guild:
        forfeiter_member = ctx.guild.get_member(user_id)
        opponent_member = ctx.guild.get_member(opponent_id)
        
        if forfeiter_member:
            await update_user_roles(forfeiter_member, forfeiter_elo)
        if opponent_member:
            await update_user_roles(opponent_member, opponent_elo)
    
    # Calculate ELO changes
    forfeiter_change = forfeiter_elo - old_forfeiter_elo
    opponent_change = opponent_elo - old_opponent_elo
    
    # Get updated stats
    forfeiter_stats = stats_data.get(str(user_id))
    opponent_stats = stats_data.get(str(opponent_id))
    
    f_wins = forfeiter_stats["wins"]
    f_losses = forfeiter_stats["losses"]
    
    o_wins = opponent_stats["wins"]
    o_losses = opponent_stats["losses"]
    
    # Create forfeit result embed
    embed = discord.Embed(
        title="🏳️ FORFEIT",
        description=f"**{forfeiter.display_name}** forfeited the match!\n**{opponent.display_name}** wins by forfeit!",
        color=0xe74c3c  # Red for forfeit
    )
    
    embed.set_thumbnail(url=opponent.display_avatar.url)
    
    # Winner stats
    embed.add_field(
        name=f"👑 {opponent.display_name} (Winner)",
        value=(
            f"**ELO:** `{opponent_elo}` *({opponent_change:+d})*\n"
            f"**Record:** {o_wins}W - {o_losses}L"
        ),
        inline=True
    )
    
    # VS separator
    embed.add_field(
        name="\u200b",
        value="\u200b",
        inline=True
    )
    
    # Forfeiter stats
    embed.add_field(
        name=f"{forfeiter.display_name} (Forfeited)",
        value=(
            f"**ELO:** `{forfeiter_elo}` *({forfeiter_change:+d})*\n"
            f"**Record:** {f_wins}W - {f_losses}L"
        ),
        inline=True
    )
    
    embed.set_footer(text="Match forfeited")
    embed.timestamp = discord.utils.utcnow()
    
    await ctx.send(embed=embed)
    
    # Notify opponent via DM
    try:
        await opponent.send(
            f"🏳️ **{forfeiter.display_name}** forfeited your ranked match!\n"
            f"You win by forfeit!\n"
            f"**ELO Change:** `{opponent_change:+d}` (Now: `{opponent_elo}`)"
        )
    except:
        pass
    
    # Archive thread if it exists
    if thread_id:
        try:
            thread = bot.get_channel(thread_id)
            if thread:
                await thread.edit(archived=True)
                print(f"✅ Archived thread after forfeit")
        except Exception as e:
            print(f"⚠️ Could not archive thread: {e}")

# === Queue Command (Automatic Matchmaking) ===
@bot.command()
async def queue(ctx):
    """Join matchmaking queue - automatically matches players"""
    user_id = ctx.author.id
    
    # Delete the user's command message
    try:
        await ctx.message.delete()
    except:
        pass
    
    # Check if this is being used in DMs or the queue channel
    is_dm = isinstance(ctx.channel, discord.DMChannel)
    is_queue_channel = QUEUE_CHANNEL_ID and ctx.channel.id == QUEUE_CHANNEL_ID
    
    if not is_dm and not is_queue_channel:
        temp_msg = await ctx.send("❌ Please use `!queue` in DMs or in the dedicated queue channel!")
        await asyncio.sleep(5)
        try:
            await temp_msg.delete()
        except:
            pass
        return
    
    # Check if user is already in a match
    if user_id in active_challenges:
        try:
            await ctx.author.send("❌ You are already in an active match! Finish it before queueing again.")
        except:
            pass
        return
    
    # Check if user is already in any queue
    in_116 = user_id in queue_116
    in_118 = user_id in queue_118
    
    if in_116 or in_118:
        # User is leaving all queues
        if in_116:
            queue_116.remove(user_id)
        if in_118:
            queue_118.remove(user_id)
        
        queues_left = []
        if in_116:
            queues_left.append("1.16")
        if in_118:
            queues_left.append("1.18+")
        
        # Remove from reminder tracking
        queue_join_times.pop(user_id, None)
        
        # Send DM confirmation
        try:
            await ctx.author.send(
                f"❌ You left the queue(s): {', '.join(queues_left)}\n"
                f"**Queue sizes:** 1.16: `{len(queue_116)}` | 1.18+: `{len(queue_118)}`"
            )
        except:
            pass
        
        # Update persistent queue message
        await update_queue_status_message()
        return
    
    # User is joining - ask which queue(s) via DM
    try:
        queue_msg = await ctx.author.send(
            f"Which queue do you want to join?\n"
            f"**Select version:**\n"
            f"{CUSTOM_EMOJIS['116']} - 1.16 only\n"
            f"{CUSTOM_EMOJIS['118']} - 1.18+ only\n"
            f"🔵 - Both queues\n\n"
            f"**React to join!**"
        )
    except discord.Forbidden:
        # User has DMs disabled, send temporary message in channel
        if is_queue_channel:
            temp_msg = await ctx.send(
                f"{ctx.author.mention} Please enable DMs to use the queue system!"
            )
            await asyncio.sleep(5)
            try:
                await temp_msg.delete()
            except:
                pass
        return
    
    await queue_msg.add_reaction(CUSTOM_EMOJIS['116'])
    await queue_msg.add_reaction(CUSTOM_EMOJIS['118'])
    await queue_msg.add_reaction("🔵")

    def queue_check(reaction, user):
        return (user.id == ctx.author.id and 
                str(reaction.emoji) in [CUSTOM_EMOJIS['116'], CUSTOM_EMOJIS['118'], "🔵"] and 
                reaction.message.id == queue_msg.id)
    
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=queue_check)
        chosen_queue = str(reaction.emoji)

        joined_queues = []

        if chosen_queue == CUSTOM_EMOJIS['116']:
            queue_116.append(user_id)
            joined_queues.append("1.16")
        elif chosen_queue == CUSTOM_EMOJIS['118']:
            queue_118.append(user_id)
            joined_queues.append("1.18+")
        else:  # 🔵
            queue_116.append(user_id)
            queue_118.append(user_id)
            joined_queues.append("1.16 and 1.18+")

        # Track queue join time for reminder
        queue_join_times[user_id] = time.time()
        
        # Send DM confirmation
        await ctx.author.send(
            f"✅ You joined queue(s): {', '.join(joined_queues)}\n"
            f"**Queue sizes:** 1.16: `{len(queue_116)}` | 1.18+: `{len(queue_118)}`\n"
            f"⏳ Waiting for opponent... You'll be notified when a match is found!"
        )
        
        # Delete the queue selection message
        try:
            await queue_msg.delete()
        except:
            pass
        
        # Update persistent queue message
        await update_queue_status_message()
        
        # Try to create matches
        await try_create_matches()
        
    except asyncio.TimeoutError:
        await ctx.author.send(f"⏰ Time's up! Use `!queue` again to join.")
        # Delete the expired queue message
        try:
            await queue_msg.delete()
        except:
            pass
        return

async def try_create_matches():
    """Try to create matches from queue"""
    # Try 1.16 queue first
    while len(queue_116) >= 2:
        if not await create_match_from_queue(queue_116, "1.16"):
            break  # No available channels
    
    # Try 1.18+ queue
    while len(queue_118) >= 2:
        if not await create_match_from_queue(queue_118, "1.18+"):
            break  # No available channels
    
    # Update queue status message after processing
    await update_queue_status_message()

async def create_match_from_queue(queue, version):
    """Create a match from queue players. Returns True if successful, False if no channels available."""
    if len(queue) < 2:
        return True
    
    # Always use the first match channel
    match_channel = bot.get_channel(MATCH_CHANNELS[0])
    
    if not match_channel:
        # Channel not found - notify first two players
        try:
            player1 = await bot.fetch_user(queue[0])
            player2 = await bot.fetch_user(queue[1])
            await player1.send("⚠️ Match channel not found. Please contact an administrator!")
            await player2.send("⚠️ Match channel not found. Please contact an administrator!")
        except:
            pass
        return False
    
    # Get first two players from queue
    player1_id = queue.pop(0)
    player2_id = queue.pop(0)
    
    # Remove from other queue if they were in both
    other_queue = queue_118 if version == "1.16" else queue_116
    if player1_id in other_queue:
        other_queue.remove(player1_id)
    if player2_id in other_queue:
        other_queue.remove(player2_id)
    
    # Remove from reminder tracking
    queue_join_times.pop(player1_id, None)
    queue_join_times.pop(player2_id, None)
    
    try:
        player1 = await bot.fetch_user(player1_id)
        player2 = await bot.fetch_user(player2_id)
    except:
        # Failed to fetch users, put them back
        queue.insert(0, player2_id)
        queue.insert(0, player1_id)
        return True
    
    # For 1.18+, ask if both players can run with pack
    can_use_bastion = False
    if version == "1.18+":
        # Create temporary message in main channel for pack check
        pack_msg = await match_channel.send(
            f"📦 **Pack Check**\n"
            f"{player1.mention} and {player2.mention}\n"
            f"Can both of you run with pack?\n"
            f"✅ - Yes (Bastion or Warped Forest)\n"
            f"❌ - No (Warped Forest only)"
        )
        
        await pack_msg.add_reaction("✅")
        await pack_msg.add_reaction("❌")
        
        reactions_tracker = {player1_id: None, player2_id: None}
        
        def pack_check(reaction, user):
            return (user.id in [player1_id, player2_id] and 
                    str(reaction.emoji) in ["✅", "❌"] and 
                    reaction.message.id == pack_msg.id)
        
        try:
            # Wait for both players to react (60 second timeout)
            start_time = time.time()
            while any(v is None for v in reactions_tracker.values()):
                if time.time() - start_time > 60:
                    raise asyncio.TimeoutError
                    
                reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=pack_check)
                reactions_tracker[user.id] = str(reaction.emoji)
                
                # Update message with status
                p1_status = "✅" if reactions_tracker[player1_id] == "✅" else "❌" if reactions_tracker[player1_id] == "❌" else "⏳"
                p2_status = "✅" if reactions_tracker[player2_id] == "✅" else "❌" if reactions_tracker[player2_id] == "❌" else "⏳"
                
                await pack_msg.edit(content=
                    f"📦 **Pack Check**\n"
                    f"{player1.mention} {p1_status} | {player2.mention} {p2_status}\n"
                    f"Can both of you run with pack?\n"
                    f"✅ - Yes (Bastion or Warped Forest)\n"
                    f"❌ - No (Warped Forest only)"
                )
            
            # Delete the pack check message
            try:
                await pack_msg.delete()
            except:
                pass
            
            # Both players can use pack only if both said yes
            can_use_bastion = all(v == "✅" for v in reactions_tracker.values())
            
        except asyncio.TimeoutError:
            await match_channel.send(f"⏰ Pack check timed out! Match cancelled.")
            # Delete pack check message
            try:
                await pack_msg.delete()
            except:
                pass
            
            # Notify players via DM that match was cancelled
            try:
                await player1.send("❌ Your match was cancelled due to pack check timeout.")
            except:
                pass
            try:
                await player2.send("❌ Your match was cancelled due to pack check timeout.")
            except:
                pass
            
            # DON'T put players back in queue - match is cancelled
            return True
    
    # Randomly select game mode based on version
    if version == "1.16":
        rand = random.random()
        if rand < 0.50:  # 50% chance
            game_mode = "village_116"
            seed_array = village_116
            emoji = CUSTOM_EMOJIS['village']
            mode_display = "Village"
        elif rand < 0.75:  # 25% chance
            game_mode = "stronghold_116"
            seed_array = codici_116
            emoji = CUSTOM_EMOJIS['stronghold']
            mode_display = "Stronghold"
        else:  # 25% chance
            game_mode = "ruined_portal_116"
            seed_array = rpcodici_116
            emoji = CUSTOM_EMOJIS['ruined_portal']
            mode_display = "Ruined Portal"
    else:  # 1.18+
        if can_use_bastion and random.random() < 0.5:
            game_mode = "bastion_118"
            seed_array = bastion_118
            emoji = "<:bastion:1438457977374900415>"
            mode_display = "Bastion"
        else:
            game_mode = "warped_forest_118"
            seed_array = warped_118
            emoji = "<:warped:1438457958739742740>"
            mode_display = "Warped Forest"
    
    if not seed_array:
        await match_channel.send(f"❌ No {mode_display} seeds available! Match cancelled.")
        return True
    
    initial_seed = random.choice(seed_array)
    
    # Create match state
    challenge_state = {
        'opponent_id': player2_id,
        'version': version,
        'mode': game_mode,
        'seed': initial_seed,
        'ranked': True
    }
    opponent_state = {
        'opponent_id': player1_id,
        'version': version,
        'mode': game_mode,
        'seed': initial_seed,
        'ranked': True
    }
    
    active_challenges[player1_id] = challenge_state
    active_challenges[player2_id] = opponent_state
    
    player1_elo = elo_data.get(str(player1_id), 1000)
    player2_elo = elo_data.get(str(player2_id), 1000)
    
    # Create thread name
    thread_name = f"{player1.name} vs {player2.name} - {version} {mode_display}"
    if len(thread_name) > 100:  # Discord thread name limit
        thread_name = f"{player1.name[:20]} vs {player2.name[:20]} - {mode_display}"
    
    try:
        # Create a new thread in the match channel
        match_thread = await match_channel.create_thread(
            name=thread_name,
            type=discord.ChannelType.public_thread,
            auto_archive_duration=60  # Auto-archive after 1 hour of inactivity
        )
        
        # Track this thread
        active_match_threads[match_thread.id] = [player1_id, player2_id]
        
        # Store thread ID in challenge state
        active_challenges[player1_id]['thread_id'] = match_thread.id
        active_challenges[player2_id]['thread_id'] = match_thread.id
        
        # Get player stats
        init_player_stats(player1_id)
        init_player_stats(player2_id)
        
        player1_stats = stats_data.get(str(player1_id))
        player2_stats = stats_data.get(str(player2_id))
        
        p1_wins = player1_stats["wins"]
        p1_losses = player1_stats["losses"]
        p1_total = p1_wins + p1_losses
        p1_winrate = f"{(p1_wins/p1_total*100):.1f}%" if p1_total > 0 else "N/A"
        
        p2_wins = player2_stats["wins"]
        p2_losses = player2_stats["losses"]
        p2_total = p2_wins + p2_losses
        p2_winrate = f"{(p2_wins/p2_total*100):.1f}%" if p2_total > 0 else "N/A"
        
        # Determine embed color based on mode
        color_map = {
            "stronghold_116": 0x3498db,      # Blue
            "ruined_portal_116": 0xe67e22,   # Orange
            "bastion_118": 0x9b59b6,          # Purple
            "warped_forest_118": 0x1abc9c    # Teal
        }
        embed_color = color_map.get(game_mode, 0x2ecc71)

        # Get emoji for mode
        mode_emoji_map = {
            "stronghold_116": CUSTOM_EMOJIS['stronghold'],
            "ruined_portal_116": CUSTOM_EMOJIS['ruined_portal'],
            "village_116": CUSTOM_EMOJIS['village'],
            "bastion_118": CUSTOM_EMOJIS['bastion'],
            "warped_forest_118": CUSTOM_EMOJIS['warped']
        }
        emoji = mode_emoji_map.get(game_mode, "🎮")

        # Create embed
        embed = discord.Embed(
            title=f"{emoji} RANKED MATCH",
            description=f"**{version} • {mode_display}**",
            color=embed_color
        )
        
        # Player 1 field
        embed.add_field(
            name=f"{player1.display_name}",
            value=(
                f"**ELO:** `{player1_elo}`\n"
                f"**Record:** {p1_wins}W - {p1_losses}L\n"
                f"**Win Rate:** {p1_winrate}"
            ),
            inline=True
        )
        
        # VS field (middle)
        embed.add_field(
            name="⚔️",
            value="\u200b",
            inline=True
        )
        
        # Player 2 field
        embed.add_field(
            name=f"{player2.display_name}",
            value=(
                f"**ELO:** `{player2_elo}`\n"
                f"**Record:** {p2_wins}W - {p2_losses}L\n"
                f"**Win Rate:** {p2_winrate}"
            ),
            inline=True
        )
        
        # Seed field
        embed.add_field(
            name="Seed",
            value=f"```{initial_seed}```",
            inline=False
        )
        
        # Commands info
        embed.add_field(
            name="📋 Commands",
            value=(
                "`!result @winner` - Report the result\n"
                "`!change` - Request a new seed\n"
                "`!result draw` - Request a draw\n"
                "`!cancel` - Cancel the match"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Match started at")
        embed.timestamp = discord.utils.utcnow()
        
        # Send embed with mentions and recording warning
        await match_thread.send(
            content=f"{player1.mention} vs {player2.mention}\n\n⚠️ **WARNING: You MUST record your match!**",
            embed=embed
        )

        # Notify players via DM
        try:
            await player1.send(
                f"🎮 **Match Found!**\n"
                f"Opponent: {player2.mention}\n"
                f"Thread: {match_thread.mention}\n"
                f"Mode: {version} {mode_display}\n"
                f"Seed: \n `{initial_seed}`"
            )
        except:
            pass
        
        try:
            await player2.send(
                f"🎮 **Match Found!**\n"
                f"Opponent: {player1.mention}\n"
                f"Thread: {match_thread.mention}\n"
                f"Mode: {version} {mode_display}\n"
                f"Seed: \n `{initial_seed}`"
            )
        except:
            pass
        
        print(f"✅ Created match thread: {thread_name}")
        
    except Exception as e:
        print(f"❌ Error creating thread: {e}")
        await match_channel.send(f"❌ Error creating match thread! Match cancelled.")
        # Clean up
        active_challenges.pop(player1_id, None)
        active_challenges.pop(player2_id, None)
        return True
    
    return True

# === Status Command ===
@bot.command()
async def status(ctx):
    """Debug command to check active matches"""
    if not active_challenges:
        await ctx.send("No active matches currently.")
        return

    match_info = []
    processed_pairs = set()
    
    for user_id, challenge_state in active_challenges.items():
        opponent_id = challenge_state['opponent_id']
        pair_key = tuple(sorted([user_id, opponent_id]))
        
        if pair_key not in processed_pairs:
            try:
                user = await bot.fetch_user(user_id)
                opponent = await bot.fetch_user(opponent_id)
                version = challenge_state.get('version', 'Unknown')
                mode = challenge_state['mode'].replace('_', ' ').title()
                match_type = "RANKED" if challenge_state.get('ranked', False) else "Private"
                match_info.append(f"{user.name} vs {opponent.name} ({version} {mode} - {match_type})")
                processed_pairs.add(pair_key)
            except (discord.NotFound, discord.HTTPException):
                match_info.append(f"User {user_id} vs User {opponent_id}")
                processed_pairs.add(pair_key)

    await ctx.send(f"**Active matches:**\n" + "\n".join(match_info))

# === Seed Stats Command ===
@bot.command()
async def seedstats(ctx):
    """Show statistics about seed arrays"""
    def get_stats(arr, name):
        total = len(arr)
        unique = len(set(arr))
        duplicates = total - unique
        negative = sum(1 for seed in arr if seed.startswith('-'))
        positive = total - negative
        return f"**{name}:**\nTotal: {total} | Unique: {unique} | Duplicates: {duplicates}\nPositive: {positive} | Negative: {negative} | Neg%: {(negative/total*100):.1f}%\n"
    
    stats = "📊 **Seed Array Statistics**\n\n"
    stats += get_stats(codici_116, "1.16 Stronghold")
    stats += get_stats(rpcodici_116, "1.16 Ruined Portal")
    stats += get_stats(village_116, "1.16 Village") 
    stats += get_stats(bastion_118, "1.18+ Bastion")
    stats += get_stats(warped_118, "1.18+ Warped Forest")
    
    await ctx.send(stats)

# === Ranked Stats Command ===
@bot.command()
async def rankedstats(ctx):
    """Display overall ranked statistics"""
    if not stats_data:
        await ctx.send("📊 No ranked data available yet.")
        return
    
    total_matches = 0
    total_wins = 0
    total_losses = 0
    total_draws = 0
    total_forfeits = 0
    
    # Count by mode
    mode_stats = {
        "stronghold_116": 0,
        "ruined_portal_116": 0,
        "village_116": 0, 
        "bastion_118": 0,
        "warped_forest_118": 0
    }
    
    # Aggregate stats from all players
    for user_id, player_data in stats_data.items():
        total_matches += player_data["total_games"]
        total_wins += player_data["wins"]
        total_losses += player_data["losses"]
        total_draws += player_data["draws"]
        total_forfeits += player_data["forfeits"]
        
        # Count by mode
        for mode, mode_data in player_data["by_mode"].items():
            mode_total = mode_data["wins"] + mode_data["losses"] + mode_data["draws"]
            mode_stats[mode] += mode_total
    
    # Since each match involves 2 players, divide by 2
    actual_matches = total_matches // 2
    
    mode_display = {
            "stronghold_116": f"{CUSTOM_EMOJIS['stronghold']} Stronghold (1.16)",
            "ruined_portal_116": f"{CUSTOM_EMOJIS['ruined_portal']} Ruined Portal (1.16)",
            "village_116": f"{CUSTOM_EMOJIS['village']} Village (1.16)",
            "bastion_118": f"{CUSTOM_EMOJIS['bastion']} Bastion (1.18+)",
            "warped_forest_118": f"{CUSTOM_EMOJIS['warped']} Warped Forest (1.18+)"
        }
    
    stats_text = "📊 **OVERALL RANKED STATISTICS** 📊\n\n"
    stats_text += f"**Total Matches Played:** `{actual_matches}`\n"
    stats_text += f"**Total Players:** `{len(stats_data)}`\n"
    stats_text += f"**Total Forfeits:** `{total_forfeits}`\n\n"
    
    stats_text += "**Matches by Mode:**\n"
    for mode, display_name in mode_display.items():
        mode_count = mode_stats[mode] // 2  # Divide by 2 since each match has 2 players
        if mode_count > 0:
            percentage = (mode_count / actual_matches * 100) if actual_matches > 0 else 0
            stats_text += f"{display_name}: `{mode_count}` ({percentage:.1f}%)\n"
    
    await ctx.send(stats_text)

# === Reload Seeds Command ===
@bot.command()
async def reloadseeds(ctx):
    """Reload all seed files from disk"""
    global codici_116, rpcodici_116, bastion_118, warped_118
    
    codici_116 = load_seeds_from_file("stronghold_116.txt")
    rpcodici_116 = load_seeds_from_file("ruined_portal_116.txt")
    village_116 = load_seeds_from_file("village.txt")
    bastion_118 = load_seeds_from_file("bastion_118.txt")
    warped_118 = load_seeds_from_file("warped_forest_118.txt")
    
    await ctx.send(
        f"🔄 **Seeds reloaded!**\n"
        f"Stronghold (1.16): {len(codici_116)}\n"
        f"Ruined Portal (1.16): {len(rpcodici_116)}\n"
        f"Village (1.16): {len(village_116)}\n"
        f"Bastion (1.18+): {len(bastion_118)}\n"
        f"Warped Forest (1.18+): {len(warped_118)}"
    )

# === Set ELO Command (Admin only) ===
@bot.command()
@commands.has_permissions(administrator=True)
async def setelo(ctx, member: discord.Member, new_elo: int):
    """Set a player's ELO (Admin only)"""
    if new_elo < 0:
        await ctx.send("❌ ELO cannot be negative!")
        return
    
    old_elo = elo_data.get(str(member.id), 1000)
    elo_data[str(member.id)] = new_elo
    
    # Save to file
    with open("elo.json", "w") as f:
        json.dump(elo_data, f)
    
    # Update roles
    if ctx.guild:
        await update_user_roles(member, new_elo)
    
    await ctx.send(
        f"✅ **ELO Updated!**\n"
        f"{member.mention}: `{old_elo}` → `{new_elo}`\n"
        f"Change: `{new_elo - old_elo:+d}`"
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def resetdraws(ctx):
    """Reset all draw counts to 0 (Admin only)"""
    confirmation_msg = await ctx.send(
        "⚠️ **WARNING: This will reset ALL draw counts to 0!**\n"
        "This will affect:\n"
        "- Overall draw counts for all players\n"
        "- Draw counts in each game mode\n\n"
        "React with ✅ to confirm reset."
    )
    
    await confirmation_msg.add_reaction("✅")
    
    def check(reaction, user):
        return (user.id == ctx.author.id and 
                str(reaction.emoji) == "✅" and 
                reaction.message.id == confirmation_msg.id)
    
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        
        # Reset draws for all players
        reset_count = 0
        total_draws_reset = 0
        
        for user_id in stats_data:
            # Reset overall draws
            old_draws = stats_data[user_id].get("draws", 0)
            stats_data[user_id]["draws"] = 0
            total_draws_reset += old_draws
            
            # Reset draws in each mode
            for mode in stats_data[user_id]["by_mode"]:
                stats_data[user_id]["by_mode"][mode]["draws"] = 0
            
            reset_count += 1
        
        save_stats()
        
        await ctx.send(
            f"✅ **Draw counts reset!**\n"
            f"Reset draws for `{reset_count}` players.\n"
            f"Total draws cleared: `{total_draws_reset}`\n"
            f"All players now have 0 draws."
        )
        
    except asyncio.TimeoutError:
        await ctx.send("❌ Reset cancelled - timeout.")

@resetdraws.error
async def resetdraws_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need Administrator permissions to use this command!")

@bot.command()
@commands.has_permissions(administrator=True)
async def resetgamecounts(ctx):
    """Reset game counts for K-factor calculation (Admin only)"""
    confirmation_msg = await ctx.send(
        "⚠️ **WARNING: This will reset game counts for K-factor calculation!**\n"
        "This means ALL players will start with higher K-factors again (max 100).\n"
        "Their ELO ratings and total game stats will NOT be affected.\n\n"
        "React with ✅ to confirm reset."
    )
    
    await confirmation_msg.add_reaction("✅")
    
    def check(reaction, user):
        return (user.id == ctx.author.id and 
                str(reaction.emoji) == "✅" and 
                reaction.message.id == confirmation_msg.id)
    
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        
        # Reset games_since_reset for all players
        reset_count = 0
        for user_id in stats_data:
            stats_data[user_id]["games_since_reset"] = 0
            reset_count += 1
        
        save_stats()
        
        await ctx.send(
            f"✅ **Game counts reset!**\n"
            f"Reset K-factor calculation for `{reset_count}` players.\n"
            f"All players will now have higher K-factors (up to 100) until they play 40 games.\n"
            f"**This will increase ELO spread going forward.**"
        )
        
    except asyncio.TimeoutError:
        await ctx.send("❌ Reset cancelled - timeout.")

@resetgamecounts.error
async def resetgamecounts_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need Administrator permissions to use this command!")

@bot.command()
async def kfactor(ctx, member: Optional[discord.Member] = None):
    """Check your current K-factor"""
    if member is None:
        member = ctx.author
    
    user_id = str(member.id)
    init_player_stats(member.id)
    
    user_stats = stats_data.get(user_id)
    games_since_reset = user_stats.get("games_since_reset", 0)
    total_games = user_stats.get("total_games", 0)
    
    k = max(20, 100 - 2 * games_since_reset) 
    
    await ctx.send(
        f"📊 **K-Factor for {member.display_name}**\n"
        f"Current K-Factor: `{k}`\n"
        f"Games since reset: `{games_since_reset}`\n"
        f"Total games (all time): `{total_games}`\n\n"
        f"*K-Factor decreases by 2 per game, minimum 40*\n" 
        f"*Games until minimum K: `{max(0, (k - 20) // 2) - 10}`*"  
    )

@setelo.error
async def setelo_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need Administrator permissions to use this command!")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found!")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid ELO value! Usage: `!setelo @user <number>`")
    else:
        await ctx.send(f"❌ Error: {error}")

# === Help Command ===
@bot.command()
async def help(ctx):
    """Display all available commands"""
    help_text = f"""
📋 **Bot Commands**

**Match Commands:**
`!queue` - Join/leave matchmaking queue (#queue)
`!solo` - Solo practice (choose version & mode, no ELO)
`!private @user` - Private match (choose version & mode, no ELO)
`!result @winner MM:SS` - Report match result with time
`!result draw` - Requests a draw
`!change` - Get a new seed during active match
`!cancel` - Request to cancel current match
`!forfeit` - Forfeit your ranked match (gives opponent the win)

**ELO & Stats Commands:**
`!elo [@user]` - Check ELO rating
`!ranking [@user]` - View your rank position
`!stats [@user]` - View detailed player statistics with charts
`!compare @player` - Compare stats & head-to-head vs another player
`!rankedstats` - View overall ranked match statistics
`!leaderboard` - View top 10 players
`!kfactor [@user]` - Check current K-factor

**Utility Commands:**
`!mobile MM:SS` - Calculate mobile time (-12%)
`!status` - View active matches
`!seedstats` - View seed statistics
`!reloadseeds` - Reload seed files

**Info:**
{CUSTOM_EMOJIS['116']} 1.16 versions: Stronghold, Ruined Portal & Village
{CUSTOM_EMOJIS['118']} 1.18+ versions: Bastion & Warped Forest
⏱️ Ranked matches require completion time (e.g., !result @player 6:45)
✅ React to role message to get verified role
🎯 Roles automatically update based on your ELO!
"""
    await ctx.send(help_text)

# Token
token = "xxx"

while True:
    try:
        print("🔄 Starting bot...")
        bot.run(token)
    except (discord.ConnectionClosed, discord.HTTPException) as e:
        print(f"⚠️ Bot disconnected: {e}. Retrying in 5 seconds...")
        time.sleep(5)
        continue
    except Exception as e:
        print(f"💀 Fatal error: {e}")
        
