#class to contain guild information
#id is guild id
#name is string of guild name
#voice_channels keeps track of guild voice channel ids


class MyGuild():
    def __init__(self, guild):
        self.id = guild.id
        self.str_id = str(guild.id)
        self.name = guild.name
        self.in_guild = True
        self.voice_channels = []

    #helps iterate through a guild to make sure we have all voice channels represented
    def update_voice_channels(self, guild):
        for ch in guild.voice_channels:
            if str(ch.id) not in self.voice_channels:
                self.voice_channels.append(str(ch.id))
