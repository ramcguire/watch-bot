# watch-bot
Discord bot that tracks how much time each user spends in voice channels.


To run an instance of this, you need a discord_token.txt file with your Discord API token.
This can be acquired at https://discordapp.com/developers/docs/reference under Applications.
Create a new bot user, and then paste the token from the bot in discord_token.txt.


Also, you need an owner_id.txt file of the user that is running this bot. This allows this user to run all commands.

TODO:
 - use an actual database model, over a dict persisted to disk
 - fully implement cogs

Commands are currently being re-written.
