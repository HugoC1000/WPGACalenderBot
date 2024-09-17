import discord
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from discord.ext import commands
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import UserSchedule, Base 
from table2ascii import table2ascii as t2a, PresetStyle
import psycopg2
import numpy as np

from config import CUSTOM_BLOCK_TIMES, CUSTOM_BLOCK_ORDERS, SPECIAL_UNIFORM_DATES, SCHEDULE_PATTERN, DAYS_OFF, CUSTOM_DAYS_OFF, TIME_SLOTS, SCHEDULE_START, ROOMS_FOR_COURSES
from config import BLOCK_1A_COURSES,BLOCK_1B_COURSES,BLOCK_1C_COURSES,BLOCK_1D_COURSES, BLOCK_1E_COURSES, BLOCK_2A_COURSES, BLOCK_2B_COURSES, BLOCK_2C_COURSES, BLOCK_2D_COURSES, BLOCK_2E_COURSES
from database import get_or_create_user_schedule, save_user_schedule, get_same_class, compare_schedule, get_school_info_from_date, modify_or_create_new_date, edit_uniform_for_date,edit_block_order_for_date, edit_block_times_for_date, add_or_update_alternate_room, change_one_block
from schedule import is_day_off, get_blocks_for_date, get_block_times_for_date, get_uniform_for_date, get_alt_rooms_for_date,get_ap_flex_courses_for_date, generate_schedule, get_user_courses, has_set_courses, get_next_course

# Load environment variables from .env file
load_dotenv()

intents = discord.Intents.all()
bot = discord.Bot(intents = intents)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

async def get_courses_from_block(ctx: discord.AutocompleteContext):
    selectedBlock = ctx.options['block']
    if selectedBlock == '1A':
        return BLOCK_1A_COURSES
    elif selectedBlock == '1B':
        return BLOCK_1B_COURSES
    elif selectedBlock == '1C':
        return BLOCK_1C_COURSES
    elif selectedBlock == '1D':
        return BLOCK_1D_COURSES
    elif selectedBlock == '1E':
        return BLOCK_1E_COURSES
    elif selectedBlock == '2A':
        return BLOCK_2A_COURSES
    elif selectedBlock == '2B':
        return BLOCK_2B_COURSES
    elif selectedBlock == '2C':
        return BLOCK_2C_COURSES
    elif selectedBlock == '2D':
        return BLOCK_2D_COURSES
    elif selectedBlock == '2E':
        return BLOCK_2E_COURSES



def getUserById(user_id):
    try:
        # Fetch the user by their ID
        user = bot.fetch_user(user_id)    
        return user
    except discord.NotFound:
        return "User Not Found"
    except discord.HTTPException as e:
        print(f'Failed to fetch user. Error: {str(e)}')
        return "Error"


schedule_input_cmds = bot.create_group("input", "input the courses you have for each block")

@schedule_input_cmds.command(name="change", description="Change one of your blocks")
async def change(ctx: discord.ApplicationContext, block: discord.Option(str, choices=["1A", "1B", "1C", "1D", "1E", "2A", "2B", "2C", "2D", "2E"]), course_name: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_courses_from_block))):

    user_id = str(ctx.author.id)
    username=str(ctx.author)
    
    result = change_one_block(user_id,username,block,course_name)
    if(result):
        await ctx.respond(f"{course_name} saved to {block}")
    else:
        await ctx.respond("An error occured")

@schedule_input_cmds.command(name = "setup", description = "Set up your schedule here!")
async def setup_schedule(ctx: discord.ApplicationContext, block1a : discord.Option(str, choices = BLOCK_1A_COURSES), block1b : discord.Option(str, choices = BLOCK_1B_COURSES), block1c :  discord.Option(str, choices = BLOCK_1C_COURSES), block1d :  discord.Option(str, choices = BLOCK_1D_COURSES), block1e :  discord.Option(str, choices = BLOCK_1E_COURSES), 
                         block2a : discord.Option(str, choices = BLOCK_2A_COURSES), block2b : discord.Option(str, choices = BLOCK_2B_COURSES), block2c : discord.Option(str, choices = BLOCK_2C_COURSES), block2d : discord.Option(str, choices = BLOCK_2D_COURSES), block2e : discord.Option(str, choices = BLOCK_2E_COURSES)):
   
    user_id = str(ctx.author.id)
    username = ctx.author.name

    schedule_data = {
        'Username' : username,
        'A1': block1a,
        'B1': block1b,
        'C1': block1c,
        'D1': block1d,
        'E1': block1e,
        'A2': block2a,
        'B2': block2b,
        'C2': block2c,
        'D2': block2d,
        'E2': block2e
    }
    print("About to print schedule data")
    print(schedule_data)
    save_user_schedule(user_id, schedule_data)
    await ctx.respond("Schedule saved!")



