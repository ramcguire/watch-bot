import discord
import globals
import logging

import operator
import os
import pendulum
import pickle
import traceback, sys

from discord.ext import commands
from sortedcontainers import SortedDict

from threading import Timer

from MyGuild import MyGuild
from MyMember import MyMember
from operator import attrgetter


globals.init()

bot = commands.Bot(command_prefix=globals.c_prefix, owner_id=globals.owner_id)


client = discord.Client()

# resets commands_run stat
def _reset_commands_run():
    globals.bot_stats['commands_run'] = 0
    globals.bot_stats.commit()

# updates admin list and dumps to file
def update_admins():
    print('updating admin list')
    logging.info('updating admin list')
    pickle.dump(globals.admins, open('./admins.p', 'wb'))


# adds all members mentioned in message to admin file
def _add_admin(message):
    # only iterates through members not already in admin list
    list_new_admins = [x for x in message.mentions if str(x.id) not in globals.admins]
    for member in list_new_admins:
        new_admin = read_member(member)
        logging.info('adding {0} to admins list'.format(new_admin.display_name))
        globals.admins.append(new_admin.str_id)
    if not len(list_new_admins):
        update_admins()


# updates running_since file (pendulum obj)
# does not commit, so need to commit if used outside of update_bot_stats()
def update_running_since():
    globals.bot_stats['running_since'] = pendulum.now('UTC')


# updates all bot stats
# uses bkg_timer for regular updates (currently every 60s)
def update_bot_stats():
    active_guilds = [x for x in globals.g_data.values() if x.in_guild]
    guild_count = len(active_guilds)
    user_count = len(globals.u_data)
    globals.bot_stats['guild_count'] = guild_count
    globals.bot_stats['user_count'] = user_count
    globals.bot_stats['running_since'] = pendulum.now('UTC')
    print('updating bot stats')
    logging.info('updating bot stats')
    globals.bot_stats.commit()


# loads running_since if backup exists
# otherwise sets running_since as current_time
def load_running_since():
    if 'running_since' in globals.bot_stats.keys():
        print('found valid running_since in bot_stats')
        logging.info('found valid running_since in bot_stats')
        return True
    else:
        print('created new running_since file')
        logging.warning('created new running_since file')
        globals.bot_stats['running_since'] = pendulum.now('UTC')
        globals.bot_stats.commit()
        return False


# helper method to add a new member to user_instance
# called by read_member if member not found
def add_new_member(member):
    current_member = MyMember(member)
    globals.u_data[current_member.str_id] = current_member
    log_str = 'added new member {0}'.format(current_member.display_name)
    print(log_str)
    logging.info(log_str)
    globals.u_data.commit()
    return globals.u_data[current_member.str_id]


# handler for member reading
# checks if member is already known, if not, adds new member
# returns member object to be worked on
def read_member(member):
    if str(member.id) not in globals.u_data.keys():
        if not member.bot:
            new_mem = add_new_member(member)
            #new_mem.process_activities()
            return globals.u_data[new_mem.str_id]
        else:
            print('found bot {0} in read_member: ignoring'.format(member.display_name))
            logging.info('found bot user in read_member: ignoring')
            return None
    # returns member object
    return globals.u_data[str(member.id)]


# handler for all guild joins/init
# runs on guild join and initialization
# handles all users in a voice channel for specified guild
def guild_join(guild):
    new_guild = MyGuild(guild)
    if new_guild.str_id not in globals.g_data.keys():
        globals.g_data[new_guild.str_id] = new_guild
    else:
        current_guild = globals.g_data[new_guild.str_id]
        current_guild.in_guild = True
        globals.g_data[new_guild.str_id] = current_guild

    log_str = 'initializing voice channels in guild \"{0}\"'.format(new_guild.name)
    print(log_str)
    logging.info(log_str)
    current_guild = globals.g_data[str(guild.id)]
    for ch in guild.voice_channels:
        current_guild.update_voice_channels(guild)
        for mem in ch.members:
            current_member = read_member(mem)
            if current_member is None:
                pass
            else:
                current_member.set_current_channel(None, ch)
                globals.u_data[current_member.str_id] = current_member
    globals.g_data.commit()
    globals.u_data.commit()


# helper method to update all members in channels
# used before shutting down/updating
# updates time for all users currently in channels
def set_leave_all():
    timestamp = pendulum.now('UTC')
    members_in_channel = [x for x in globals.u_data.values() if x.in_channel]
    for member in members_in_channel:
        member.adjust_leave_time(timestamp)
        globals.u_data[member.str_id] = member
    globals.u_data.commit()


