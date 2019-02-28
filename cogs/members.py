import asyncio
import globals
import logging
from discord.ext import commands


class MembersCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # test sayhello command
    @commands.command(name='sayhello')
    async def sayhello(self, ctx):

        '''Simple hello world!'''
        globals.increment_commands_run()
        await ctx.send("hello world!")

    # prints current stats about bot
    @commands.command(name='bot_stats')
    async def _get_bot_stats(self, ctx):

        '''Prints stats about bot'''
        # increment commands count
        globals.increment_commands_run()
        log_str = 'recieved ' + globals.c_prefix + 'bot_stats command from {0}'.format(ctx.message.author.display_name)
        print(log_str)
        logging.info(log_str)
        # construct response
        ret_str = 'This bot is currently in {0} guilds, tracking {1} member(s).\n'.format(globals.bot_stats['guild_count'], globals.bot_stats['user_count'])
        ret_str += 'This bot has processed a total of {0} command(s).'.format(globals.bot_stats['commands_run'])
        await ctx.send(ret_str)


def setup(bot):
    bot.add_cog(MembersCog(bot))
