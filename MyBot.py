import discord
import logging
import operator
import os
import pendulum
import pickle
from sortedcontainers import SortedDict

from discord.ext import commands
from sqlitedict import SqliteDict
from threading import Timer

from MyGuild import MyGuild
from MyMember import MyMember
from operator import attrgetter


# try to modularize the command prefix
c_prefix = '!'



# setup logging to file (ignoring debug logging)
logging.basicConfig(filename='.activity_log.log', level=logging.INFO)

# token for discord bot (from discord api)
with open('discord_token.txt', 'r') as myfile:
    TOKEN = myfile.readline()

# can run shutdown/reset commands run
with open('owner_id.txt', 'r') as myfile:
    owner_id = int(myfile.readline())

bot = commands.Bot(command_prefix=c_prefix, owner_id=owner_id)

# commands that are displayed with $commands
commands_str = 'Current commands (only valid for guild the $commands message was sent in):\n'
commands_str = c_prefix + 'commands - returns a list of commands user is authorized to use in the guild that the message was sent.\n'
commands_str += c_prefix + 'timespent - returns time spent in voice channels of the requesting user in current guild.\n'
commands_str += c_prefix + 'bot_stats - returns random bot statistics.\n'
commands_str += c_prefix + 'reset_user_stats - removes stats for respective user in this guild. Must confirm by sending CONFIRM in DM.\n'
commands_str += c_prefix + 'set_pref_tz - allows you to set a preferred timezone for data display. Syntax: $set_pref_tz Timezone_name\n'
commands_str += '-------------- use https://en.wikipedia.org/wiki/List_of_tz_database_time_zones to find your Timezone database name.\n'
commands_str += c_prefix + 'get_pref_tz - sends you a message with your current timezone (defaults to UTC).\n'
commands_str += c_prefix + 'guild_stats - Prints a summary of collective time spent by users in voice channels in this guild.'
commands_str += c_prefix + 'gametime - Prints a summary of time spent in games that the bot has tracked. Use \"gametime current\" to see history of current activity.\n'
commands_str += c_prefix + 'guild_games - Prints the collective time users in this guild have spent in each game.\n'

commands_str_local_admin = '[GUILD ADMIN] ' + c_prefix + 'reset_guild_stats (owner/admin of guild only) - removes all tracked time for all users in guild.\n'
commands_str_local_admin = '[GUILD ADMIN] ' + c_prefix + 'leave_guild (owner/admin of guild only) - leaves guild, but does not remove tracked information. Bot can be re-added.\n'


commands_str_admin = ''

commands_str_owner = '[OWNER] ' + c_prefix + 'reset_commands_run - resets commands_run from bot stats to 0.\n'
commands_str_owner += '[OWNER] ' + c_prefix + 'add_admin - adds users that are mentioned in this message to admins list.\n'
commands_str_owner += '[OWNER] ' + c_prefix + 'rem_admin - removes users that are mentioned in this message from admins list.\n'
commands_str_owner += '[OWNER] ' + c_prefix + 'shutdown - best way to shutdown bot, cleans up all in_channel members and quits.\n'
commands_str_owner += '[OWNER] ' + c_prefix + 're_init - removes all data and bot stats and starts fresh.\n'


client = discord.Client()
continue_timer = True

# keeping track of all data here
# uses sqlite/pickle to store objects in a persistent dictionary
bot_stats = SqliteDict('./bot_stats.db')
u_data = SqliteDict('./user_data.db')
g_data = SqliteDict('./guild_data.db')


admins = []
# load admins information
# if doesn't exist, run InitHelper
if not os.path.isfile('./admins.p'):
    admins.append(str(owner_id))
    pickle.dump(admins, open('./admins.p', 'wb'))

admins = pickle.load(open('./admins.p', 'rb'))


# helper method to increment commands run in bot_stats dict
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


