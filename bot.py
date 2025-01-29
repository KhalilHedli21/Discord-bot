from discord.ext import commands, tasks
import discord
from datetime import datetime, timedelta
import sqlite3
import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import re


intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

#setting up the db
connection = sqlite3.connect('DBNAME') #enter your database name here (to test)
cursor = connection.cursor()
#create schedule table to save meetings and their info
cursor.execute('''CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    role TEXT,
    reminder_sent BOOLEAN DEFAULT FALSE
)''')

#function to add a schedule to the database
def add_schedule_to_db(title, date, time, role):
    cursor.execute('''INSERT INTO schedule (title, date, time, role) VALUES (?, ?, ?, ?)''',
                   (title, date, time, role))
    connection.commit()

#function to retrieve the role from the server so we can mention directly
def get_role_by_name(guild, role_name):
    return discord.utils.get(guild.roles, name=role_name)
#delete a schedule from the database
def delete_schedule(meeting_id):
    cursor.execute("DELETE FROM schedule WHERE id = ?", (meeting_id,))
    connection.commit()

#command to delete a schedule
@client.command()
async def delete(ctx, meeting_id: int):
    """deletes a schedule with the given meeting ID.\n syntax: !delete meeting_id"""
    
    cursor.execute("SELECT * FROM schedule WHERE id = ?", (meeting_id,))
    schedule = cursor.fetchone()
    if not schedule:
        await ctx.send("No meeting found with that ID.")
        return

    delete_schedule(meeting_id)
    await ctx.send(f"Meeting with ID {meeting_id} has been deleted.")

#schedule command to set up meetings
@client.command()
async def schedule(ctx, title: str, *args):
    """Schedules a new meeting with a title, absolute date/time, or relative time and a role (optional).\n
    Syntax 1: !schedule "title" "yyyy-mm-dd" "H:M" @role\n
    Syntax 2: !schedule "title" in X minutes/hours/days/weeks @role"""
    try:
        #retrieve the role if it is mentioned
        role = None
        if args and args[-1].startswith("<@&"):  #check if last argument is a role mention
            role = discord.utils.get(ctx.guild.roles, id=int(args[-1][3:-1]))  #get role id
            time_input = args[:-1]  #delete role from args
        else:
            time_input = args  #no role

        time_str = " ".join(time_input)

        #check if format is absolute or relative
        try:
            meeting_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            match = re.match(r"in (\d+) (minute|hour|day|week)s?", time_str)
            if match:
                value, unit = int(match.group(1)), match.group(2)
                if unit == "minute":
                    meeting_time = datetime.now() + timedelta(minutes=value)
                elif unit == "hour":
                    meeting_time = datetime.now() + timedelta(hours=value)
                elif unit == "day":
                    meeting_time = datetime.now() + timedelta(days=value)
                elif unit == "week":
                    meeting_time = datetime.now() + timedelta(weeks=value)
                else:
                    raise ValueError("Unsupported time unit.")
            else:
                raise ValueError("Invalid time format. Use 'YYYY-MM-DD H:M' or 'in X hours/days'.")

        #ensure the meeting is scheduled in the future
        if meeting_time < datetime.now():
            await ctx.send("Invalid: The scheduled time must be in the future.")
            return

        #save the meeting to the database
        add_schedule_to_db(title, meeting_time.strftime("%Y-%m-%d"), meeting_time.strftime("%H:%M"), role.name if role else None)

        #confirmation message
        await ctx.send(f"'{title}' is scheduled for {meeting_time.strftime('%Y-%m-%d %H:%M')}. I will remind you! {role.mention if role else ''}")

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")


#command to list all schedules and their info in a table
@client.command()
async def list(ctx):
    """displays your schedule details in a table format!\n syntax: !list """
    #retrieve schedules from the db
    cursor.execute("SELECT * FROM schedule")
    schedules = cursor.fetchall()

    #check if there are any schedules in the db
    if not schedules:
        await ctx.send("No scheduled meetings found.")
        return

    
    #draw the header part of tab
    table =  "┌────────┬────────────┬────────────┬───────┬────────────┐\n"
    table += "│   ID   │   Title    │    Date    │ Time  │    Role    │\n"
    table += "├────────┼────────────┼────────────┼───────┼────────────┤\n"
    
    #add rows
    for schedule in schedules:
        table += "│ {0:<6} │ {1:<10} │ {2:<8} │ {3:<5} │ {4:<10} │\n".format(schedule[0], schedule[1], schedule[2], schedule[3], schedule[4] or "None")
    
    #add bottom border
    table += "└────────┴────────────┴────────────┴───────┴────────────┘"


    await ctx.send("Here are your upcoming meetings:")
    #discord has a 2000 car limit so if it exceeds we split it 
    max_message_length = 2000
    while len(table) > max_message_length:
        await ctx.send(f"```{table[:max_message_length]}```")
        table = table[max_message_length:]

    #send the rest of the table if it exceeds the limit

    await ctx.send(f"```{table}```")


