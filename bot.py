import discord
from discord.ext import commands
import asyncio 
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

#testing to see if bot is logged
@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

#testing to see if bot is responding to simple commands
@client.command()
async def hello(ctx):
    await ctx.send('Hello!')

@client.command()
async def ping(ctx):
    await ctx.send('pong!')

#schedule a meeting with title, date, time and role(optional)
@client.command()
async def schedule(ctx, title: str, date: str, time: str, role: discord.Role = None):
    
    try:
        try:
            #converting the combined datetime string into a datetime object for easy manipulation
            date_time_str = f"{date} {time}"
            
            meeting_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")

        except ValueError:
            await ctx.send("Error: The date and time format is incorrect. Please use the format 'YYYY-MM-DD' 'HH:MM'.")
            return
        
        #check if the date is in the future
        if meeting_time < datetime.now():
            await ctx.send("Invalid: The scheduled time must be in the future.")
            return
        
        #calculate the time left until the meeting
        time_till_meeting = meeting_time - datetime.now()

         #calculate the time for the reminder 10 minutes before the meeting
        reminder_time_10 = meeting_time - time_till_meeting(minutes=10)
        
        #calculate the time left until the reminder
        reminder_time = reminder_time_10 - datetime.now()

        #send confirmation message in the channel where the command was used
        await ctx.send(f"Meeting '{title}' is scheduled for {date} at {time}. I will remind you!")

        if reminder_time.total_seconds() > 0:
            await asyncio.sleep(reminder_time.total_seconds())
            if role:
                await ctx.send(f"Reminder: {title} is starting in 10 minutes! {role.mention}")
            else:
                await ctx.send(f"Reminder: {title} is starting in 10 minutes!")
        
        #wait for the specified time and then send a reminder
        await asyncio.sleep(time_till_meeting.total_seconds())

        #check if there is a role in the command to send a mention or not
        if role:
            await ctx.send(f"Reminder: {title} is starting now! {role.mention}")
        else:
            await ctx.send(f"Reminder: {title} is starting now!")

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")