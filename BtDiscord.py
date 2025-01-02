import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

meetings = {}



async def check_meetings():
    print('Checking')
    now = datetime.now(timezone.utc)
    for meeting_id, meeting in meetings.items():
        meeting_time = meeting["datetime"]
        if now >= meeting_time:
            channel = bot.get_channel(meeting["channel_id"])
            if channel:
                user_mentions = ", ".join([f"<@{userid}>" for userid in meeting["users"]])
                message = f"Reminder: Meeting '{meeting['subject']}' is happening now! \n Users: {user_mentions} \n"
                await channel.send(message)
                meetings.pop(meeting_id)



async def periodic_check():
    while True:
        await check_meetings()
        await asyncio.sleep(20)
        


@bot.event
async def on_ready():
    print(f"Hello, I'm logged in as {bot.user}, use !help for more information.")
    bot.loop.create_task(periodic_check())
@bot.command()
async def set(ctx, Subject: str, datetime_str: str, channel_name: str, *users: discord.User):
    try:
        meeting_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        meeting_datetime = meeting_datetime.replace(tzinfo=timezone.utc)
    except ValueError:
        await ctx.send("Invalid datetime format. Please use YYYY-MM-DD HH:MM.")
        return

    channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
    if not channel:
        await ctx.send(f"Channel `{channel_name}` not found.")
        return

    meeting_id = len(meetings) + 1
    meetings[meeting_id] = {
        "ID": meeting_id,
        "subject": Subject,
        "datetime": meeting_datetime,
        "users": [user.id for user in users],
        "channel_id": channel.id
    }

    user_mentions = " ".join([user.mention for user in users])
    await ctx.send(f"Meeting about ***{Subject}*** set for **{meeting_datetime} UTC** in {channel.mention} with {user_mentions}.")



@bot.command()
async def list(ctx):
    if not meetings:
        await ctx.send("No Meetings Scheduled, Stay tuned.")
    else:
        author_id = ctx.author.id
        message = "Upcoming Meetings: \n"

        for meeting_id, meeting in meetings.items():
            if author_id in meeting["users"]:
                user_mentions = ", ".join([f"<@{userid}>" for userid in meeting["users"]])
                message += f"ID: {meeting['ID']} \n Subject: ***{meeting['subject']}*** \n Channel: <#{meeting['channel_id']}> \n Users: {user_mentions} \n"

        if message == "Upcoming Meetings: \n":
            await ctx.send("No Meetings Scheduled for you, Stay tuned.")
        else:
            await ctx.send(message)

@bot.command()
async def delete(ctx, ID: int):
    if ID in meetings:
        del_meeting = meetings.pop(ID)
        await ctx.send(f"Meeting ***{del_meeting['subject']}*** deleted.")
    else:
        await ctx.send("Meeting ID not found.")

@bot.command()
async def help(ctx):
    await ctx.send("Available commands: \n!set [Subject] [datetime] [channel] [@user1] [@user2]... - Set a meeting \n!list - List all meetings \n!del [Meeting ID] - Delete a meeting \n !help - Show this message")


load_dotenv()
my_token = os.getenv('BOT_TOKEN')
bot.run(my_token)
