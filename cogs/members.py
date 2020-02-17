import asyncio
import globals
import logging
from discord.ext import commands


class MembersCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # test sayhello command
    @commands.command()
    async def sayhello(self, ctx):
        '''Simple hello world!'''
        globals.increment_commands_run()
        await ctx.send("hello world! 2000")

def setup(bot):
    bot.add_cog(MembersCog(bot))