getCmds = bot.create_group("get", "Get information about schedules and courses")

@getCmds.command(name = "people_in_class", description = "Gives a list of people who are in the class specified")
async def people_in_my_class(ctx, block: discord.Option(str, choices = ["1A","1B","1C","1D","1E","2A","2B","2C","2D","2E"]), course_name : discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_courses_from_block))):

    # Call your function to get users in the same class
    output = get_same_class(block, course_name) 

    if not output:
        await ctx.respond(f"No users found in {course_name} {block}.")
        return

    # Prepare the response message
    response = f"Those in {course_name} {block} are:\n"
    
    for theid in output:
        # print(type(theid[0]))
        # print(ctx.author.guild)
        # print(ctx.author.guild.get_member(int(theid)))
        try:
            name = ctx.author.guild.get_member(int(theid)).name
            # print(type(name))
            response += f"- {name}\n"
        except:
            response += f"- {theid} (Not in this server) \n"

    # Send the response
    await ctx.respond(response)


@getCmds.command(name="today_schedule", description="Get your schedule for today.")
async def get_today_schedule(ctx):
    user_id = str(ctx.author.id)
    today = datetime.now().date()
    
    # Fetch the user schedule
    user_schedule = get_or_create_user_schedule(user_id, username=str(ctx.author))
    
    # Get today's schedule and block times
    today_schedule = get_blocks_for_date(today)
    if not today_schedule:
        await ctx.respond("No school today.")
        return
    
    if not has_set_courses(user_schedule):
        await ctx.respond("You haven't set any courses yet.")
        return
    
    # Fetch other necessary data
    user_courses = get_user_courses(user_schedule)
    today_block_times = get_block_times_for_date(today)
    alt_rooms = get_alt_rooms_for_date(today)
    ap_flex_courses = get_ap_flex_courses_for_date(today)
    
    # Generate the schedule
    print(today_schedule)
    courses_output = generate_schedule(user_schedule, today_schedule, today_block_times, alt_rooms, ap_flex_courses, user_courses)
    
    await ctx.respond(f"**## Today's schedule for {ctx.author.name}:**```\n" + "\n".join(courses_output) + "```")


@getCmds.command(name="tomorrow_schedule", description="Get your schedule for tomorrow.")
async def get_tomorrow_schedule(ctx):
    user_id = str(ctx.author.id)
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    tomorrow = tomorrow.date()
    
    # Fetch the user schedule
    user_schedule = get_or_create_user_schedule(user_id, username=str(ctx.author))
    
    # Get today's schedule and block times
    tomorrow_schedule = get_blocks_for_date(tomorrow)
    if not tomorrow_schedule:
        await ctx.respond("No school tomorrow.")
        return
    
    if not has_set_courses(user_schedule):
        await ctx.respond("You haven't set any courses yet.")
        return
    
    # Fetch other necessary data
    user_courses = get_user_courses(user_schedule)
    tomorrow_block_times = get_block_times_for_date(tomorrow)
    alt_rooms = get_alt_rooms_for_date(tomorrow)
    ap_flex_courses = get_ap_flex_courses_for_date(tomorrow)
    
    # Generate the schedule
    print(tomorrow_schedule)
    courses_output = generate_schedule(user_schedule, tomorrow_schedule, tomorrow_block_times, alt_rooms, ap_flex_courses, user_courses)
    print(courses_output)
    
    await ctx.respond(f"**## Tomorrow's schedule for {ctx.author.name}:**```\n" + "\n".join(courses_output) + "```")