# handler method for any open times for bad shutdowns
# used on init if shutdown = False (bad shutdown, assume users still in_channel)
# if a running_since values was not able to be loaded, won't set manual leave time and will lose some time info
def on_bad_shutdown():
    # create list of members in channel and members in game
    members_in_channel = [x for x in globals.u_data.values() if x.in_channel]
    if load_running_since():
        print('cleaning up users who were left as in channel (bad shutdown)')
        logging.warning('cleaning up users who were left as in channel (bad shutdown)')
        man_leave_time = globals.bot_stats['running_since']
        for members in members_in_channel:
            members.adjust_leave_time(man_leave_time)
            globals.u_data[members.str_id] = members
    else:
        log_str = 'invalid running_since'
        print(log_str)
        logging.warning(log_str)
        for members in members_in_channel:
            members.in_channel = False
            globals.u_data[members.str_id] = members
    globals.u_data.commit()


# returns a collective timesummary for users spent in each voice channel
# only works in guild
def get_guild_stats(message):
    mem = read_member(message.author)
    total_time = 0.0
    ret_str = 'User voice channel activity in guild \"{0}\"\n'.format(message.guild.name)
    unique_users = []
    for ch in message.guild.voice_channels:
        matching_users = [x for x in globals.u_data.values() if str(ch.id) in x.channel_info]
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
    ret_str += 'Collecting data since: {0}'.format((globals.g_data[str(message.guild.id)].creation_time).in_tz(mem.pref_tz))
    return ret_str


# calculates timespent for user in all tracked guilds
def get_full_timesummary(message):
    ret_str = ''
    member_id = str(message.author.id)

    log_str = 'recieved ' + globals.c_prefix + 'timespent (full timesummary) command from \"{0}\" DMChannel'.format(message.author.display_name)
    print(log_str)
    logging.info(log_str)

    if member_id not in globals.u_data.keys():
        return 'No voice channel data found for \"{0}\".'.format(message.author.display_name)

    member = globals.u_data[member_id]
    for guilds in member.guild_info.keys():
        ret_str += 'Guild: {0}\n'.format(globals.g_data[str(guilds)].name)
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

# calculates time_spent when passed a message obj
# returns result as string
def get_timesummary(message):
    guild_id = str(message.guild.id)
    member_id = str(message.author.id)
    log_str = 'recieved ' + globals.c_prefix + 'timespent command from \"{0}\" in guild \"{1}\"'.format(message.author.display_name, message.guild.name)
    print(log_str)
    logging.info(log_str)
    no_data_str = 'No voice channel data found for \"{0}\" in guild \"{1}\"'.format(message.author.display_name, message.guild.name)
    # first check if we have any data on user
    if str(member_id) not in globals.u_data.keys():
        return no_data_str
    # member object we will use
    member = globals.u_data[str(member_id)]
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
def _reset_user_stats(message):
    logging.info('recieved ' + globals.c_prefix + 'reset_user_stats command from {0} in DMChannel'.format(message.author.display_name))
    if str(message.author.id) in globals.u_data.keys():
        member = globals.u_data[str(message.author.id)]
        member.channel_info = {}
        member.creation_time = pendulum.now('UTC').replace(microsecond=0)
        globals.u_data[str(message.author.id)] = member
        globals.u_data.commit()


