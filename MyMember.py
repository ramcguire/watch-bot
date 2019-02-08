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
        self.activity_info = {}
        self.current_activities = []
        self.channel_info = {}
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

    # returns string of datetime since first seen anywhere
    def get_creation_time(self):
        return self.creation_time

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
            if current_channel.str_id not in self.channel_info.keys():
                print('Adding %s to known channels for %s' % (current_channel.name, self.display_name))
                logging.info('Adding %s to known channels for %s' % (current_channel.name, self.display_name))
                current_channel.set_join_channel()
                self.channel_info[current_channel.str_id] = current_channel
                self.in_channel = True
            else:
                a_channel = self.channel_info[current_channel.str_id]
                a_channel.set_join_channel()
                self.channel_info[current_channel.str_id] = a_channel
            self.in_channel = True
            print('%s joined channel %s (known: %s)' % (self.display_name, after.name, str(len(self.channel_info.keys()))))
            logging.info('%s joined channel %s (known: %s)' % (self.display_name, after.name, str(len(self.channel_info.keys()))))
            self.print_known_channels()
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

    # beginning actiivty tracking
    def set_current_activity(self, before, after):
        # make list of before/after activity names to compare
        # filter out all activities that aren't game
        time_stamp = pendulum.now('UTC')
        before_act = []
        before_name = []
        after_act = []
        after_name = []
        for act in before.activities:
            if type(act) is discord.Game:
                before_act.append(act)
                before_name.append(act.name)
        for act in after.activities:
            if type(act) is discord.Game:
                after_act.append(act)
                after_name.append(act.name)
        # check if before/after are the same
        if sorted(after_name) == sorted(before_name):
            print('ignoring member update, activities are the same')
            logging.info('ignoring member update, activities are the same')
            return

        # starting an activity
        for act in [x for x in after_act if x.name not in before_name]:
            new_act = MyGame(act)
            if act.name not in self.activity_info.keys():
                print('new activity found for {0} adding to current activities and getting start time'.format(after.display_name))
                logging.info('new activity found for {0} adding to current activities and getting start time'.format(after.display_name))
                self.activity_info[act.name] = new_act
                self.current_activities.append(act.name)
            if act.name in self.activity_info.keys():
                # if not already in activity, update start time
                # ignores if already in_game
                if not self.activity_info[act.name].in_game:
                    print('activity {0} started'.format(act))
                    logging.info('activity {0} started'.format(act))
                    self.current_activities.append(act.name)
                    self.activity_info[act.name].update_start_time(new_act.start_time)

        # ending an activity
        for act in [x for x in before_act if x.name not in after_name]:
            if act.name in self.current_activities:
                # only end if already in_game
                if self.activity_info[act.name].in_game:
                    print('activity {0} ended'.format(act.name))
                    logging.info('activity {0} ended'.format(act.name))
                    self.current_activities.remove(act.name)
                    self.activity_info[act.name].update_end_time(time_stamp)
        return

    # sets a leave_time for every game still in game
    def set_activity_end_time(self, leave_time):
        for game in [x for x in self.activity_info.values() if x.in_game]:
            game.update_end_time(leave_time)