@getCmds.command(name = "compare_schedules", description = "Compare schedules for two people")
async def compare_schedules(ctx, person1: discord.Option(discord.Member,description = "Person 1"), person2: discord.Option(discord.Member,description = "Person 2")):
    schedule1, schedule2 = compare_schedule(person1.id, person2.id)
    # await ctx.send(f"User 1 Schedule: {schedule1}")
    # await ctx.send(f"User 2 Schedule: {schedule2}")
    
    output = t2a(
        header=["Block", f"{person1.name}", f"{person2.name}"],
        body=[["1A", schedule1.get('1A'), schedule2.get('1A')],["1B", schedule1.get('1B'), schedule2.get('1B')],["1C", schedule1.get('1C'), schedule2.get('1C')],
            ["1D", schedule1.get('1D'), schedule2.get('1D')],["1E", schedule1.get('1E'), schedule2.get('1E')],
            ["2A", schedule1.get('2A'), schedule2.get('2A')],["2B", schedule1.get('2B'), schedule2.get('2B')],["2C", schedule1.get('2C'), schedule2.get('2C')],
            ["2D", schedule1.get('2D'), schedule2.get('2D')],["2E", schedule1.get('2E'), schedule2.get('2E')]
        ],
        style=PresetStyle.thin
    )
    await ctx.respond(f"```\n{output}\n```")


@bot.slash_command(name="upnxt", description="Quickly get your next course for today.")
async def up_next(ctx):
    user_id = str(ctx.author.id)
    today = datetime.now().date()
    current_time = datetime.now().time()
    
    user_schedule = get_or_create_user_schedule(user_id, username=str(ctx.author))
    
    # Get today's schedule and block times
    today_schedule = get_blocks_for_date(today)
    if not today_schedule:
        await ctx.respond("No school today.")
        return
    
    if not has_set_courses(user_schedule):
        await ctx.respond("You haven't set any courses yet.")
        return
    
    user_courses = get_user_courses(user_schedule)
    today_block_times = get_block_times_for_date(today)
    alt_rooms = get_alt_rooms_for_date(today)
    ap_flex_courses = get_ap_flex_courses_for_date(today)
    
    await ctx.respond(get_next_course(user_schedule, today_schedule, today_block_times, alt_rooms, ap_flex_courses,user_courses))
    

@bot.slash_command(name = "ping_class", description = "Pings everyone in this server whose in the class specifed")
async def ping_class(ctx,block: discord.Option(str, choices = ["1A","1B","1C","1D","1E","2A","2B","2C","2D","2E"]), course_name : discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_courses_from_block))):
     # Call your function to get users in the same class
    output = get_same_class(block, course_name)  # Implement this function to query the database\

    if not output:
        await ctx.respond(f"No users found in {course_name} {block}.")
        return
    
    response = ""
    
    for theid in output:
        try:
            # print(type(name))
            response += f"<@{int(theid)}>"
        except:
            response += f"{theid} (Not in this server) \n"

    await ctx.respond(response,allowed_mentions=discord.AllowedMentions(users=True))


uniform_cmds = bot.create_group("uniform", "Get information about uniform")

@uniform_cmds.command(name="today", description="Get uniform for today")
async def get_uniform_for_today(ctx: discord.ApplicationContext):
    today = datetime.today()
    weekno = today.weekday()
    today_date = today.date()

    # Initialize response
    response = ""

    # Query the database for today's schedule
    
    today_block_order_info = get_blocks_for_date(today_date)
    today_uniform_info = get_uniform_for_date(today_date)

    # Check for no school days
    if not today_block_order_info:
        response = "No school today."
        await ctx.respond(response)
        return

    # Add uniform details
    if today_uniform_info == "Ceremonial":
        response += "Ceremonial Uniform\n"
    else:
        response += f"{today_uniform_info}\n"

    # Add hoodie allowance based on the day of the week
    if weekno == 4:  # Assuming Friday is the 5th weekday (index 4)
        response += "Hoodie allowed (Exceptions apply)\n"

    # Get user schedule
    user_id = str(ctx.author.id)
    user_schedule = get_or_create_user_schedule(user_id)

    # Handle cases where the user schedule is missing
    if not user_schedule:
        response += "(Unable to predict if you have PE today. Please input schedule to gain access to this feature)\n"
        await ctx.respond(response)
        return

    # Check for PE classes in the user's schedule
    pe_courses = {"PE 10", "PE 11", "PE 10 Brenko", "PE 10 Kimura", "PE Aquatics"}
    
    # Extract the block order for the day from the DB and match with user's schedule
    for block in today_block_order_info:
        course_name = getattr(user_schedule, block[1] + block[0], 'Free period')
        if course_name in pe_courses:
            response += "PE Strip may be needed as you have PE today. (Exceptions apply)\n"
            break  # PE detected, no need to check further slots

    await ctx.respond(response)

