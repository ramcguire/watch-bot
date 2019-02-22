# watch-bot
Discord bot that tracks how much time each user spends in voice channels.


To run an instance of this, you need a discord_token.txt file with your Discord API token.
This can be acquired at https://discordapp.com/developers/docs/reference under Applications.
Create a new bot user, and then paste the token from the bot in discord_token.txt.


Also, you need an owner_id.txt file of the user that is running this bot. This allows this user to run all commands.



Current supported commands:
[PREFIX]commands - returns a list of commands user is authorized to use in the guild that the message was sent.

[PREFIX]timespent - returns time spent in voice channels of the requesting user in current guild.

[PREFIX]reset_user_stats - removes stats for respective user in this guild. Must confirm by sending CONFIRM in DM.

[PREFIX]set_pref_tz - allows you to set a preferred timezone for data display. Syntax: $set_pref_tz Timezone_name (use    https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

[PREFIX]get_pref_tz - sends you a message with your current timezone (defaults to UTC).

[PREFIX]guild_stats - Prints a summary of collective time spent by users in voice channels in this guild.

[PREFIX]gametime - Prints a summary of time spent in games that the bot has tracked. Use "gametime current" to see history of current activity.

[PREFIX]guild_games - Prints the collective time users in this guild have spent in each game.

[GUILD ADMIN COMMANDS]

[PREFIX]reset_guild_stats (owner/admin of guild only) - removes all tracked time for all users in guild.
[PREFIX]leave_guild (owner/admin of guild only) - leaves guild, but does not remove tracked information. Bot can be re-added.

[BOT OWNER COMMANDS]

[PREFIX]reset_commands_run - resets commands_run from bot stats to 0.

[PREFIX]add_admin - adds users that are mentioned in this message to admins list.

[PREFIX]rem_admin - removes users that are mentioned in this message from admins list.

[PREFIX]shutdown - best way to shutdown bot, cleans up all in_channel members and quits.

[PREFIX]re_init - removes all data and bot stats and starts fresh.
