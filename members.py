import asyncio
import discord
from discord.ext import commands


class MembersCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='sayhello')
    async def sayhello(self, ctx):

        '''Simple hello world!'''
        await ctx.send("hello world!")