# resets commands_run stat
def reset_commands_run(message):
    if is_owner(message.author.id):
        logging.info('recieved (VALID) ' + c_prefix + 'reset_commands_run command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        bot_stats['commands_run'] = 0
        bot_stats.commit()
    else:
        logging.warning('recieved (INVALID) ' + c_prefix + 'reset_commands_run command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))


# gets list of commands that the author is allowed to use
# each is on a guild by guild basis
# (only returns allowed commands for guild in which message was sent)
def get_commands(message):
    result = commands_str
    if is_local_admin(message.author.id):
        result += commands_str_local_admin
    if is_bot_admin(message.author.id):
        result += commands_str_admin
    if is_owner(message.author.id):
        result += commands_str_owner
    return result


# returns bot_stats string
def get_bot_stats(message):
    # increment commands count
    increment_commands_run()
    log_str = 'recieved ' + c_prefix + 'bot_stats command from {0}'.format(message.author.display_name)
    print(log_str)
    logging.info(log_str)
    # construct response
    ret_str = 'This bot is currently in {0} guilds, tracking {1} member(s).\n'.format(bot_stats['guild_count'], bot_stats['user_count'])
    ret_str += 'This bot has processed a total of {0} command(s).'.format(bot_stats['commands_run'])
    return ret_str


# updates admin list and dumps to file
def update_admins():
    print('updating admin list')
    logging.info('updating admin list')
    pickle.dump(admins, open('./admins.p', 'wb'))


# adds all members to admin file
def add_admin(message):
    # adds all members that weren't already in admins list to admins list
    if is_owner(message.author.id):
        logging.info('recieved (VALID) ' + c_prefix + 'addadmin command from {0}'.format(message.author.display_name))
        increment_commands_run()
        # only iterates through members not already in admin list
        list_new_admins = [x for x in message.mentions if str(x.id) not in admins]
        for member in list_new_admins:
            new_admin = read_member(member)
            logging.info('adding {0} to admins list'.format(new_admin.display_name))
            admins.append(new_admin.str_id)
        if not len(list_new_admins):
            update_admins()
    else:
        logging.warning('recieved (INVALID) ' + c_prefix + 'add_admin command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))


# returns a string with a list of admins
def list_admins(message):
    if is_bot_admin(message.author.id):
        logging.info('recieved (VALID) ' + c_prefix + 'list_admins command from {0}'.format(message.author.display_name))
        admin_list = 'List of current admins:\n'
        for admin in admins:
            admin_list += '{0} - id: {1}\n'.format(u_data[admin].display_name, admin)
        return admin_list
    else:
        return 'Not authorized to view bot admins.'


# removes admins from admin file and updates
def remove_admin(message):
    if is_owner(message.author.id):
        logging.info('recieved (VALID) ' + c_prefix + 'rem_admin command from {0}'.format(message.author.display_name, message.guild.name))
        increment_commands_run()
        list_rem_admins = [x for x in message.mentions if str(x.id) in admins]
        for member in list_rem_admins:
            admins.remove(str(member.id))
        if not len(list_rem_admins):
            update_admins()
    else:
        logging.warning('recieved (INVALID) ' + c_prefix + 'rem_admin command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))


# updates running_since file (pendulum obj)
# does not commit, so need to commit if used outside of update_bot_stats()
def update_running_since():
    bot_stats['running_since'] = pendulum.now('UTC')


# updates all bot stats
# uses BackgroundTimer for regular updates (currently every 60s)
def update_bot_stats():
    active_guilds = [x for x in g_data.values() if x.in_guild]
    guild_count = len(active_guilds)
    user_count = len(u_data)
    bot_stats['guild_count'] = guild_count
    bot_stats['user_count'] = user_count
    bot_stats['running_since'] = pendulum.now('UTC')
    print('updating bot stats')
    logging.info('updating bot stats')
    bot_stats.commit()


# loads running_since if backup exists
# otherwise sets running_since as current_time
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


# helper method to add a new member to user_instance
# called by read_member if member not found
def add_new_member(member):
    current_member = MyMember(member)
    u_data[current_member.str_id] = current_member
    log_str = 'added new member {0}'.format(current_member.display_name)
    print(log_str)
    logging.info(log_str)
    u_data.commit()
    return u_data[current_member.str_id]


# handler for member reading
# checks if member is already known, if not, adds new member
# returns member object to be worked on
def read_member(member):
    if str(member.id) not in u_data.keys():
        if not member.bot:
            new_mem = add_new_member(member)
            #new_mem.process_activities()
            return u_data[new_mem.str_id]
        else:
            print('found bot {0} in read_member: ignoring'.format(member.display_name))
            logging.info('found bot user in read_member: ignoring')
            return None
    # returns member object
    return u_data[str(member.id)]


# handler for all guild joins/init
# runs on guild join and initialization
# handles all users in a voice channel for specified guild
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
    current_guild = g_data[str(guild.id)]
    for ch in guild.voice_channels:
        current_guild.update_voice_channels(guild)
        for mem in ch.members:
            current_member = read_member(mem)
            if current_member is None:
                pass
            else:
                current_member.set_current_channel(None, ch)
                u_data[current_member.str_id] = current_member
    g_data.commit()
    u_data.commit()


# helper method to update all members in channels
# used before shutting down/updating
# updates time for all users currently in channels
def set_leave_all():
    timestamp = pendulum.now('UTC')
    members_in_channel = [x for x in u_data.values() if x.in_channel]
    members_in_game = [x for x in u_data.values() if len(x.current_activities)]
    for member in members_in_channel:
        member.adjust_leave_time(timestamp)
        u_data[member.str_id] = member
    for member in members_in_game:
        for game in member.current_activities:
            ended_game = member.activity_info[game]
            ended_game.update_end_time(timestamp)
            ended_game.total_time += ((timestamp - ended_game.start_time).total_seconds())
            ended_game.in_game = False
            member.activity_info[game] = ended_game
        u_data[member.str_id] = member
    u_data.commit()


# handler method for any open times for bad shutdowns
# used on init if shutdown = False (bad shutdown, assume users still in_channel/in_game)
# if a running_since values was not able to be loaded, won't set manual leave time and will lose some time info
def on_bad_shutdown():
    # create list of members in channel and members in game
    members_in_channel = [x for x in u_data.values() if x.in_channel]
    members_in_game = [x for x in u_data.values() if len(x.current_activities)]
    if load_running_since():
        print('cleaning up users who were left as in channel (bad shutdown)')
        logging.warning('cleaning up users who were left as in channel (bad shutdown)')
        man_leave_time = bot_stats['running_since']
        for member in members_in_game:
            for game in member.current_activities:
                ended_game = member.activity_info[game]
                ended_game.update_end_time(man_leave_time)
                ended_game.total_time += ((man_leave_time - ended_game.start_time).total_seconds())
                ended_game.in_game = False
                member.activity_info[game] = ended_game
            u_data[member.str_id] = member
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


# returns a collective timesummary for users spent in each voice channel
# only works in guild
def get_guild_stats(message):
    increment_commands_run()
    mem = read_member(message.author)
    total_time = 0.0
    ret_str = 'User voice channel activity in guild \"{0}\"\n'.format(message.guild.name)
    unique_users = []
    for ch in message.guild.voice_channels:
        matching_users = [x for x in u_data.values() if str(ch.id) in x.channel_info]
        this_channel = 0.0
        if len(matching_users):
            active_users = 0
            for items in matching_users:
                if items.id not in unique_users:
                    # keeping track of the unique users who spent time in voice channels
                    unique_users.append(items.id)

                this_channel += items.channel_info[str(ch.id)].get_total_time_in_channel()
                active_users += 1
            plural = ''
            if active_users > 1:
                plural = 's'
            ret_str += '{0} - {1} collective time wasted by {2} user{3}.\n'.format(ch.mention, format_seconds(this_channel), str(active_users), plural)
        total_time += this_channel
    plural = ''
    if len(unique_users) > 1:
        plural = 's'
    ret_str += 'Total time spent in voice channels by {0} unique user{1}: {2}\n'.format(str(len(unique_users)), plural, format_seconds(total_time))
    ret_str += 'Collecting data since: {0}'.format((g_data[str(message.guild.id)].creation_time).in_tz(mem.pref_tz))
    return ret_str


# calculates timespent for user in all tracked guilds
def get_full_timesummary(message):
    increment_commands_run()
    ret_str = ''
    member_id = str(message.author.id)
    log_str = 'recieved ' + c_prefix + 'timespent (full timesummary) command from \"{0}\" DMChannel'.format(message.author.display_name)
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
        # Loop through sorted channel names
        for ch in chan_info:
            # get base time in channel
            time_in_channel = ch.get_total_time_in_channel()
            # add time information to time summary
            ch_summary = '{0} - {1}\n'.format(ch.mention, format_seconds(time_in_channel))
            ret_str += ch_summary
        if not len(chan_info):
            ret_str += 'No data found for guild\n'
        else:
            data_since = 'Data collected since: {0}\n'.format((member.creation_time).in_tz(member.pref_tz))
            ret_str += data_since
    return ret_str


def get_current_game_time(message):
    increment_commands_run()
    member = read_member(message.author)
    if member is None:
        return
    if len(member.activity_info):
        current_games = [x for x in member.activity_info.values() if x.in_game]
        if len(current_games):
            return_str = '{0}\'s current games:\n'.format(message.author.display_name)
            for game in (sorted(current_games, key=operator.attrgetter('name'))):
                return_str += '{0} - {1}\n'.format(str(game.name), format_seconds(game.get_total_time_in_game()))
            return return_str
        return '{0} has no current game.\n'.format(message.author.display_name)


def get_game_time(message):
    increment_commands_run()
    member = read_member(message.author)
    if member is None:
        return
    # check if there is any activity_info
    if len(member.activity_info):
        return_str = '{0}\'s total time spent in game:\n'.format(message.author.display_name)
        #(sorted(member.activity_info.values(), key=operator.attrgetter('name')))
        for game in (sorted(member.activity_info.values(), key=operator.attrgetter('name'))):
            return_str += '{0} - {1}\n'.format(str(game.name), format_seconds(game.get_total_time_in_game()))
        return return_str
    return 'No game data found for {0}'.format(message.author.display_name)


def get_guild_game_time(message):
    increment_commands_run()
    guild_activities = SortedDict()
    for mem in [x for x in message.guild.members if not x.bot]:
        this_mem = read_member(mem)
        if this_mem is None:
            pass
        else:
            for activity in this_mem.activity_info.keys():
                if activity not in guild_activities.keys():
                    guild_activities[activity] = 0
                guild_activities[activity] += this_mem.activity_info[activity].get_total_time_in_game()
    return_str = 'Activity summary for guild \"{0}\":\n'.format(message.guild.name)
    for key in guild_activities.keys():
        return_str += '{0} - {1}\n'.format(key, format_seconds(guild_activities[key]))
    return return_str


# calculates time_spent when passed a message obj
# returns result as string
def get_timesummary(message):
    increment_commands_run()
    guild_id = str(message.guild.id)
    member_id = str(message.author.id)
    log_str = 'recieved ' + c_prefix + 'timespent command from \"{0}\" in guild \"{1}\"'.format(message.author.display_name, message.guild.name)
    print(log_str)
    logging.info(log_str)
    no_data_str = 'No voice channel data found for \"{0}\" in guild \"{1}\"'.format(message.author.display_name, message.guild.name)
    # first check if we have any data on user
    if str(member_id) not in u_data.keys():
        return no_data_str
    # member object we will use
    member = u_data[str(member_id)]
    # start creating response string
    time_summary = '{0}\'s summary of time spent in voice channels in \"{1}\":\n'.format(member.display_name, message.guild.name)

    # filter only voice channels from guild where message was sent
    guild_channels = [x for x in member.channel_info.values() if x.guild_id == message.guild.id]
    if not len(guild_channels):
        return no_data_str
    # alphabetically sort guild channels
    chan_info = sorted(guild_channels, key=attrgetter('name'))
    # Loop through sorted channel names
    for ch in chan_info:
        # get base time in channel
        time_in_channel = ch.total_time
        if ch.in_channel:
            time_in_channel += ch.get_time_since_join()
        # add time information to time summary
        ch_summary = '{0} - {1}\n'.format(ch.mention, format_seconds(time_in_channel))
        time_summary = time_summary + ch_summary
    data_since = 'Data collected since: {0}\n'.format((member.guild_info[guild_id]).in_tz(member.pref_tz))
    time_summary = time_summary + data_since
    return time_summary


# method that resets one users stats in all tracked guilds
def reset_my_stats(message):
    increment_commands_run()
    logging.info('recieved ' + c_prefix + 'reset_user_stats command from {0} in DMChannel'.format(message.author.display_name))
    if str(message.author.id) in u_data.keys():
        member = u_data[str(message.author.id)]
        member.channel_info = {}
        member.creation_time = pendulum.now('UTC').replace(microsecond=0)
        u_data[str(message.author.id)] = member
        u_data.commit()


# method for resetting individual user stats
# returns string based on input message
def reset_user_stats(message):
    increment_commands_run()
    logging.info('recieved ' + c_prefix + 'reset_user_stats command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
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
        # OUTPUT LINE
        log_str = 'Removed user data for {0} in guild \"{1}\"'.format(member.display_name, message.guild.name)
        logging.info(log_str)
        return log_str


# method for resetting user stats for this guild - will continue to log data
def reset_guild_stats(message):
    if is_owner(message.author.id) or is_bot_admin(message.author.id) or is_local_admin(message.author.id):
        logging.info('recieved (VALID) ' + c_prefix + 'rem_guild_stats command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
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
        logging.info('recieved (INVALID) ' + c_prefix + 'rem_guild_stats command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        return 'Unathorized'


# helper method to format seconds into a readable time
# returns as a string, using pendulum duration.in_words()
def format_seconds(sec):
    return str((pendulum.duration(seconds=sec)).in_words())


# helper method to determine if owner (returns True if owner)
# checks if input id matches owner id - both converted to str
def is_owner(id):
    if str(id) == str(owner_id):
        return True
    return False


# helper method to determine if user is bot admin (stored in admins)
# checks if input id in admins list (returns True)
def is_bot_admin(id):
    if str(id) in admins:
        return True
    if str(id) == str(owner_id):
        return True
    return False


# will return true if bot admin or local admin (admin on guild)
def is_local_admin(id):
    str_id = str(id)
    if is_owner(str_id):
        return True
    if is_bot_admin(str_id):
        return True
    if is_owner(str_id):
        return True
    return False


# should handle everything for bot init
# either startup or $re_init command form owner
def on_bot_init():
    if not len(u_data):
        print('Looks like this is the first time initializing user stats')
        logging.info('Looks like this is the first time initializing user stats')
    if 'shutdown' in bot_stats.keys():
        if not bot_stats['shutdown']:
            if len(u_data):
                print('cleaning up from bad shutdown')
                logging.info('cleaning up from bad shutdown')
                on_bad_shutdown()
    bot_stats['shutdown'] = False


def bot_ready():
    log_str = 'We have logged in as {0.user}'.format(bot)
    print(log_str)
    logging.info(log_str)
    print('initializing guilds and channels')
    logging.info('initializing guilds and channels')
    print('now looping through current guilds')
    logging.info('now looping through current guilds')
    # gets list of guilds
    for g in bot.guilds:
        guild_join(g)
    # checks all visible members for current activities
    for member in bot.get_all_members():
        mem = read_member(member)
        if mem is not None:
            mem.process_activities(member, member)
            for act in member.activities:
                if type(act) is discord.Game:
                    mem.read_activity(act)
            u_data[mem.str_id] = mem
    update_bot_stats()
    u_data.commit()
    bot_stats.commit()
    global bkg_timer
    bkg_timer = Timer(60.0, update_bot_stats)
    bkg_timer.start()
    print('Finished init, starting timer for frequent bot_stats updates')
    logging.info('Finished init, starting timer for frequent bot_stats updates')


# method to help fully re_init bot and data
# will lose all tracked information!
def re_init(message):
    logging.info('recieved ' + c_prefix + 're_init command from {0}'.format(message.author.display_name))
    # clear all tracked data (will be re-initialized in on_bot_init)
    g_data.clear()
    u_data.clear()
    bot_stats.clear()
    g_data.commit()
    u_data.commit()
    bot_stats.commit()
    # remove admins file and reset to owner_id
    if os.path.exists('./admins.p'):
        os.remove('./admins.p')
    admins = []
    admins.append(str(owner_id))
    update_admins()
    # reset commands run and set shutdown = True
    bot_stats['commands_run'] = 0
    bot_stats['shutdown'] = True
    # cancels timer for re-init later
    global bkg_timer
    bkg_timer.cancel()
    bkg_timer = None
    logging.info('Canceled bkg_timer as part of re_init')
    # clear the log file??? why do we have logging in this function....
    # maybe change....
    clear_log_file()
    # finally, call on_bot_init
    bot_ready()


# clear log file
# maybe save it later?
def clear_log_file():
    with open('./activity_log.log', 'w'):
        pass


# function for shutting down bot
# cleans up all in channel connections and updates stats
def shutdown(message):
    increment_commands_run()
    logging.info('recieved ' + c_prefix + 'shutdown command from {0}'.format(message.author.display_name))
    # cancel bkg_timer, and set it to None
    global bkg_timer
    bkg_timer.cancel()
    bkg_timer = None
    print('Canceled timer, finishing shutdown procedures')
    logging.info('Canceled timer, finishing shutdown procedures')
    # make all users leave channel and update shutdown value
    set_leave_all()
    bot_stats['shutdown'] = True
    update_bot_stats()
    # close sqlitedict connections
    u_data.close()
    bot_stats.close()
    logging.info('closing client and quitting script')


def set_pref_tz(message):
    # split message into list and remove the $set_pref_tz
    arguments = message.content.split(' ')
    del arguments[0]
    # if there is another argument
    if len(arguments):
        # check if argument is a valid timezone name
        if arguments[0] in pendulum.timezones:
            increment_commands_run()
            # set and update pref_tz
            member = read_member(message.author)
            member.pref_tz = arguments[0]
            u_data[member.str_id] = member
            u_data.commit()
            return True
    # returns False if invalid for any reason
    return False


# returns the pref_tz of the author
def get_pref_tz(message):
    increment_commands_run()
    member = read_member(message.author)
    if member is None:
        return None
    return member.pref_tz


# leaves guild message was sent in
# for local_admin or owner
def leave_guild(message):
    # if user is authorized to run this command
    if is_owner(message.author.id) or is_local_admin(message.author.id):
        increment_commands_run()
        logging.info('recieved ' + c_prefix + 'leave_guild command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        # iterate through members in voice channels and adjust leave time
        for channels in message.guild.voice_channels:
            for members in channels.members:
                current_mem = read_member(members)
                if current_mem is None:
                    pass
                current_mem.adjust_leave_time(pendulum.now('UTC'))
                u_data[current_mem.str_id] = current_mem
        # commit changes, and remove guild from guild data
        u_data.commit()
        logging.info('finished closing voice channel information for members in {0}, leaving guild'.format(message.guild.name))
        guild_to_leave = g_data[str(message.guild.id)]
        guild_to_leave.in_guild = False
        g_data[str(message.guild.id)] = guild_to_leave
        update_bot_stats()
        return
    logging.warning('recieved INVALID ' + c_prefix + 'leave_guild command from {0}'.format(message.author.display_name))
    return

# ------------------------------------------------------------------------------------------------------------------------#
# -------------------------------------------------ALL EVENTS BELOW-------------------------------------------------------#
# ------------------------------------------------------------------------------------------------------------------------#
# ------------------------------------------------------------------------------------------------------------------------#
# ------------------------------------------------------------------------------------------------------------------------#


@bot.event
async def on_ready():
    bot_ready()


# called when bot is added to a guild
# just calls guild_join() method
@bot.event
async def on_guild_join(guild):
    guild_join(guild)


@bot.command()
async def say_hello(ctx):
    await ctx.send('hello!')


@bot.command()
async def timespend(ctx):
    if not ctx.message.guild:
        summary_str = 'Full voice channel time information:\n'
        summary_str += get_full_timesummary(ctx.message)
        await ctx.send(summary_str)
        return
    await ctx.send(get_timesummary(ctx.message))


@bot.command()
@commands.is_owner()
async def shutdown2(ctx):
    shutdown(ctx.message)
    await bot.close()
    exit()


@bot.command()
@commands.is_owner()
async def _add_admin(ctx):

    return

@bot.command()
@commands.is_owner()
async def reinit(ctx):
    re_init(ctx.message)

# event for all messages, handles commands
# look into using bot functionality from discord library
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # timespent command
    if message.content.startswith(c_prefix + 'timespent'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('Full voice channel time information:')
            await message.channel.send(get_full_timesummary(message))
            return
        await message.channel.send(get_timesummary(message))
        return

    # shutdown command
    if message.content.startswith(c_prefix + 'shutdown'):
        # handles all shutdown procedures
        shutdown(message)
        # closes client and exits
        await client.close()
        exit()
        return

    # add_admin
    # OWNER ONLY
    if message.content.startswith(c_prefix + 'add_admin'):
        add_admin(message)
        return

    # list_admins
    # OWNER OR BOT ADMIN
    if message.content.startswith(c_prefix + 'list_admins'):
        await message.author.send(list_admins(message))

    # rem_admin
    # OWNER ONLY
    if message.content.startswith(c_prefix + 'rem_admin'):
        remove_admin(message)
        return

    # reset_guild_stats
    # LOCAL ADMIN, BOT ADMIN, OR OWNER
    if message.content.startswith(c_prefix + 'reset_guild_stats'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('This command needs to be sent from a guild.')
            return
        await message.channel.send(reset_guild_stats(message))
        guild_join(message.guild)
        return

    # reset_user_stats
    if message.content.startswith(c_prefix + 'reset_user_stats'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('Are you sure you want to remove all user stats?')
            await message.channel.send('Send \"CONFIRM\" to confirm.')

            def check(m):
                return m.content == 'CONFIRM'
            await client.wait_for('message', check=check)
            reset_my_stats(message)
            return
        reset_user_stats(message)
        return

    # botstats
    if message.content.startswith(c_prefix + 'bot_stats'):
        await message.channel.send(get_bot_stats(message))
        return

    # commands
    if message.content.startswith(c_prefix + 'commands'):
        await message.author.send(get_commands(message))
        return

    # reset_commands_run
    # OWNER ONLY
    if message.content.startswith(c_prefix + 'reset_commands_run'):
        reset_commands_run(message)
        return

    # re_init
    # OWNER ONLY
    if message.content.startswith(c_prefix + 're_init'):
        re_init(message)
        return

    # set_pref_tz
    if message.content.startswith(c_prefix + 'set_pref_tz'):
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

    # get_pref_tz
    if message.content.startswith(c_prefix + 'get_pref_tz'):
        await message.author.send('Your current preferred timezone is set to {0}'.format(get_pref_tz(message)))
        return

    # leave_guild
    if message.content.startswith(c_prefix + 'leave_guild'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('This command needs to be sent from a guild channel.')
            return
        leave_guild(message)
        await message.channel.send('No longer tracking voice channel activity. Bye!')
        await message.guild.leave()
        return

    if message.content.startswith(c_prefix + 'guild_stats'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('This command needs to be sent from a guild channel.')
            return
        await message.channel.send(get_guild_stats(message))
        return

    if message.content == str(c_prefix + 'gametime current'):
        await message.channel.send(get_current_game_time(message))
        return

    if message.content.startswith(c_prefix + 'gametime'):
        await message.channel.send(get_game_time(message))
        return

    if message.content.startswith(c_prefix + 'guild_games'):
        if type(message.channel) is discord.DMChannel:
            await message.channel.send('This command needs to be sent from a guild channel.')
            return
        await message.channel.send(get_guild_game_time(message))


# for voice state updates
# any time a member leaves or joins a voice channel
@bot.event
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


# for tracking activities
@client.event
async def on_member_update(before, after):
    current_member = read_member(before)
    if current_member is None:
        return
    current_member.process_activities(before, after)
    u_data[current_member.str_id] = current_member
    u_data.commit()
    return


on_bot_init()
bot.run(TOKEN, bot=True, reconnect=True)

#client.run(TOKEN)
