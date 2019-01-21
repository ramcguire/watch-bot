#class to contain channel information/timing
#new MyChannel is created every time a member joins a channel
#channel information is stored in MyMember channel_info and known_channels
#doesn't contain guild channel information
import logging
import pendulum


class MyChannel():
    def __init__(self, channel):
        self.guild_id = channel.guild.id
        self.id = channel.id
        self.str_id = str(channel.id)
        self.name = channel.name
        self.mention = channel.mention
        self.in_channel = True
        self.time_spent = []
        self.total_time = 0

    #returns TRUE if channel id's match
    def compare_channel_id(self, id):
        if self.id == id:
            return True
        return False

    def get_channel_id(self):
        return self.id

    #appends time_spent information for current channel (used in MyUser)
    #is a tuple of start datetime[pendulum], end datetime[pendulum], seconds spent in channel
    #resets join/leave time to None
    def update_time_spent(self):
        if self.leave_time is None or self.join_time is None:
            print('invalid update_time_spent() call')
            logging.warning('invalid update_time_spent() call')
            return
        time_spent = self.calc_time_in_channel()
        if time_spent < 0:
            print('found negative time_spent value, ignoring...')
            logging.warning('found negative time_spent value, ignoring...')
            return
        group = (self.join_time, self.leave_time)
        self.total_time += time_spent
        self.time_spent.append(group)
        self.join_time = None
        self.leave_time = None

    #helper method to set timestamp of joining the channel
    def set_join_channel(self):
        self.join_time = pendulum.now('UTC')
        self.in_channel = True

    #helper method to set timestamp of leaving the channel
    def set_leave_channel(self):
        self.leave_time = pendulum.now('UTC')
        self.in_channel = False

    #manually sets leave time
    #used if a member is initialized when in_channel = True
    #will set the leave time as last known running_since time
    def set_man_leave(self, manual_datetime):
        self.leave_time = manual_datetime
        self.update_time_spent()

    #returns seconds since timestamp
    def calc_time_in_channel(self):
        return (self.leave_time - self.join_time).total_seconds()

    #returns seconds since joining voice channel
    def get_time_since_join(self):
        if self.join_time is None:
            return 0.0
        return (pendulum.now('UTC') - self.join_time).total_seconds()

    #helps return total time in channel (including offset)
    def get_total_time_in_channel(self):
        time = self.total_time
        if self.in_channel:
            time += self.get_time_since_join()
        return time
