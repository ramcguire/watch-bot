# class to contain information for activty tracking per user
# since there can be multiple activities per member, each MyActivity
# should contain timestamp and timespent
# information for only that activity
import logging
import pendulum


class MyActivity():
    def __init__(self, activity):
        pass


class MyGame():
    def __init__(self, activity):
        self.name = activity.name
        self.in_game = True
        self.start_time = pendulum.instance(activity.start, 'UTC')
        self.timestamps = []
        self.total_time = 0.0

    # helper method to update timestamp/in_game attribute
    def update_end_time(self, end_time):
        self.in_game = False
        self.end_time = end_time
        self.update_timestamps()

    # helper method to update timestamp/in_game attribute
    def update_start_time(self, start_time):
        if self.in_game:
            logging.warning(
                'found already in_game while trying toupdate_start_time')
            print('found already in_game while trying to update_start_time')
        self.in_game = True
        self.start_time = start_time

    # updates timestamps after ending a game
    def update_timestamps(self):
        # if trying to update without valid timestamp pair
        if self.start_time is None or self.end_time is None:
            logging.warning('invalid update_timestamps in MyGame, start or end time is None')
            print('invalid update_timestamps in MyGame, start or end time isNone')
            return
        # updates timestamps and total_time
        self.timestamps.append((self.start_time, self.end_time))
        self.total_time += self.calc_time()
        # reset start/end timestamps
        self.end_time = None
        self.start_time = None

    # helper method to calc time in game
    def calc_time(self):
        return (self.end_time - self.start_time).total_seconds()

    def get_total_time_in_game(self):
        time = self.total_time
        if self.in_game:
            time += round((pendulum.now('UTC') -
                self.start_time).total_seconds())
        return time

    def calc_time_since_start(self):
        return round((pendulum.now('UTC') - self.start_time).total_seconds())