@uniform_cmds.command(name="tomorrow", description="Get uniform for tomorrow")
async def get_uniform_for_tomorrow(ctx: discord.ApplicationContext):
    
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    tomorrow_date = tomorrow.date()
    weekno = tomorrow.weekday()

    # Initialize response
    response = ""

    # Query the database for today's schedule
    
    tomorrow_block_order_info = get_blocks_for_date(tomorrow_date)
    tomorrow_uniform_info = get_uniform_for_date(tomorrow_date)

    # Check for no school days
    if not tomorrow_block_order_info:
        response = "No school tomorrow."
        await ctx.respond(response)
        return

    # Add uniform details
    if tomorrow_uniform_info == "Ceremonial":
        response += "Ceremonial Uniform\n"
    else:
        response += f"{tomorrow_uniform_info}\n"

    # Add hoodie allowance based on the day of the week
    if weekno == 4:  # Assuming Friday is the 5th weekday (index 4)
        response += "Hoodie allowed (Exceptions apply)\n"

    # Get user schedule
    user_id = str(ctx.author.id)
    user_schedule = get_or_create_user_schedule(user_id)

    # Handle cases where the user schedule is missing
    if not user_schedule:
        response += "(Unable to predict if you have PE today. Please input schedule to gain access to this feature)\n"
        await ctx.respond(response)
        return

    # Check for PE classes in the user's schedule
    pe_courses = {"PE 10", "PE 11", "PE 10 Brenko", "PE 10 Kimura", "PE Aquatics"}
    
    # Extract the block order for the day from the DB and match with user's schedule
    for block in tomorrow_block_order_info:
        course_name = getattr(user_schedule, block[1] + block[0], 'Free period')
        if course_name in pe_courses:
            response += "PE Strip may be needed as you have PE tomorrow. (Exceptions apply)\n"
            break  # PE detected, no need to check further slots

    await ctx.respond(response)




@bot.slash_command(name="help", description="List all available commands.")
async def help_command(ctx):
    help_message = """
    # **Calendar Bot Help**

    ## **To get started:** Use `/input setup` and input your schedules.

    **Available Commands:**

    All commands have autocomplete inside their options. 

    `/input setup` - Set up your schedule with initial data.

    `/input change [block]` - Update the course name for a specific block (e.g., `/input change 1A`).

    `/get schedule_today` - Displays your schedule for today.

    `/get schedule_tomorrow` - Shows your schedule for tomorrow.

    `/get compare_schedules <user1> <user2>` - Compares the schedules of two users.

    `/get people_in_class <block> <class>` - Lists all people in a specified class block.

    `/ping_class <block> <class>` - Pings everyone in a specified class block.

    `/uniform today` - Check uniform needed today.

    `/uniform tomorrow` - Check uniform needed tomorrow.
    """
    await ctx.respond(help_message)


dev_cmds = bot.create_group("zdeveloper", "Developer commands")

@dev_cmds.command(name = "say", description = "Says something")
async def say(ctx, message : str):
    developer_id = 826334880455589918
    if ctx.author.id == developer_id:
        await ctx.respond(message)
    else:
        await ctx.respond('This command is for developer only')



set_cmds = bot.create_group("set", "Set information aobut tables")

@set_cmds.command(name="uniform", description="Set the uniform for a specific day")
async def set_uniform(ctx: discord.ApplicationContext, date_str: discord.Option(str, description= "YYYY-MM-DD"), new_uniform: str):
    """
    Set the uniform for a given date.
    
    Args:
        ctx (discord.ApplicationContext): The context of the command call.
        date_str (str): The date in "YYYY-MM-DD" format for which to set the uniform.
        new_uniform (str): The new uniform value to set.
    """
    # Convert the string date to a datetime object
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await ctx.respond("Invalid date format. Please use YYYY-MM-DD.")
        return
    
    status = edit_uniform_for_date(date_obj, new_uniform)
    
    if status == 1:
        await ctx.respond("No school on that day")
    elif status == 2:
        await ctx.respond(f"Uniform for {date_str} has been updated to {new_uniform}.")
    elif status == None:
        await ctx.respond(f"An error occured. ")
      
