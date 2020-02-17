import operator
import numpy as np
import pendulum

from matplotlib import pyplot as plt
from matplotlib import style

from MyChannel import MyChannel
from MyGuild import MyGuild
from MyMember import MyMember
from sqlitedict import SqliteDict

style.use('ggplot')

u_data = SqliteDict('./user_data.db')

member = u_data['170043759579365377']

list_games = [x.name for x in sorted(member.activity_info.values(), key=operator.attrgetter('total_time'), reverse=True)]

list_times = []
label_games = []
leftover_games = 0


for game in list_games[:10]:
    s = member.activity_info[game].total_time
    add_str = '\n(' + (pendulum.duration(seconds=s)).in_words() + ')'
    list_times.append(s)
    label_games.append(str(game + add_str))

if (len(list_times) > 10):
    leftover_time = sum(list_times[10:])
    print('greater than 1')
    leftover_games = len(list_times[10:])
    list_times[10] = sum(list_times[10:])
    add_str = 'Other ({0} games)'.format(str(leftover_games))
    list_games[10] = add_str
    add_str += '\n(' + (pendulum.duration(seconds=leftover_time)).in_words() + ')'
    label_games[10] = add_str


max_time = np.ceil(max(list_times))


def set_y_label(max_time):
    # month
    if max_time > 2592000:
        list_times[:21] = [x / 2592000 for x in list_times]
        return 'Time played (months)'

        # week
    elif max_time > 604800:
        list_times[:10] = [x / 604800 for x in list_times]
        return 'Time played (weeks)'

        # day
    elif max_time > 86400:
        list_times[:10] = [x / 86400 for x in list_times]
        plt.ylabel()
        return 'Time played (days)'

    # hour
    elif max_time > 3600:
        list_times[:10] = [x / 3600 for x in list_times]
        return 'Time played (hours)'

    # minute
    elif max_time > 60:
        list_times[:10] = [x / 60 for x in list_times]
        return 'Time played (minutes)'

    else:
        return 'Time played (seconds)'


y_label = set_y_label(max_time)
#plt.bar(label_games[:10], list_times[:10])
#plt.xlabel('Games')
#plt.ylabel(y_label)
plt.pie(list_times[:10], labels=list_games[:10], autopct='%.1f%%')
plt.title('Second Chart')


#plt.savefig('output.png', bbox_inches='tight')

plt.show()
