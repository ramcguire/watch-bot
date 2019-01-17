import discord
import logging
import os
import pendulum
import pickle

from sqlitedict import SqliteDict
from threading import Timer

from MyGuild import MyGuild
from MyMember import MyMember
from operator import attrgetter


#setup logging to file (ignoring debug logging)
logging.basicConfig(filename='.activity_log.log', level=logging.INFO)

#token for discord bot (from discord api)
with open('discord_token.txt', 'r') as myfile:
    TOKEN = myfile.read()

#can run shutdown/reset commands run
with open('owner_id.txt', 'r') as myfile:
    owner_id = int(myfile.read())

#commands that are displayed with $commands
commands_str = 'Current commands (only valid for guild the $commands message was sent in):\n'
commands_str = '$commands - returns a list of commands user is authorized to use in the guild that the message was sent.\n'
commands_str += '$timespent - returns time spent in voice channels of the requesting user in current guild.\n'
commands_str += '$bot_stats - returns random bot statistics.\n'
commands_str += '$reset_user_stats - removes stats for respective user in this guild.\n'
commands_str += '$set_pref_tz - allows you to set a preferred timezone for data display. Syntax: $set_pref_tz Timezone_name\n'
commands_str += '-------------- use https://en.wikipedia.org/wiki/List_of_tz_database_time_zones to find your Timezone database name.\n'
commands_str += '$get_pref_tz - sends you a message with your current timezone (defaults to UTC).\n'
commands_str += '$guild_stats - Prints a summary of collective time spent by users in voice channels in this guild.'


commands_str_local_admin = '[GUILD ADMIN] $reset_guild_stats (owner/admin of guild only) - removes all tracked time for all users in guild.\n'

commands_str_admin = ''

commands_str_owner = '[OWNER] $reset_commands_run - resets commands_run from bot stats to 0.\n'
commands_str_owner += '[OWNER] $add_admin - adds users that are mentioned in this message to admins list.\n'
commands_str_owner += '[OWNER] $rem_admin - removes users that are mentioned in this message from admins list.\n'
commands_str_owner += '[OWNER] $shutdown - best way to shutdown bot, cleans up all in_channel members and quits.\n'
commands_str_owner += '[OWNER] $re_init - removes all data and bot stats and starts fresh.\n'


client = discord.Client()
continue_timer = True

#keeping track of all data here
#uses sqlite/pickle to store objects in a persistent dictionary
bot_stats = SqliteDict('./bot_stats.db')
u_data = SqliteDict('./user_data.db')
g_data = SqliteDict('./guild_data.db')


admins = []
#load admins information
#if doesn't exist, run InitHelper
if not os.path.isfile('./admins.p'):
    admins.append(str(owner_id))
    pickle.dump(admins, open('./admins.p', 'wb'))

admins = pickle.load(open('./admins.p', 'rb'))


#helper method to increment commands run in bot_stats dict
def increment_commands_run():
    if 'commands_run' in bot_stats.keys():
        cmds_run = bot_stats['commands_run']
        cmds_run += 1
        bot_stats['commands_run'] = cmds_run
        bot_stats.commit()
    else:
        print('no current bot stats found, starting count now')
        logging.warning('no current bot stats found, starting count now')
        bot_stats['commands_run'] = 1
        bot_stats.commit()


