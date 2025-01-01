import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# In-memory storage for meetings
meetings = {}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(name='create_meeting')
async def create_meeting(ctx, title: str, time: str):
    """Create a meeting with a title and time."""
    if title in meetings:
        await ctx.send(f'Meeting "{title}" already exists.')
    else:
        meetings[title] = time
        await ctx.send(f'Meeting "{title}" scheduled for {time}.')

@bot.command(name='edit_meeting')
async def edit_meeting(ctx, title: str, new_time: str):
    """Edit the time of an existing meeting."""
    if title in meetings:
        meetings[title] = new_time
        await ctx.send(f'Meeting "{title}" has been rescheduled to {new_time}.')
    else:
        await ctx.send(f'Meeting "{title}" does not exist.')

@bot.command(name='list_meetings')
async def list_meetings(ctx):
    """List all scheduled meetings."""
    if not meetings:
        await ctx.send('No meetings scheduled.')
    else:
        meeting_list = '\n'.join([f'{title}: {time}' for title, time in meetings.items()])
        await ctx.send(f'Scheduled Meetings:\n{meeting_list}')

@bot.command(name='delete_meeting')
async def delete_meeting(ctx, title: str):
    """Delete a scheduled meeting."""
    if title in meetings:
        del meetings[title]
        await ctx.send(f'Meeting "{title}" has been deleted.')
    else:
        await ctx.send(f'Meeting "{title}" does not exist.')

@bot.command(name='help')
async def help_command(ctx):
    """Show available commands."""
    help_text = (
        "!create_meeting <title> <time> - Schedule a new meeting\n"
        "!edit_meeting <title> <new_time> - Reschedule an existing meeting\n"
        "!list_meetings - List all scheduled meetings\n"
        "!delete_meeting <title> - Delete a scheduled meeting\n"
        "!help - Show this help message"
    )
    await ctx.send(help_text)

bot.run(TOKEN)
