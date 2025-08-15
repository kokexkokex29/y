#!/usr/bin/env python3
"""
Discord Football Club Management Bot
Comprehensive bot with 15+ slash commands for managing football clubs
"""

import discord
from discord.ext import commands, tasks
import asyncio
import os
import logging
import json
from datetime import datetime, timedelta
from database import Database
import aiohttp
from typing import Optional
import time

# Configure logging
logger = logging.getLogger(__name__)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

class FootballBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        self.db = Database()
        self.rate_limit_delay = 1.0  # Base delay between API calls
        self.max_retries = 3
        self.last_request_time = 0
        
    async def setup_hook(self):
        """Setup hook called when bot is ready"""
        logger.info("Bot setup hook called")
        await self.tree.sync()
        logger.info("Commands synced")
        
        # Start background tasks
        if not self.match_reminder.is_running():
            self.match_reminder.start()
        
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Football Clubs ⚽"
        )
        await self.change_presence(activity=activity)
        
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("❌ You don't have permission to use this command!", ephemeral=True)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.respond(f"⏰ Command on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
        else:
            logger.error(f"Command error: {error}")
            await ctx.respond("❌ An error occurred while processing your command.", ephemeral=True)
    
    async def rate_limit_handler(self):
        """Handle rate limiting to prevent 429 errors"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        
        self.last_request_time = time.time()
    
    @tasks.loop(minutes=1)
    async def match_reminder(self):
        """Check for upcoming matches and send reminders"""
        try:
            upcoming_matches = self.db.get_upcoming_matches()
            current_time = datetime.now()
            
            for match in upcoming_matches:
                match_time = datetime.strptime(match['datetime'], '%Y-%m-%d %H:%M')
                time_diff = (match_time - current_time).total_seconds() / 60
                
                # Send reminder 5 minutes before match
                if 4 <= time_diff <= 6 and not match['reminder_sent']:
                    await self.send_match_reminder(match)
                    self.db.mark_reminder_sent(match['id'])
                    
        except Exception as e:
            logger.error(f"Error in match reminder task: {e}")
    
    async def send_match_reminder(self, match):
        """Send match reminder to teams"""
        try:
            guild = self.get_guild(match['guild_id'])
            if not guild:
                return
                
            team1 = guild.get_role(match['team1_id'])
            team2 = guild.get_role(match['team2_id'])
            
            if team1 and team2:
                embed = discord.Embed(
                    title="⚽ Match Reminder",
                    description=f"Your match starts in 5 minutes!",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                embed.add_field(
                    name="Teams",
                    value=f"{team1.name} vs {team2.name}",
                    inline=False
                )
                embed.add_field(
                    name="Time",
                    value=f"<t:{int(datetime.strptime(match['datetime'], '%Y-%m-%d %H:%M').timestamp())}:F>",
                    inline=False
                )
                
                # Send to team members via DM
                for member in team1.members:
                    try:
                        await member.send(embed=embed)
                    except:
                        pass  # User has DMs disabled
                        
                for member in team2.members:
                    try:
                        await member.send(embed=embed)
                    except:
                        pass  # User has DMs disabled
                        
        except Exception as e:
            logger.error(f"Error sending match reminder: {e}")

# Initialize bot
bot = FootballBot()

def is_admin():
    """Check if user has administrator permissions"""
    async def predicate(interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
            return False
        
        member = interaction.guild.get_member(interaction.user.id)
        if not member or not member.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only administrators can use this command!", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate)

# Club Management Commands

@bot.tree.command(name="create_club", description="Create a new football club")
@discord.app_commands.describe(
    name="The name of the club",
    budget="The club's budget in Euros"
)
@is_admin()
async def create_club(interaction: discord.Interaction, name: str, budget: float):
    """Create a new football club"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        success = bot.db.create_club(interaction.guild.id, name, budget)
        if success:
            embed = discord.Embed(
                title="✅ Club Created",
                description=f"**{name}** has been created successfully!",
                color=discord.Color.green()
            )
            embed.add_field(name="Budget", value=f"€{budget:,.2f}", inline=True)
            embed.set_footer(text=f"Created by {interaction.user.display_name}")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Club already exists!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error creating club: {e}")
        await interaction.response.send_message("❌ An error occurred while creating the club.", ephemeral=True)

@bot.tree.command(name="delete_club", description="Delete a football club")
@discord.app_commands.describe(name="The name of the club to delete")
@is_admin()
async def delete_club(interaction: discord.Interaction, name: str):
    """Delete a football club"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        success = bot.db.delete_club(interaction.guild.id, name)
        if success:
            embed = discord.Embed(
                title="✅ Club Deleted",
                description=f"**{name}** has been deleted successfully!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Club not found!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error deleting club: {e}")
        await interaction.response.send_message("❌ An error occurred while deleting the club.", ephemeral=True)

@bot.tree.command(name="list_clubs", description="List all football clubs")
async def list_clubs(interaction: discord.Interaction):
    """List all football clubs"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        clubs = bot.db.get_clubs(interaction.guild.id)
        
        if not clubs:
            await interaction.response.send_message("📋 No clubs found in this server.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="⚽ Football Clubs",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for club in clubs[:10]:  # Limit to 10 clubs
            player_count = bot.db.get_player_count(club['id'])
            embed.add_field(
                name=f"🏆 {club['name']}",
                value=f"💰 Budget: €{club['budget']:,.2f}\n👥 Players: {player_count}",
                inline=True
            )
            
        embed.set_footer(text=f"Total Clubs: {len(clubs)}")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error listing clubs: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching clubs.", ephemeral=True)

@bot.tree.command(name="update_club_budget", description="Update a club's budget")
@discord.app_commands.describe(
    name="The name of the club",
    budget="The new budget in Euros"
)
@is_admin()
async def update_club_budget(interaction: discord.Interaction, name: str, budget: float):
    """Update a club's budget"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        success = bot.db.update_club_budget(interaction.guild.id, name, budget)
        if success:
            embed = discord.Embed(
                title="✅ Budget Updated",
                description=f"**{name}**'s budget has been updated!",
                color=discord.Color.green()
            )
            embed.add_field(name="New Budget", value=f"€{budget:,.2f}", inline=True)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Club not found!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error updating club budget: {e}")
        await interaction.response.send_message("❌ An error occurred while updating the budget.", ephemeral=True)

# Player Management Commands

@bot.tree.command(name="add_player", description="Add a player to a club")
@discord.app_commands.describe(
    name="The player's name",
    club="The club name",
    value="The player's value in Euros",
    position="The player's position",
    age="The player's age"
)
@is_admin()
async def add_player(interaction: discord.Interaction, name: str, club: str, value: float, position: str = "Forward", age: int = 25):
    """Add a player to a club"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        success = bot.db.add_player(interaction.guild.id, name, club, value, position, age)
        if success:
            embed = discord.Embed(
                title="✅ Player Added",
                description=f"**{name}** has been added to **{club}**!",
                color=discord.Color.green()
            )
            embed.add_field(name="Value", value=f"€{value:,.2f}", inline=True)
            embed.add_field(name="Position", value=position, inline=True)
            embed.add_field(name="Age", value=f"{age} years", inline=True)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Club not found or player already exists!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error adding player: {e}")
        await interaction.response.send_message("❌ An error occurred while adding the player.", ephemeral=True)

@bot.tree.command(name="remove_player", description="Remove a player from their club")
@discord.app_commands.describe(name="The player's name")
@is_admin()
async def remove_player(interaction: discord.Interaction, name: str):
    """Remove a player from their club"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        success = bot.db.remove_player(interaction.guild.id, name)
        if success:
            embed = discord.Embed(
                title="✅ Player Removed",
                description=f"**{name}** has been removed!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Player not found!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error removing player: {e}")
        await interaction.response.send_message("❌ An error occurred while removing the player.", ephemeral=True)

@bot.tree.command(name="update_player_value", description="Update a player's value")
@discord.app_commands.describe(
    name="The player's name",
    value="The new value in Euros"
)
@is_admin()
async def update_player_value(interaction: discord.Interaction, name: str, value: float):
    """Update a player's value"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        success = bot.db.update_player_value(interaction.guild.id, name, value)
        if success:
            embed = discord.Embed(
                title="✅ Player Value Updated",
                description=f"**{name}**'s value has been updated!",
                color=discord.Color.green()
            )
            embed.add_field(name="New Value", value=f"€{value:,.2f}", inline=True)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Player not found!", ephemeral=True)
    except Exception as e:
        logger.error(f"Error updating player value: {e}")
        await interaction.response.send_message("❌ An error occurred while updating the player value.", ephemeral=True)

@bot.tree.command(name="transfer_player", description="Transfer a player between clubs")
@discord.app_commands.describe(
    player="The player's name",
    from_club="The current club",
    to_club="The destination club",
    transfer_fee="The transfer fee in Euros"
)
@is_admin()
async def transfer_player(interaction: discord.Interaction, player: str, from_club: str, to_club: str, transfer_fee: float):
    """Transfer a player between clubs"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        success = bot.db.transfer_player(interaction.guild.id, player, from_club, to_club, transfer_fee)
        if success:
            embed = discord.Embed(
                title="✅ Transfer Complete",
                description=f"**{player}** has been transferred!",
                color=discord.Color.gold()
            )
            embed.add_field(name="From", value=from_club, inline=True)
            embed.add_field(name="To", value=to_club, inline=True)
            embed.add_field(name="Transfer Fee", value=f"€{transfer_fee:,.2f}", inline=True)
            
            # Log transfer
            bot.db.log_transfer(interaction.guild.id, player, from_club, to_club, transfer_fee, interaction.user.id)
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Transfer failed! Check if clubs exist and have sufficient budget.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error transferring player: {e}")
        await interaction.response.send_message("❌ An error occurred during the transfer.", ephemeral=True)

@bot.tree.command(name="list_players", description="List players in a club")
@discord.app_commands.describe(club="The club name (optional)")
async def list_players(interaction: discord.Interaction, club: str = ""):
    """List players in a club or all players"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        if club and club.strip():
            players = bot.db.get_club_players(interaction.guild.id, club)
            title = f"⚽ {club} Players"
        else:
            players = bot.db.get_all_players(interaction.guild.id)
            title = "⚽ All Players"
            
        if not players:
            await interaction.response.send_message("📋 No players found.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for player in players[:15]:  # Limit to 15 players
            club_name = player.get('club_name', 'Free Agent')
            embed.add_field(
                name=f"👤 {player['name']}",
                value=f"🏆 {club_name}\n💰 €{player['value']:,.2f}\n⚽ {player['position']}\n🎂 {player['age']} years",
                inline=True
            )
            
        embed.set_footer(text=f"Total Players: {len(players)}")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error listing players: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching players.", ephemeral=True)

# Match Management Commands

@bot.tree.command(name="create_match", description="Create a match between two teams")
@discord.app_commands.describe(
    team1="First team role",
    team2="Second team role",
    date="Match date (YYYY-MM-DD)",
    time="Match time (HH:MM)",
    description="Match description"
)
@is_admin()
async def create_match(interaction: discord.Interaction, team1: discord.Role, team2: discord.Role, date: str, time: str, description: str = "League Match"):
    """Create a match between two teams"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        match_datetime = f"{date} {time}"
        datetime.strptime(match_datetime, '%Y-%m-%d %H:%M')  # Validate format
        
        match_id = bot.db.create_match(
            interaction.guild.id,
            team1.id,
            team2.id,
            match_datetime,
            description
        )
        
        if match_id:
            embed = discord.Embed(
                title="⚽ Match Created",
                description=description,
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Teams", value=f"{team1.mention} vs {team2.mention}", inline=False)
            embed.add_field(name="Date & Time", value=f"<t:{int(datetime.strptime(match_datetime, '%Y-%m-%d %H:%M').timestamp())}:F>", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            # Send DM notifications to team members
            notification_embed = discord.Embed(
                title="📅 New Match Scheduled",
                description=f"You have a match scheduled!",
                color=discord.Color.blue()
            )
            
            # Check if user is member and has roles
            member = interaction.guild.get_member(interaction.user.id)
            opponent = team2.name if member and team1 in member.roles else team1.name
            notification_embed.add_field(name="Opponent", value=opponent, inline=False)
            notification_embed.add_field(name="Date & Time", value=f"<t:{int(datetime.strptime(match_datetime, '%Y-%m-%d %H:%M').timestamp())}:F>", inline=False)
            
            for member in team1.members + team2.members:
                try:
                    await member.send(embed=notification_embed)
                except:
                    pass  # User has DMs disabled
                    
        else:
            await interaction.response.send_message("❌ Failed to create match!", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("❌ Invalid date/time format! Use YYYY-MM-DD for date and HH:MM for time.", ephemeral=True)
    except Exception as e:
        logger.error(f"Error creating match: {e}")
        await interaction.response.send_message("❌ An error occurred while creating the match.", ephemeral=True)

@bot.tree.command(name="list_matches", description="List upcoming matches")
async def list_matches(interaction: discord.Interaction):
    """List upcoming matches"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        matches = bot.db.get_upcoming_matches(interaction.guild.id)
        
        if not matches:
            await interaction.response.send_message("📋 No upcoming matches found.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="📅 Upcoming Matches",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for match in matches[:10]:  # Limit to 10 matches
            team1 = interaction.guild.get_role(match['team1_id'])
            team2 = interaction.guild.get_role(match['team2_id'])
            
            if team1 and team2:
                match_time = datetime.strptime(match['datetime'], '%Y-%m-%d %H:%M')
                embed.add_field(
                    name=f"⚽ {match['description']}",
                    value=f"{team1.mention} vs {team2.mention}\n<t:{int(match_time.timestamp())}:F>",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error listing matches: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching matches.", ephemeral=True)

# Statistics Commands

@bot.tree.command(name="club_stats", description="Show detailed club statistics")
@discord.app_commands.describe(name="The club name")
async def club_stats(interaction: discord.Interaction, name: str):
    """Show detailed club statistics"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        club_data = bot.db.get_club_stats(interaction.guild.id, name)
        
        if not club_data:
            await interaction.response.send_message("❌ Club not found!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title=f"📊 {name} Statistics",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="💰 Budget", value=f"€{club_data['budget']:,.2f}", inline=True)
        embed.add_field(name="👥 Players", value=str(club_data['player_count']), inline=True)
        embed.add_field(name="💎 Total Value", value=f"€{club_data['total_value']:,.2f}", inline=True)
        embed.add_field(name="📈 Average Value", value=f"€{club_data['avg_value']:,.2f}", inline=True)
        embed.add_field(name="🔝 Most Valuable", value=f"{club_data['most_valuable']} (€{club_data['highest_value']:,.2f})", inline=True)
        embed.add_field(name="🔄 Transfers", value=f"In: {club_data['transfers_in']} | Out: {club_data['transfers_out']}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error getting club stats: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching club statistics.", ephemeral=True)

@bot.tree.command(name="top_players", description="Show top players by value")
async def top_players(interaction: discord.Interaction):
    """Show top players by value"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        players = bot.db.get_top_players(interaction.guild.id, limit=10)
        
        if not players:
            await interaction.response.send_message("📋 No players found.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="🏆 Top Players by Value",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        for i, player in enumerate(players, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            embed.add_field(
                name=f"{medal} {player['name']}",
                value=f"🏆 {player['club_name']}\n💰 €{player['value']:,.2f}\n⚽ {player['position']}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error getting top players: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching top players.", ephemeral=True)

@bot.tree.command(name="richest_clubs", description="Show clubs with highest budgets")
async def richest_clubs(interaction: discord.Interaction):
    """Show clubs with highest budgets"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        clubs = bot.db.get_richest_clubs(interaction.guild.id, limit=10)
        
        if not clubs:
            await interaction.response.send_message("📋 No clubs found.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="💰 Richest Clubs",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        for i, club in enumerate(clubs, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            embed.add_field(
                name=f"{medal} {club['name']}",
                value=f"💰 €{club['budget']:,.2f}\n👥 {club['player_count']} players",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error getting richest clubs: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching richest clubs.", ephemeral=True)

@bot.tree.command(name="transfer_history", description="Show recent transfer history")
async def transfer_history(interaction: discord.Interaction):
    """Show recent transfer history"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        transfers = bot.db.get_transfer_history(interaction.guild.id, limit=10)
        
        if not transfers:
            await interaction.response.send_message("📋 No transfers found.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="🔄 Recent Transfers",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for transfer in transfers:
            transfer_date = datetime.strptime(transfer['date'], '%Y-%m-%d %H:%M:%S')
            embed.add_field(
                name=f"👤 {transfer['player_name']}",
                value=f"📤 {transfer['from_club']} ➡️ {transfer['to_club']}\n💰 €{transfer['fee']:,.2f}\n📅 <t:{int(transfer_date.timestamp())}:R>",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error getting transfer history: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching transfer history.", ephemeral=True)

# Utility Commands

@bot.tree.command(name="reset_data", description="Reset all bot data (USE WITH CAUTION)")
@is_admin()
async def reset_data(interaction: discord.Interaction):
    """Reset all bot data"""
    await bot.rate_limit_handler()
    
    # Confirmation embed
    embed = discord.Embed(
        title="⚠️ DANGER: Reset All Data",
        description="This will permanently delete ALL clubs, players, matches, and transfer history!\n\n**This action cannot be undone!**",
        color=discord.Color.red()
    )
    
    # Create confirmation view
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            
        @discord.ui.button(label="CONFIRM RESET", style=discord.ButtonStyle.danger)
        async def confirm_reset(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user != interaction.user:
                await button_interaction.response.send_message("❌ Only the command user can confirm this action!", ephemeral=True)
                return
                
            if not interaction.guild:
                await button_interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
                return
                
            try:
                bot.db.reset_all_data(interaction.guild.id)
                
                success_embed = discord.Embed(
                    title="✅ Data Reset Complete",
                    description="All bot data has been permanently deleted.",
                    color=discord.Color.green()
                )
                await button_interaction.response.edit_message(embed=success_embed, view=None)
            except Exception as e:
                logger.error(f"Error resetting data: {e}")
                await button_interaction.response.send_message("❌ An error occurred while resetting data.", ephemeral=True)
                
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel_reset(self, button_interaction: discord.Interaction, button: discord.ui.Button):
            if button_interaction.user != interaction.user:
                await button_interaction.response.send_message("❌ Only the command user can cancel this action!", ephemeral=True)
                return
                
            cancel_embed = discord.Embed(
                title="✅ Reset Cancelled",
                description="Data reset has been cancelled. Your data is safe.",
                color=discord.Color.green()
            )
            await button_interaction.response.edit_message(embed=cancel_embed, view=None)
    
    view = ConfirmView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="bot_info", description="Show bot information and statistics")
async def bot_info(interaction: discord.Interaction):
    """Show bot information and statistics"""
    await bot.rate_limit_handler()
    
    if not interaction.guild:
        await interaction.response.send_message("❌ This command can only be used in servers!", ephemeral=True)
        return
    
    try:
        stats = bot.db.get_server_stats(interaction.guild.id)
        
        embed = discord.Embed(
            title="🤖 Football Club Bot Info",
            description="Comprehensive football club management system",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="🏆 Total Clubs", value=str(stats['total_clubs']), inline=True)
        embed.add_field(name="👥 Total Players", value=str(stats['total_players']), inline=True)
        embed.add_field(name="📅 Upcoming Matches", value=str(stats['upcoming_matches']), inline=True)
        embed.add_field(name="🔄 Total Transfers", value=str(stats['total_transfers']), inline=True)
        embed.add_field(name="💰 Total Market Value", value=f"€{stats['total_value']:,.2f}", inline=True)
        embed.add_field(name="🌐 Servers", value=str(len(bot.guilds)), inline=True)
        
        embed.set_footer(text="Created with ❤️ for football management")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error getting bot info: {e}")
        await interaction.response.send_message("❌ An error occurred while fetching bot information.", ephemeral=True)

# Image Upload Command
@bot.tree.command(name="upload_image", description="Upload an image with embed")
@discord.app_commands.describe(
    title="Embed title",
    description="Embed description",
    attachment="Image file to upload"
)
@is_admin()
async def upload_image(interaction: discord.Interaction, title: str, description: str, attachment: discord.Attachment):
    """Upload an image with custom embed"""
    await bot.rate_limit_handler()
    
    try:
        if not attachment.content_type or not attachment.content_type.startswith('image/'):
            await interaction.response.send_message("❌ Please upload a valid image file!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_image(url=attachment.url)
        embed.set_footer(text=f"Uploaded by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        await interaction.response.send_message("❌ An error occurred while uploading the image.", ephemeral=True)

async def start_bot():
    """Start the Discord bot with proper error handling"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error("DISCORD_TOKEN not found in environment variables")
        return
        
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token")
    except discord.HTTPException as e:
        if e.status == 429:
            logger.warning(f"Rate limited: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying
            await start_bot()
        else:
            logger.error(f"HTTP error: {e}")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        await asyncio.sleep(30)  # Wait 30 seconds before retrying
        await start_bot()
