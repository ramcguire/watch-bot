#class to contain guild information
#id is guild id
#guild_name is string of guild name
#channels is list of voice channels (not tracking text channels)


class MyGuild():
    def __init__(self, guild):
        self.id = guild.id
        self.str_id = str(guild.id)
        self.name = guild.name
        self.channels = guild.voice_channels

    #returns list of voice channels
    def return_voice_channels(self):
        if self.channels is not None:
            return self.channels
        return None

    def print_voice_channels(self):
        if self.channels is not None:
            for ch in self.channels:
                print(ch.name)
        else:
            print('No voice channels.')