# method for resetting individual user stats
# returns string based on input message
def reset_user_stats(message):
    logging.info('recieved ' + globals.c_prefix + 'reset_user_stats command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
    this_guild = message.guild.id
    deletable = []
    if str(message.author.id) in globals.u_data.keys():
        member = globals.u_data[str(message.author.id)]
        for channels in member.channel_info.values():
            if this_guild == channels.guild_id:
                deletable.append(str(channels.str_id))
        for i in deletable:
            del member.channel_info[i]
        globals.u_data[member.str_id] = member
        globals.u_data.commit()
        # OUTPUT LINE
        log_str = 'Removed user data for {0} in guild \"{1}\"'.format(member.display_name, message.guild.name)
        logging.info(log_str)
        return log_str


# method for resetting user stats for this guild - will continue to log data
def reset_guild_stats(message):
    if is_owner(message.author.id) or is_bot_admin(message.author.id) or is_local_admin(message.author.id):
        logging.info('recieved (VALID) ' + globals.c_prefix + 'rem_guild_stats command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        print('removing all stats from guild \"{0}\"'.format(message.guild.name))
        deletable = []
        this_guild = message.guild.id
        for members in message.guild.members:
            if str(members.id) in globals.u_data.keys():
                member = globals.u_data[str(members.id)]
                for channels in member.channel_info.values():
                    if this_guild == channels.guild_id:
                        deletable.append(str(channels.str_id))
                for i in deletable:
                    del member.channel_info[i]
                globals.u_data[member.str_id] = member
        return 'Removing all user data for voice channels in this guild \"{0}\" and re-initializing.'.format(message.guild.name)
        globals.u_data.commit()
        guild_join(message.guild)
    else:
        logging.info('recieved (INVALID) ' + globals.c_prefix + 'rem_guild_stats command from {0} in guild \"{1}\"'.format(message.author.display_name, message.guild.name))
        return 'Unathorized'


# helper method to format seconds into a readable time
# returns as a string, using pendulum duration.in_words()
def format_seconds(sec):
    return str((pendulum.duration(seconds=sec)).in_words())


# helper method to determine if owner (returns True if owner)
# checks if input id matches owner id - both converted to str
def is_owner(id):
    if str(id) == str(globals.owner_id):
        return True
    return False


# helper method to determine if user is bot admin (stored in admins)
# checks if input id in admins list (returns True)
def is_bot_admin(id):
    if str(id) in globals.admins:
        return True
    if str(id) == str(globals.owner_id):
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
    if not len(globals.u_data):
        print('Looks like this is the first time initializing user stats')
        logging.info('Looks like this is the first time initializing user stats')
    if 'shutdown' in globals.bot_stats.keys():
        if not globals.bot_stats['shutdown']:
            if len(globals.u_data):
                print('cleaning up from bad shutdown')
                logging.info('cleaning up from bad shutdown')
                on_bad_shutdown()
    globals.bot_stats['shutdown'] = False


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
    update_bot_stats()
    globals.u_data.commit()
    globals.bot_stats.commit()
    global bkg_timer
    bkg_timer = Timer(60.0, update_bot_stats)
    bkg_timer.start()
    print('Finished init, starting timer for frequent bot_stats updates')
    logging.info('Finished init, starting timer for frequent bot_stats updates')


# method to help fully re_init bot and data
# will lose all tracked information!
def _re_init():
    globals.g_data.clear()
    globals.u_data.clear()
    globals.bot_stats.clear()
    globals.g_data.commit()
    globals.u_data.commit()
    globals.bot_stats.commit()
    # remove admins file and reset to globals.owner_id
    if os.path.exists('./admins.p'):
        os.remove('./admins.p')
    admins = []
    admins.append(str(globals.owner_id))
    update_admins()
    # reset commands run and set shutdown = True
    globals.bot_stats['commands_run'] = 0
    globals.bot_stats['shutdown'] = True
    # cancels timer for re-init later
    global bkg_timer
    bkg_timer.cancel()
    bkg_timer = None
    #finish up
    bot_ready()


# clear log file
# maybe save it later?
def clear_log_file():
    with open('./activity_log.log', 'w'):
        pass


# function for shutting down bot
# cleans up all in channel connections and updates stats
def shutdown_bot(message):
    # cancel bkg_timer, and set it to None
    global bkg_timer
    bkg_timer.cancel()
    bkg_timer = None
    print('Canceled timer, finishing shutdown procedures')
    # make all users leave channel and update shutdown status value
    set_leave_all()
    globals.bot_stats['shutdown'] = True
    update_bot_stats()
    # close sqlitedict connections
    globals.u_data.close()
    globals.bot_stats.close()


def set_pref_tz(message):
    # split message into list and remove the $set_pref_tz
    arguments = message.content.split(' ')
    del arguments[0]
    # if there is another argument
    if len(arguments):
        # check if argument is a valid timezone name
        if arguments[0] in pendulum.timezones:
            # set and update pref_tz
            member = read_member(message.author)
            member.pref_tz = arguments[0]
            globals.u_data[member.str_id] = member
            globals.u_data.commit()
            return True
    # returns False if invalid for any reason
    return False


# returns the pref_tz of the author
def get_pref_tz(message):
    member = read_member(message.author)
    if member is None:
        return None
    return member.pref_tz


# helper to leave_guild command, used to clean up data
def _leave_guild(message):
    # if user is authorized to run this command
    # iterate through members in voice channels and adjust leave time
    for channels in message.guild.voice_channels:
        for members in channels.members:
            current_mem = read_member(members)
            if current_mem is None:
                pass
            current_mem.adjust_leave_time(pendulum.now('UTC'))
            globals.u_data[current_mem.str_id] = current_mem
    # commit changes, and remove guild from guild data
    globals.u_data.commit()
    guild_to_leave = globals.g_data[str(message.guild.id)]
    guild_to_leave.in_guild = False
    globals.g_data[str(message.guild.id)] = guild_to_leave
    update_bot_stats()
    return

# ------------------------------------------------------------------------------------------------------------------------#
# -------------------------------------------------ALL EVENTS BELOW-------------------------------------------------------#
# ------------------------------------------------------------------------------------------------------------------------#
# ------------------------------------------------------------------------------------------------------------------------#
# ------------------------------------------------------------------------------------------------------------------------#

async def is_guild_admin(ctx):
    # if message was not sent from a guild return false
    if ctx.message.guild is None:
        return False
    # if author was bot owner or a guild administrator
    if ctx.message.author.is_owner():
        return True
    return ctx.message.author.permissions.administrator

async def is_text_channel(ctx):
    return type(ctx.message.channel) == discord.TextChannel

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
    globals.increment_commands_run()
    await ctx.send('hello!')


@bot.command()
async def timespent(ctx):
    globals.increment_commands_run()
    if not ctx.message.guild:
        summary_str = 'Full voice channel time information:\n'
        summary_str += get_full_timesummary(ctx.message)
        await ctx.send(summary_str)
        return
    await ctx.send(get_timesummary(ctx.message))

@bot.command()
@commands.is_owner()
async def _add_admin(ctx):
    globals.increment_commands_run()
    return

@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    # handles all shutdown procedures
    shutdown_bot(ctx.message)
    # closes client and exits
    await client.close()
    exit()
    return

@bot.command()
@commands.is_owner()
async def add_admin(ctx):
    globals.increment_commands_run()
    _add_admin(ctx.message)
    return

@bot.command()
@commands.is_owner()
async def remove_admin(ctx):
    list_rem_admins = [x for x in ctx.message.mentions if str(x.id) in globals.admins]
    for member in list_rem_admins:
        globals.admins.remove(str(member.id))
    if not len(list_rem_admins):
        update_admins()

@bot.command()
@commands.check(is_text_channel)
async def reset_guild_stats(ctx):
    globals.increment_commands_run()
    await ctx.message.channel.send(reset_guild_stats(ctx.message))
    guild_join(ctx.message.guild)
    return

@bot.command()
async def reset_user_stats(ctx):
    if type(ctx.message.channel) is discord.DMChannel:
        await ctx.message.channel.send('Are you sure you want to remove all user stats?')
        await ctx.message.channel.send('Send \"CONFIRM\" to confirm.')

        def check(m):
            return m.content == 'CONFIRM'
        await client.wait_for('message', check=check)
        globals.increment_commands_run()
        _reset_user_stats(ctx.message)
        return

@bot.command()
@commands.is_owner()
async def list_admins(ctx):
    globals.increment_commands_run()
    admin_list = 'List of current admins:\n'
    for admin in globals.admins:
        admin_list += '{0} - id: {1}\n'.format(globals.u_data[admin].display_name, admin)
    await ctx.message.author.send(admin_list)
    return

# need to fix this
@bot.command()
async def bot_stats(ctx):
    await ctx.message.channel.send(get_bot_stats(message))
    return

@bot.command()
@commands.is_owner()
async def reset_commands_run(ctx):
    _reset_commands_run()

@bot.command()
@commands.is_owner()
async def re_init(ctx):
    _re_init()

@bot.command()
@commands.check(is_text_channel)
@commands.check(is_guild_admin)
async def leave_guild(ctx):
    _leave_guild(ctx.message)
    await ctx.message.channel.send('No longer tracking voice channel activity. Bye!')
    await ctx.message.guild.leave()
    
@bot.command()
@commands.check(is_text_channel)
async def guild_stats(ctx):
    await ctx.message.channel.send(get_guild_stats(ctx.message))



# event for all messages, handles commands
# TODO: replace all commands with @bot.command() decorator
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # set_pref_tz
    if message.content.startswith(globals.c_prefix + 'set_pref_tz'):
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
    if message.content.startswith(globals.c_prefix + 'get_pref_tz'):
        await message.author.send('Your current preferred timezone is set to {0}'.format(get_pref_tz(message)))
        return

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
    globals.u_data[current_member.str_id] = current_member
    globals.u_data.commit()
    return

# cogs setup
initial_extensions = ['cogs.members']

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()


on_bot_init()
bot.run(globals.TOKEN, bot=True, reconnect=True)


