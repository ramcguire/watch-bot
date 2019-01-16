#class to contain channel information/timing
#channel information is stored in MyMember channel_info and known_channels
#doesn't contain guild channel information
import pendulum

class MyChannel():
    def __init__(self, channel):
        self.guild_id = channel.guild.id
        self.id = channel.id
        self.str_id = str(channel.id)
        self.name = channel.name
        self.mention = channel.mention
        self.time_spent = []

    #returns guild object this channel belongs to
    def get_guild(self):
        return self.guild

    #returns TRUE if channel id's match
    def compare_channel_id(self, id):
        if self.id == id:
            return True
        return False

    def get_channel_id(self):
        return self.id

    def get_channel_name(self):
        return self.name

    #appends time_spent information for current channel (used in MyUser)
    #is a tuple of start datetime[pendulum], end datetime[pendulum], seconds spent in channel
    #resets join/leave time to None
    def update_time_spent(self):
        if self.join_time is None:
            print('join_time is None')
        if self.leave_time is None:
            print('leave_time is None')
        if self.leave_time is None or self.join_time is None:
            print('invalid update_time_spent() call')
            return
        group = (self.join_time, self.leave_time, self.calc_time_in_channel())
        self.time_spent.append(group)
        self.join_time = None
        self.leave_time = None

    #helper method to set timestamp of joining the channel
    def set_join_channel(self):
        self.join_time = pendulum.now('UTC')

    #helper method to set timestamp of leaving the channel
    def set_leave_channel(self):
        self.leave_time = pendulum.now('UTC')

    #manually sets leave time
    #used if a member is initialized when in_channel = True
    #will set the leave time as last known running_since time
    def set_man_leave(self, manual_datetime):
        self.leave_time = manual_datetime

    #returns seconds since timestamp
    def calc_time_in_channel(self):
        return (self.leave_time - self.join_time).total_seconds()

    #returns total time in channel (in seconds)
    def get_time_in_channel(self):
        sum = 0.0
        for timestamps in self.time_spent:
            sum += timestamps[2]
        return sum

    #returns seconds since joining voice channel
    def get_time_since_join(self):
        if self.join_time is None:
            return 0.0
        return (pendulum.now('UTC') - self.join_time).total_seconds()
