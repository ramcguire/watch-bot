# contains all member information
# includes dict of known channels (keys are channel id in string, values are MyChannel instance)
# also includes status information like in_channel, and activity (to be used later for activity time tracking)
# guild_info is a dict (keys are guild id in string, values are datetime[pendulum] of when member was first spotted in guild voice channel)
import discord
import logging
from MyActivity import MyGame
from MyChannel import MyChannel
import pendulum


class MyMember():
    def __init__(self, member):
        self.id = member.id
        self.str_id = str(member.id)
        self.display_name = member.display_name
        self.creation_time = pendulum.now('UTC').replace(microsecond=0)
        # keys are str(activity_name), values are MyGame obj
        self.activity_info = {}
        # should contain all activties that are in_game
        self.current_activities = set()
        # keys are str(channel_id), values are MyChannel obj
        self.channel_info = {}
        # keys are str(guild_id), values are MyGuild obj
        self.guild_info = {}
        self.pref_tz = 'UTC'
        self.in_channel = False
        if member.voice is not None:
            self.in_channel = True
        if self.in_channel:
            self.current_channel_id = str(member.voice.channel.id)
        for activity in member.activities:
            if type(activity) is discord.Game:
                if activity.name not in self.activity_info.keys():
                    self.current_activities.append(activity.name)
                    current_activity = MyGame(activity)
                    self.activity_info[activity.name] = current_activity

    def get_guild_time(self, guild_id):
        if str(guild_id) in self.guild_info:
            return self.guild_info[str(guild_id)].replace(microsecond=0)

    # returns channel_info for specified channel id
    def get_channel_info(self, id):
        if str(id) not in self.channel_info.keys():
            return None
        return self.channel_info[str(id)]

    # sets a timestamp at current time to help track timing
    def set_timestamp(self):
        self.timestamp = pendulum.now('UTC')

    # helps determine if channel is already known for the user
    def is_channel_known(self, channel_id):
        if str(channel_id) in self.channel_info.keys():
            return True
        return False

    # returns seconds since timestamp
    def calc_timestamp(self):
        return (pendulum.now('UTC') - self.timestamp).total_seconds()

    # helper method to check guild association
    def guild_status(self, guild_id):
        if str(guild_id) not in self.guild_info.keys():
            self.guild_info[str(guild_id)] = pendulum.now('UTC')

    # helps adjust leave time on last known in_channel value
    def adjust_leave_time(self, manual_datetime):
        self.channel_info[self.current_channel_id].in_channel = False
        self.channel_info[self.current_channel_id].set_man_leave(manual_datetime)
        self.channel_info[self.current_channel_id].update_time_spent()
        self.in_channel = False
        self.current_channel = None

    # helper method to set the current channel
    # sets channel as VoiceChannel object
    def set_current_channel(self, before, after):
        # if channels didn't change, ignore
        if before == after:
            return
        # case for no voice channel -> voice channel
        if before is None and after is not None:
            # check if joining afk channel, so we can ignore
            if after.guild.afk_channel == after:
                return
            current_channel = MyChannel(after)
            self.current_channel_id = current_channel.str_id
            self.current_channel = MyChannel(after)
            self.guild_status(str(after.guild.id))
            self.current_channel.set_join_channel()
            # add channel id to known channels
            if current_channel.str_id not in self.channel_info.keys():
                print('Adding %s to known channels for %s' % (current_channel.name, self.display_name))
                logging.info('Adding %s to known channels for %s' % (current_channel.name, self.display_name))
                current_channel.set_join_channel()
                self.channel_info[current_channel.str_id] = current_channel
                self.in_channel = True
            # otherwise, appends required information
            else:
                a_channel = self.channel_info[current_channel.str_id]
                a_channel.set_join_channel()
                self.channel_info[current_channel.str_id] = a_channel
            self.in_channel = True
            print('%s joined channel %s (known: %s)' % (self.display_name, after.name, str(len(self.channel_info.keys()))))
            logging.info('%s joined channel %s (known: %s)' % (self.display_name, after.name, str(len(self.channel_info.keys()))))
            return

        # case for voice channel -> no voice channel
        if before is not None and after is None:
            # checks if leaving afk channel to prevent errors
            if before.guild.afk_channel == before:
                return
            self.channel_info[str(before.id)].set_leave_channel()
            self.channel_info[str(before.id)].update_time_spent()
            self.channel_info[str(before.id)].in_channel = False
            self.in_channel = False
            self.current_channel_id = None
            print('%s left channel %s (known: %s)' % (self.display_name, before.name, str(len(self.channel_info.keys()))))
            logging.info('%s left channel %s (known: %s)' % (self.display_name, before.name, str(len(self.channel_info.keys()))))
            self.print_known_channels()
            return

        # case for channel -> channel
        if before is not None and after is not None:
            self.guild_status(str(after.guild.id))
            # checks if previous channel was known to avoid any issues
            # if previous channel is unknown, ignores before channel time update
            if str(before.id) in self.channel_info.keys():
                self.channel_info[str(before.id)].set_leave_channel()
                self.channel_info[str(before.id)].update_time_spent()
            # check if new channel is afk channel
            if after.guild.afk_channel == after:
                logging.info('{0} is now in an afk channel, ignoring time spent in afk'.format(self.display_name))
                print('{0} is now in an afk channel, ignoring time spent in afk'.format(self.display_name))
                return
            current_channel = MyChannel(after)

            if current_channel.str_id not in self.channel_info.keys():
                print('Adding %s to known channels for %s' % (current_channel.name, self.display_name))
                logging.info('Adding %s to known channels for %s' % (current_channel.name, self.display_name))
                current_channel.set_join_channel()
                self.channel_info[current_channel.str_id] = current_channel
            if current_channel.str_id in self.channel_info.keys():
                self.channel_info[current_channel.str_id].set_join_channel()
            self.current_channel_id = current_channel.str_id
            print('%s changed to channel %s (known: %s)' % (self.display_name, after.name, str(len(self.channel_info.keys()))))
            logging.info('%s changed to channel %s (known: %s)' % (self.display_name, after.name, str(len(self.channel_info.keys()))))
            return

    # compares if input id matches current id
    # returns TRUE if id's match
    def compare_id(self, id):
        if self.id == id:
            return True
        return False

    def get_known_channels(self):
        return self.channel_info.keys()

    def print_known_channels(self):
        print('Current known channels for %s:' % self.display_name)
        for ch in self.get_known_channels():
            print(str(ch))

    # returns display_name as string
    def get_display_name(self):
        return str(self.display_name)

    # prints display_name
    def print_display_name(self):
        print(self.display_name)

    # checks if channel id is in known channels
    def check_known_channels(self, id):
        return (id in self.channel_info.keys())

    def read_activity(self, activity):
        if activity.name in self.activity_info.keys():
            self.activity_info[activity.name].update_start_time(pendulum.instance(activity.start, 'UTC'))
        else:
            new_act = MyGame(activity)
            self.activity_info[activity.name] = new_act

    # sets a leave_time for every game still in game
    def set_activity_end_time(self, leave_time):
        for game in [x for x in self.activity_info.values() if x.in_game]:
            game.update_end_time(leave_time)

    def process_activities(self, before, after):
        timestamp = pendulum.now('UTC')
        before_set = set()
        after_set = set()
        # populate both sets
        if before is not None:
            for act in before.activities:
                before_set.add(act.name)
        if after is not None:
            for act in after.activities:
                after_set.add(act.name)

        # check if activities haven't been instantiated yet
        if before is not None:
            new_activities = [x for x in before.activities if x.name not in self.activity_info]
            for act in new_activities:
                self.current_activities.add(act.name)
                new_act = MyGame(act.name)
                new_act.update_start_time(pendulum.instance(act.start, 'UTC'))
                self.activity_info[act.name] = new_act

        if after is not None:
            new_activities = [x for x in after.activities if x.name not in self.activity_info]
            for act in new_activities:
                self.current_activities.add(act.name)
                new_act = MyGame(act.name)
                new_act.update_start_time(pendulum.instance(act.start, 'UTC'))
                self.activity_info[act.name] = new_act

        # for ending activity
        for ended_act in [x for x in before_set if x not in after_set]:
            # end the activity, and update total_time
            ending = self.activity_info[ended_act]
            ending.update_end_time(timestamp)
            ending.total_time += ((timestamp - ending.start_time).total_seconds())
            ending.in_game = False
            self.activity_info[ended_act] = ending
            self.current_activities.remove(ended_act)

        # for starting an activity
        for started_act in (after_set - before_set):
            self.current_activities.add(started_act)
            if started_act not in self.activity_info:
                new_act = MyGame(started_act)
                new_act.update_start_time(timestamp)
                self.activity_info[started_act] = new_act
            else:
                self.activity_info[started_act].update_start_time(timestamp)
