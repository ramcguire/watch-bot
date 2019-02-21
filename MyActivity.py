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
        self.name = activity
        self.in_game = False
        self.start_time = None
        self.total_time = 0.0

    # helper method to update timestamp/in_game attribute
    # called when activity is ended
    def update_end_time(self, end_time):
        if self.in_game:
            logging.warning('not currently in_game, won\'t update end_time')
            return
        if self.start_time is None:
            logging.warning('no start time found, can\'t calculate time')
            return
        # reset start and set in_game false
        self.start_time = None
        self.in_game = False

    # helper method to update timestamp/in_game attribute
    # called when activity is started
    def update_start_time(self, start_time):
        if self.in_game:
            logging.warning(
                'found already in_game while trying toupdate_start_time')
            print('found already in_game while trying to update_start_time')
        self.in_game = True
        self.start_time = start_time

    # helper method to calc time in game
    def calc_time(self):
        return (self.end_time - self.start_time).total_seconds()

    # returns total time in game
    def get_total_time_in_game(self):
        if self.in_game:
            print('found in_game still')
            return (self.total_time + self.calc_time_since_start())
        return self.total_time

    def calc_time_since_start(self):
        return round((pendulum.now('UTC') - self.start_time).total_seconds())
