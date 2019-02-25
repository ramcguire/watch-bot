import discord
from discord.ext import commands


class MembersCog:
    def __init__(self, bot):
        self.bot = bot
bot = commands.bot(command_prefix='!')

@command.command(name='sayhello')



def setup(bot):
    bot.add_cog(MembersCog(bot))