#command to export the schedules as csv or pdf files
@client.command()
async def export(ctx, format: str):
    """can turn your schedule into a csv or pdf !\n syntax: !export format_name"""
    #validate the format parameter
    if format not in ["csv", "pdf"]:
        await ctx.send("Invalid format! Please use 'csv' or 'pdf'.")
        return
    
    #fetch the schedule data from the database
    cursor.execute("SELECT * FROM schedule")
    schedules = cursor.fetchall()

    #if format=csv
    if format == "csv":
        #create a file-like object to write CSV data
        csv_file = io.StringIO()
        csv_writer = csv.writer(csv_file)

        #write headers 
        csv_writer.writerow(["Meeting_ID", "Title", "Date", "Time", "Role"])

        #write the data
        for schedule in schedules:
            
            meeting_id, title, date, time, role, _ = schedule[:6]  #no need for the 6th column
            csv_writer.writerow([meeting_id, title, date, time, role or "None"])

        #go back to the start of the file
        csv_file.seek(0)

        #send the file
        await ctx.send("Here is the CSV of upcoming meetings:", file=discord.File(fp=csv_file, filename="upcoming_meetings.csv"))
    
    #if format=pdf
    elif format == "pdf":
        #create a file-like object to write PDF data
        pdf_file = io.BytesIO()
        c = canvas.Canvas(pdf_file, pagesize=letter)

        #add title and font
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "Upcoming Meetings:\n")

        #define table headers and starting position
        headers = ["Meeting_ID", "Title", "Date", "Time", "Role"]
        y_position = 730
        x_positions = [100, 200, 300, 400, 500]

        #draw table headers
        for i, header in enumerate(headers):
            c.drawString(x_positions[i], y_position, header)

        #draw table separators (lines)
        c.setLineWidth(1)
        c.line(90, y_position - 5, 600, y_position - 5)  #add lines for table 
        y_position -= 20  #advance down

        # Draw the table data
        for schedule in schedules:
            meeting_id, title, date, time, role, _ = schedule[:6]  #no need for 6th column

            #draw each cell 
            c.drawString(x_positions[0], y_position, str(meeting_id))
            c.drawString(x_positions[1], y_position, str(title))
            c.drawString(x_positions[2], y_position, str(date))
            c.drawString(x_positions[3], y_position, str(time))
            c.drawString(x_positions[4], y_position, str(role or "None"))

            #draw line for table
            c.line(90, y_position - 5, 600, y_position - 5)

            y_position -= 20  #advance down

        #save PDF
        c.save()

        #rewind to beginning
        pdf_file.seek(0)
        #send the PDF file
        await ctx.send("Here is the PDF of the upcoming meetings:", file=discord.File(fp=pdf_file, filename="schedule.pdf"))



#custom help command
@client.command()
async def helpme(ctx, command_name: str = None):
    """shows help information for commands. without a command name, lists all available commands.
    syntax: !helpme [command_name]"""
    #if no command name is provided, show all commands
    if command_name is None:
        help_text = "Here are the available commands:\n"
        for command in client.commands:
            #for each command, include its name and description
            help_text += f"**!{command.name}**: {command.help}\n"
        await ctx.send(help_text)
    else:
        #show help for a specific command
        command = client.get_command(command_name)
        if command:
            #send specific command's help text
            await ctx.send(f"**!{command.name}**: {command.help}")
        else:
            #if the command doesn't exist
            await ctx.send(f"No command found with the name `{command_name}`.")


#task to check and send scheduled reminders each time when bot is turned on
@tasks.loop(seconds=10)  
async def check_scheduled_reminders():
    cursor.execute("SELECT * FROM schedule WHERE reminder_sent = FALSE")
    schedules = cursor.fetchall()

    for schedule in schedules:
        title, date, time, role, reminder_sent = schedule[1], schedule[2], schedule[3], schedule[4], schedule[5]
        date_time_str = f"{date} {time}"
        meeting_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")

        if datetime.now() <= meeting_time:
            #calculate the reminder time 10 minutes before the meeting
            reminder_time_10 = meeting_time - timedelta(minutes=10)

            #check if the reminder time is in the past but less than 10 minutes ago
            if datetime.now() >= reminder_time_10 and (datetime.now() - reminder_time_10).total_seconds() < 60:
                guild = client.guilds[0]  # Get the first (and only) guild
                channel = discord.utils.get(guild.text_channels, name="🖥-cmd")
                if channel:
                        if role:
                     #get the role from the server to easily mention
                            role_obj = get_role_by_name(guild, role)
    
                            if role_obj:
                                await channel.send(f"Reminder: {title} is starting in 10 minutes! {role_obj.mention}")
                            else:
                                await channel.send(f"Reminder: {title} is starting in 10 minutes!")
                        else:
                            await channel.send(f"Reminder: {title} is starting in 10 minutes!")
                #update the database to mark this reminder as sent so that it won't check for it again
                cursor.execute("UPDATE schedule SET reminder_sent = TRUE WHERE id = ?", (schedule[0],))
                connection.commit()

            #check if the meeting time is now
            if datetime.now() >= meeting_time and (datetime.now() - meeting_time).total_seconds() < 60:
                if channel:
                    if role:
                    #get the role from the server to easily mention
                        role_obj = get_role_by_name(guild, role)
    
                        if role_obj:
                            await channel.send(f"Reminder: {title} is starting in 10 minutes! {role_obj.mention}")
                        else:
                            await channel.send(f"Reminder: {title} is starting in 10 minutes!")
                    else:
                        await channel.send(f"Reminder: {title} is starting in 10 minutes!")

                #mark the reminder as sent for "starting now"
                cursor.execute("UPDATE schedule SET reminder_sent = TRUE WHERE id = ?", (schedule[0],))
                connection.commit()


#start the loop when the bot is ready
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    check_scheduled_reminders.start()  #this starts the task loop
    await check_scheduled_reminders()




#run the bot with your token
client.run('TOKEN')

