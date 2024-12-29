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
