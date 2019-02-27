import logging
import os
import pickle

from sqlitedict import SqliteDict


# serves as initialization point for global variables to be used accross
# modules
# each variable can be access using globals.variable_name
def init():
    global TOKEN
    global owner_id
    global bot_stats
    global u_data
    global g_data
    global continue_timer
    global admins
    global c_prefix
    global bkg_timer

    # setup logging to file (ignoring debug logging)
    logging.basicConfig(filename='.activity_log.log', level=logging.INFO)

    # initialize all member variables here
    with open('discord_token.txt', 'r') as myfile:
        TOKEN = myfile.readline()
    with open('owner_id.txt', 'r') as myfile:
        owner_id = int(myfile.readline())

    c_prefix = '!'

    continue_timer = True

    # keeping track of all data here
    # uses sqlite/pickle to store objects in a persistent dictionary
    bot_stats = SqliteDict('./bot_stats.db')
    u_data = SqliteDict('./user_data.db')
    g_data = SqliteDict('./guild_data.db')

    # load admins information
    # if doesn't exist, create using owner_id as default first admin
    admins = []
    if not os.path.isfile('./admins.p'):
        admins.append(str(owner_id))
        pickle.dump(admins, open('./admins.p', 'wb'))

    admins = pickle.load(open('./admins.p', 'rb'))