#resets commands_run stat
def reset_commands_run(message):
    if is_owner(message.author.id):
        logging.info('recieved (VALID) $reset_commands_run command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        bot_stats['commands_run'] = 0
        bot_stats.commit()
    else:
        logging.warning('recieved (INVALID) $reset_commands_run command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))


#gets list of commands that the author is allowed to use
#each $commands is on a guild by guild basis
#(only returns allowed commands for guild in which message was sent)
def get_commands(message):
    result = commands_str
    if is_local_admin(message.author.id):
        result += commands_str_local_admin
    if is_bot_admin(message.author.id):
        result += commands_str_admin
    if is_owner(message.author.id):
        result += commands_str_owner
    return result


#returns bot_stats string
def get_bot_stats(message):
    #increment commands count
    increment_commands_run()
    log_str = 'recieved $bot_stats command from {0}'.format(message.author.display_name)
    print(log_str)
    logging.info(log_str)
    #construct response
    ret_str = 'This bot is currently in {0} guilds, tracking {1} member(s).\n'.format(bot_stats['guild_count'], bot_stats['user_count'])
    ret_str += 'This bot has processed a total of {0} command(s).'.format(bot_stats['commands_run'])
    return ret_str


#updates admin list and dumps to file
def update_admins():
    print('updating admin list')
    logging.info('updating admin list')
    pickle.dump(admins, open('./admins.p', 'wb'))


#adds all members to admin file
def add_admin(message):
    #adds all members that weren't already in admins list to admins list
    if is_owner(message.author.id):
        logging.info('recieved (VALID) $addadmin command from {0}'.format(message.author.display_name))
        increment_commands_run()
        #only iterates through members not already in admin list
        list_new_admins = [x for x in message.mentions if str(x.id) not in admins]
        for member in list_new_admins:
            new_admin = read_member(member)
            logging.info('adding {0} to admins list'.format(new_admin.display_name))
            admins.append(new_admin.str_id)
        if not len(list_new_admins):
            update_admins()
    else:
        logging.warning('recieved (INVALID) $add_admin command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))


#returns a string with a list of admins
def list_admins(message):
    if is_bot_admin(message.author.id):
        logging.info('recieved (VALID) $list_admins command from {0}'.format(message.author.display_name))
        admin_list = 'List of current admins:\n'
        for admin in admins:
            admin_list += '{0} - id: {1}\n'.format(u_data[admin].display_name, admin)
        return admin_list
    else:
        return 'Not authorized to view bot admins.'


#removes admins from admin file and updates
def remove_admin(message):
    if is_owner(message.author.id):
        logging.info('recieved (VALID) $rem_admin command from {0}'.format(message.author.display_name, message.guild.name))
        increment_commands_run()
        list_rem_admins = [x for x in message.mentions if str(x.id) in admins]
        for member in list_rem_admins:
            admins.remove(str(member.id))
        if not len(list_rem_admins):
            update_admins()
    else:
        logging.warning('recieved (INVALID) $rem_admin command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))


#updates running_since file (pendulum obj)
#does not commit, so need to commit if used outside of update_bot_stats()
def update_running_since():
    bot_stats['running_since'] = pendulum.now('UTC')


#updates all bot stats
#uses BackgroundTimer for regular updates (currently every 60s)
def update_bot_stats():
    active_guilds = [x for x in g_data.values() if x.in_guild]
    guild_count = len(active_guilds)
    user_count = len(u_data)
    bot_stats['guild_count'] = guild_count
    bot_stats['user_count'] = user_count
    update_running_since()
    print('updating bot stats')
    logging.info('updating bot stats')
    bot_stats.commit()


#loads running_since if backup exists
#otherwise sets running_since as current_time
def load_running_since():
    if 'running_since' in bot_stats.keys():
        print('found valid running_since in bot_stats')
        logging.info('found valid running_since in bot_stats')
        return True
    else:
        print('created new running_since file')
        logging.warning('created new running_since file')
        bot_stats['running_since'] = pendulum.now('UTC')
        bot_stats.commit()
        return False


#helper method to add a new member to user_instance
#called by read_member if member not found
def add_new_member(member):
    current_member = MyMember(member)
    u_data[current_member.str_id] = current_member
    log_str = 'added new member {0}'.format(current_member.display_name)
    print(log_str)
    logging.info(log_str)
    u_data.commit()
    return u_data[current_member.str_id]


#handler for member reading
#checks if member is already known, if not, calls add new member
#returns existing member or new member object
def read_member(member):
    if str(member.id) not in u_data.keys():
        if not member.bot:
            new_mem = add_new_member(member)
            return u_data[new_mem.str_id]
        else:
            print('found bot user in read_member: ignoring')
            logging.info('found bot user in read_member: ignoring')
            return None
    #returns member object
    return u_data[str(member.id)]


#handler for all guild joins/init
#runs on guild join and initialization
#handles all users in a voice channel for specified guild
def guild_join(guild):
    new_guild = MyGuild(guild)
    if new_guild.str_id not in g_data.keys():
        g_data[new_guild.str_id] = new_guild
    else:
        current_guild = g_data[new_guild.str_id]
        current_guild.in_guild = True
        g_data[new_guild.str_id] = current_guild

    log_str = 'initializing voice channels in guild \"{0}\"'.format(new_guild.name)
    print(log_str)
    logging.info(log_str)
    for ch in guild.voice_channels:
        current_guild = g_data[new_guild.str_id]
        current_guild.update_voice_channels(guild)
        for mem in ch.members:
            current_member = read_member(mem)
            if current_member is None:
                pass
            current_member.set_current_channel(None, ch)
            u_data[current_member.str_id] = current_member
    g_data.commit()
    u_data.commit()


#helper method to update all members in channels
#used before shutting down/updating
#updates time for all users currently in channels
def set_leave_all():
    members_in_channel = [x for x in u_data.values() if x.in_channel]
    for member in members_in_channel:
        member.adjust_leave_time(pendulum.now('UTC'))
        u_data[member.str_id] = member
    u_data.commit()


#handler method for any members with in_channel = True
#used on init if shutdown = False (bad shutdown, assume users still in_channel)
#if a running_since values was not able to be loaded, won't set manual leave time and will lose some time info
def check_in_channel():
    members_in_channel = [x for x in u_data.values() if x.in_channel]
    if load_running_since():
        log_str = 'cleaning up users who were left as in channel (bad shutdown)'
        print(log_str)
        logging.warning(log_str)
        man_leave_time = bot_stats['running_since']
        for members in members_in_channel:
            members.adjust_leave_time(man_leave_time)
            u_data[members.str_id] = members
    else:
        log_str = 'invalid running_since'
        print(log_str)
        logging.warning(log_str)
        for members in members_in_channel:
            members.in_channel = False
            u_data[members.str_id] = members
    u_data.commit()


#returns a collective timesummary for users spent in each voice channel
#only works in guild
def get_guild_stats(message):
    increment_commands_run()
    total_time = 0.0
    ret_str = 'User voice channel activity in guild \"{0}\"\n'.format(message.guild.name)
    for ch in message.guild.voice_channels:
        matching_users = [x for x in u_data.values() if str(ch.id) in x.channel_info]
        this_channel = 0.0
        if len(matching_users):
            active_users = 0
            for items in matching_users:
                this_channel += items.get_channel_info(ch.id).get_time_in_channel()
                active_users += 1
            ret_str += '{0} - {1} collective time wasted by {2} users.\n'.format(ch.mention, format_seconds(this_channel), str(active_users))
        else:
            ret_str += '{0} - No data recorded for this channel\n'.format(ch.mention)
        total_time += this_channel
    ret_str += 'Total time spent in voice channels by users: {0}\n'.format(format_seconds(total_time))
    return ret_str


#calculates timespent for user in all tracked guilds
def get_full_timesummary(message):
    increment_commands_run()
    ret_str = ''
    member_id = str(message.author.id)
    log_str = 'recieved $timespent command from \"{0}\" DMChannel'.format(message.author.display_name)
    print(log_str)
    logging.info(log_str)
    no_data_str = 'No voice channel data found for \"{0}\".'.format(message.author.display_name)
    if member_id not in u_data.keys():
        return no_data_str
    member = u_data[member_id]
    for guilds in member.guild_info.keys():
        ret_str += 'Guild: {0}\n'.format(g_data[str(guilds)].name)
        guild_channels = [x for x in member.channel_info.values() if x.guild_id == int(guilds)]
        chan_info = sorted(guild_channels, key=attrgetter('name'))
        #Loop through sorted channel names
        for ch in chan_info:
            #get base time in channel
            time_in_channel = ch.get_time_in_channel()
            #add time information to time summary
            ch_summary = '{0} - {1}\n'.format(ch.mention, format_seconds(time_in_channel))
            ret_str += ch_summary
        if not len(chan_info):
            ret_str += 'No data found for guild\n'
        else:
            data_since = 'Data collected since: {0}\n'.format((member.guild_info[guilds]).in_tz(member.pref_tz))
            ret_str += data_since
    return ret_str


#calculates time_spent when passed a message obj
#returns result as string
def get_timesummary(message):
    increment_commands_run()
    guild_id = str(message.guild.id)
    member_id = str(message.author.id)
    log_str = 'recieved $timespent command from \"{0}\" in guild \"{1}\"'.format(message.author.display_name, message.guild.name)
    print(log_str)
    logging.info(log_str)
    no_data_str = 'No voice channel data found for \"{0}\" in guild \"{1}\"'.format(message.author.display_name, message.guild.name)
    #first check if we have any data on user
    if str(member_id) not in u_data.keys():
        return no_data_str
    #member object we will use
    member = u_data[str(member_id)]
    #start creating response string
    time_summary = '{0}\'s summary of time spent in voice channels in \"{1}\":\n'.format(member.display_name, message.guild.name)

    #filter only voice channels from guild where message was sent
    guild_channels = [x for x in member.channel_info.values() if x.guild_id == message.guild.id]
    if not len(guild_channels):
        return no_data_str
    #alphabetically sort guild channels
    chan_info = sorted(guild_channels, key=attrgetter('name'))
    #Loop through sorted channel names
    for ch in chan_info:
        #get base time in channel
        time_in_channel = ch.get_time_in_channel()
        #add time information to time summary
        ch_summary = '{0} - {1}\n'.format(ch.mention, format_seconds(time_in_channel))
        time_summary = time_summary + ch_summary
    data_since = 'Data collected since: {0}\n'.format((member.guild_info[guild_id]).in_tz(member.pref_tz))
    time_summary = time_summary + data_since
    return time_summary


#method that resets one users stats in all tracked guilds
def reset_my_stats(message):
    increment_commands_run()
    logging.info('recieved $reset_user_stats command from {0} in DMChannel'.format(message.author.display_name))
    if str(message.author.id) in u_data.keys():
        member = u_data[str(message.author.id)]
        member.channel_info = {}
        member.creation_time = pendulum.now('UTC').replace(microsecond=0)
        u_data[str(message.author.id)] = member
        u_data.commit()


#method for resetting individual user stats
#returns string based on input message
def reset_user_stats(message):
    increment_commands_run()
    logging.info('recieved $reset_user_stats command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
    this_guild = message.guild.id
    deletable = []
    if str(message.author.id) in u_data.keys():
        member = u_data[str(message.author.id)]
        for channels in member.channel_info.values():
            if this_guild == channels.guild_id:
                deletable.append(str(channels.str_id))
        for i in deletable:
            del member.channel_info[i]
        u_data[member.str_id] = member
        u_data.commit()
        #OUTPUT LINE
        log_str = 'Removed user data for {0} in guild \"{1}\"'.format(member.display_name, message.guild.name)
        logging.info(log_str)
        return log_str


#method for resetting user stats for this guild - will continue to log data
def reset_guild_stats(message):
    if is_owner(message.author.id) or is_bot_admin(message.author.id) or is_local_admin(message.author.id):
        logging.info('recieved (VALID) $rem_guild_stats command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        increment_commands_run()
        log_str = 'removing all stats from guild \"{0}\"'.format(message.guild.name)
        print(log_str)
        logging.info(log_str)
        deletable = []
        this_guild = message.guild.id
        for members in message.guild.members:
            if str(members.id) in u_data.keys():
                member = u_data[str(members.id)]
                for channels in member.channel_info.values():
                    if this_guild == channels.guild_id:
                        deletable.append(str(channels.str_id))
                for i in deletable:
                    del member.channel_info[i]
                u_data[member.str_id] = member
        return 'Removing all user data for voice channels in this guild \"{0}\" and re-initializing.'.format(message.guild.name)
        u_data.commit()
        guild_join(message.guild)
    else:
        logging.info('recieved (INVALID) $rem_guild_stats command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        return 'Unathorized'


#helper method to format seconds into a readable time
#returns as a string
def format_seconds(seconds):
    time = round(seconds)
    time_str = ''
    day = '0'
    hour = '0'
    minute = '0'
    if time > 86400:
        day = str(time // 86400)
        time = time % 86400
    if time > 3600:
        hour = str(time // 3600)
        time = time % 3600
    if time > 60:
        minute = str(time // 60)
        time = time % 60
    time_str = '{0} seconds'.format(time)
    if not minute == '0':
        time_str = '{0} minutes and {1}'.format(minute, time_str)
    if not hour == '0':
        time_str = '{0} hour(s), {1}'.format(hour, time_str)
    if not day == '0':
        time_str = '{0} day(s), {1}'.format(day, time_str)
    return time_str


#helper method to determine if owner (returns True if owner)
#checks if input id matches owner id - both converted to str
def is_owner(id):
    if str(id) == str(owner_id):
        return True
    return False


#helper method to determine if user is bot admin (stored in admins)
#checks if input id in admins list (returns True)
def is_bot_admin(id):
    if str(id) in admins:
        return True
    if str(id) == str(owner_id):
        return True
    return False


#will return true if bot admin or local admin (admin on guild)
def is_local_admin(id):
    str_id = str(id)
    if is_owner(str_id):
        return True
    if is_bot_admin(str_id):
        return True
    if is_owner(str_id):
        return True
    return False


#should handle everything for bot init
#either startup or $re_init command form owner
def on_bot_init():
    if not len(u_data):
        print('Looks like this is the first time initializing user stats')
        logging.info('Looks like this is the first time initializing user stats')
    log_str = 'We have logged in as {0.user}'.format(client)
    print(log_str)
    logging.info(log_str)
    print('initializing guilds and channels')
    logging.info('initializing guilds and channels')
    if 'shutdown' in bot_stats.keys():
        if not bot_stats['shutdown']:
            if len(u_data):
                print('using check_in_channel')
                check_in_channel()
    bot_stats['shutdown'] = False
    #gets list of guilds
    print('now looping through current guilds')
    logging.info('now looping through current guilds')
    for g in client.guilds:
        guild_join(g)
    update_bot_stats()
    u_data.commit()
    bot_stats.commit()
    global bkg_timer
    bkg_timer = Timer(60.0, update_bot_stats)
    bkg_timer.start()
    logging.info('Finished init, starting timer for frequent bot_stats updates')


#method to help fully re_init bot and data
#will lose all tracked information!
def re_init(message):
    #if is authorized
    if is_owner(message.author.id):
        logging.info('recieved $re_init command from {0}'.format(message.author.display_name))
        #clear all tracked data (will be re-initialized in on_bot_init)
        g_data.clear()
        u_data.clear()
        bot_stats.clear()
        g_data.commit()
        u_data.commit()
        bot_stats.commit()
        #remove admins file and reset to owner_id
        if os.path.exists('./admins.p'):
            os.remove('./admins.p')
        admins = []
        admins.append(str(owner_id))
        update_admins()
        #reset commands run and set shutdown = True
        bot_stats['commands_run'] = 0
        bot_stats['shutdown'] = True
        #cancels timer for re-init later
        global bkg_timer
        bkg_timer.cancel()
        bkg_timer = None
        logging.info('Canceled bkg_timer as part of re_init')
        #clear the log file??? why do we have logging in this function....
        #maybe change....
        clear_log_file()
        #finally, call on_bot_init
        on_bot_init()


#clear log file
#maybe save it later?
def clear_log_file():
    with open('./activity_log.log', 'w') as file:
        pass


#function for shutting down bot
#cleans up all in channel connections and updates stats
def shutdown(message):
    if is_owner(message.author.id):
        increment_commands_run()
        logging.info('recieved $shutdown command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        #cancel bkg_timer, and set it to None
        global bkg_timer
        bkg_timer.cancel()
        bkg_timer = None
        print('Canceled timer, finishing shutdown procedures')
        logging.info('Canceled timer, finishing shutdown procedures')
        #make all users leave channel and update shutdown value
        set_leave_all()
        bot_stats['shutdown'] = True
        update_bot_stats()
        #close sqlitedict connections
        u_data.close()
        bot_stats.close()
        logging.info('closing client and quitting script')
    else:
        logging.warning('INVALID $shutdown command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))


def set_pref_tz(message):
    #split message into list and remove the $set_pref_tz
    arguments = message.content.split(' ')
    del arguments[0]
    #if there is another argument
    if len(arguments):
        #check if argument is a valid timezone name
        if arguments[0] in pendulum.timezones:
            increment_commands_run()
            #set and update pref_tz
            member = read_member(message.author)
            member.pref_tz = arguments[0]
            u_data[member.str_id] = member
            u_data.commit()
            return True
    #returns False if invalid for any reason
    return False


#returns the pref_tz of the author
def get_pref_tz(message):
    increment_commands_run()
    member = read_member(message.author)
    if member is None:
        return None
    return member.pref_tz


#leaves guild message was sent in
#for local_admin or owner
def leave_guild(message):
    #if user is authorized to run this command
    if is_owner(message.author.id) or is_local_admin(message.author.id):
        increment_commands_run()
        logging.info('recieved $leave_guild command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        #iterate through members in voice channels and adjust leave time
        for channels in message.guild.voice_channels:
            for members in channels.members:
                current_mem = read_member(members)
                if current_mem is None:
                    pass
                current_mem.adjust_leave_time(pendulum.now('UTC'))
                u_data[current_mem.str_id] = current_mem
        #commit changes, and remove guild from guild data
        u_data.commit()
        logging.info('finished closing voice channel information for members in {0}, leaving guild'.format(message.guild.name))
        guild_to_leave = g_data[str(message.guild.id)]
        guild_to_leave.in_guild = False
        g_data[str(message.guild.id)] = guild_to_leave
        update_bot_stats()
        return
    logging.warning('recieved INVALID $leave_guild command from {0}'.format(message.author.display_name))
    return

#------------------------------------------------------------------------------------------------------------------------#
#-------------------------------------------------ALL EVENTS BELOW-------------------------------------------------------#
#------------------------------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------------------------------#
#------------------------------------------------------------------------------------------------------------------------#


@client.event
async def on_ready():
    on_bot_init()


#called when bot is added to a guild
#just calls guild_join() method
@client.event
async def on_guild_join(guild):
    guild_join(guild)


#event for all messages, handles commands
#look into using bot functionality from discord library
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    #timespent command
    if message.content.startswith('$timespent'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('Full voice channel time information:')
            await message.channel.send(get_full_timesummary(message))
            return
        await message.channel.send(get_timesummary(message))
        return

    #shutdown command
    if message.content.startswith('$shutdown'):
        #handles all shutdown procedures
        shutdown(message)
        #closes client and exits
        await client.close()
        exit()
        return

    #add_admin
    #OWNER ONLY
    if message.content.startswith('$add_admin'):
        add_admin(message)
        return

    #list_admins
    #OWNER OR BOT ADMIN
    if message.content.startswith('$list_admins'):
        await message.author.send(list_admins(message))

    #rem_admin
    #OWNER ONLY
    if message.content.startswith('$rem_admin'):
        remove_admin(message)
        return

    #reset_guild_stats
    #LOCAL ADMIN, BOT ADMIN, OR OWNER
    if message.content.startswith('$reset_guild_stats'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('This command needs to be sent from a guild.')
            return
        await message.channel.send(reset_guild_stats(message))
        guild_join(message.guild)
        return

    #reset_user_stats
    if message.content.startswith('$reset_user_stats'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('Are you sure you want to remove all user stats?')
            await message.channel.send('Send \"CONFIRM\" to confirm.')

            def check(m):
                return m.content == 'CONFIRM'
            msg = await client.wait_for('message', check=check)
            reset_my_stats(message)
            return
        reset_user_stats(message)
        return

    #botstats
    if message.content.startswith('$bot_stats'):
        await message.channel.send(get_bot_stats(message))
        return

    #commands
    if message.content.startswith('$commands'):
        await message.author.send(get_commands(message))
        return

    #reset_commands_run
    #OWNER ONLY
    if message.content.startswith('$reset_commands_run'):
        reset_commands_run(message)
        return

    #re_init
    #OWNER ONLY
    if message.content.startswith('$re_init'):
        re_init(message)
        return

    #set_pref_tz
    if message.content.startswith('$set_pref_tz'):
        if set_pref_tz(message):
            input_tz = message.content.split(' ')
            await message.author.send('Successfully set preferred timezone to {0}'.format(input_tz[1]))
            return
        helper_str = 'Timezone information not found! Try again using a valid timezone.'
        helper_str += 'Accepts timezones under TZ Database name found:'
        helper_str += 'https://en.wikipedia.org/wiki/List_of_tz_database_time_zones'
        helper_str += 'Your current timezone is set to: {0} (default is UTC)'.format(get_pref_tz(message))
        await message.author.send(helper_str)
        return

    #get_pref_tz
    if message.content.startswith('$get_pref_tz'):
        await message.author.send('Your current preferred timezone is set to {0}'.format(get_pref_tz(message)))

    #leave_guild
    if message.content.startswith('$leave_guild'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('This command needs to be sent from a guild channel.')
            return
        leave_guild(message)
        await message.channel.send('No longer tracking voice channel activity. Bye!')
        await message.guild.leave()

    if message.content.startswith('$guild_stats'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('This command needs to be sent from a guild channel.')
            return
        await message.channel.send(get_guild_stats(message))

    #handling direct messages?
    if type(message.channel) is discord.DMChannel:
        print('got DM!!!')
        return


#for voice state updates
#any time a member leaves or joins a voice channel
@client.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        print('bot user, ignoring')
        return
    print('voice status update for {0}'.format(member.display_name))
    current_member = read_member(member)
    current_member.set_current_channel(before.channel, after.channel)
    u_data[current_member.str_id] = current_member
    u_data.commit()
    return

client.run(TOKEN)
