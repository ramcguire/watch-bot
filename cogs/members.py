import asyncio
import globals
from discord.ext import commands


class MembersCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='sayhello')
    async def sayhello(self, ctx):

        '''Simple hello world!'''
        globals.increment_commands_run()
        await ctx.send("hello world!")



def setup(bot):
    bot.add_cog(MembersCog(bot))