@set_cmds.command(name="block_order", description="Set the block order for a specific day")
async def set_block_order(ctx: discord.ApplicationContext, date_str : discord.Option(str, description="YYYY-MM-DD"),block_order_str: discord.Option(str, description= "Block order seperated by commas. E.g. 1A,1B,1C")):
    """
    Set the block order for a given date.
    
    Args:
        ctx (discord.ApplicationContext): The context of the command call.
        date_str (str): The date in "YYYY-MM-DD" format for which to set the uniform.
        block_order_str (str): The new block order with each block seperated by commas.
    """
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await ctx.respond("Invalid date format. Please use YYYY-MM-DD.")
        return
    
    
    block_order_list = block_order_str.strip().split(',')
    
    status = edit_block_order_for_date(date_obj, block_order_list)
    
    if status == 1:
        await ctx.respond("No school on that day")
    elif status == 2:
        await ctx.respond(f"Block order for {date_str} has been updated to {block_order_list}.")
    elif status == None:
        await ctx.respond(f"An error occured. ")

@set_cmds.command(name="block_times", description="Set the uniform for a specific day")
async def set_block_times(ctx: discord.ApplicationContext, date_str: discord.Option(str, description= "YYYY-MM-DD"), block_times_str: discord.Option(str, description= "Block times seperated by commas. Use dash for recess and lunch. Use default for default block times.")):
    """
    Set the uniform for a given date.
    
    Args:
        ctx (discord.ApplicationContext): The context of the command call.
        date_str (str): The date in "YYYY-MM-DD" format for which to set the uniform.
        block_times_str (str): The new block order with each block seperated by commas.
    """
    # Convert the string date to a datetime object
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await ctx.respond("Invalid date format. Please use YYYY-MM-DD.")
        return
    
    block_times_list = []
    if block_times_str.strip().lower() == "default":
        block_times_list = TIME_SLOTS
    else:
        block_times_list = block_times_str.split(',')
    
    print("e")
    status = edit_block_times_for_date(date_obj, block_times_list)
    
    if status == 1:
        await ctx.respond("No school on that day")
    elif status == 2:
        await ctx.respond(f"Block time for {date_str} has been updated to {block_times_list}.")
    elif status == None:
        await ctx.respond(f"An error occured. ")    
        
@set_cmds.command(name="general", description="Set the all the info for a specific day")
async def update_schedule(ctx: discord.ApplicationContext, date_str: discord.Option(str, description= "YYYY-MM-DD"), uniform: str, is_school: bool, block_order: discord.Option(str, description= "Block order seperated by commas"), block_times: discord.Option(str, description= "Block times seperated by comma. Type default for 'default' times")):
    """
    Update or create a schedule entry for a given date.
    
    Args:
        ctx (discord.ApplicationContext): The context of the command call.
        date_str (str): The date in "YYYY-MM-DD" format for which to update/create the schedule.
        uniform (str): The uniform for the day.
        is_school (bool): Whether the school is open on that date.
        block_order (str): Comma-separated list of block order. Example: "A1,B2,C1,D2".
        block_times (str): Comma-separated list of block times. Example: "08:00-09:00,09:10-10:10,...".
    """
    # Convert string date to a datetime object
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await ctx.respond("Invalid date format. Please use YYYY-MM-DD.")
        return
    # Parse block order and block times
    
    block_times_list = []
    block_order_list = []

    try: 
        if block_times.strip().lower() == "default":
            block_times_list = TIME_SLOTS
        else:
            block_order_list = [block.strip() for block in block_order.split(',')]
            block_times_list = [time.strip() for time in block_times.split(',')]
    except Exception as e:
        await ctx.respond(f"Error parsing block order or block times: {e}")
        return
    
    status = modify_or_create_new_date(date_obj, uniform, is_school, block_order_list, block_times_list)
    
    if not status:
        await ctx.respond("An error occurred while creating an entry")
        return
    else:
        await ctx.respond("Entry added succesfully")

@set_cmds.command(name="add_alt_room", description="Add an alternate room for a course on a specific day")
async def add_alt_room(ctx:discord.ApplicationContext, date_str: discord.Option(str, description= "YYYY-MM-DD"), block: discord.Option(str, choices=["1A", "1B", "1C", "1D", "1E", "2A", "2B", "2C", "2D", "2E"]), course_name: discord.Option(str, autocomplete=discord.utils.basic_autocomplete(get_courses_from_block)), new_room: str):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        await ctx.respond("Invalid date format. Please use YYYY-MM-DD.")
        return
    
    result = add_or_update_alternate_room(date_obj, block, course_name, new_room)
    
    if(result):
        await ctx.respond("Alt room succesfully updated")
        return
    else:
        await ctx.respond("An error occured")
        return
    

print("runs?")

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

bot.run(DISCORD_TOKEN) # run the bot with the token

