'''
File: functions.py
Author: Nathan Hoad
Description: Misc. functions used in makeme.
'''
import logging
import sys
import time

from pyinotify import WatchManager, ThreadedNotifier, ProcessEvent, IN_CLOSE_WRITE, IN_CLOSE_NOWRITE

import config

def monitor(filename, server):
    print("Beginning Monitoring for {0}".format(filename))
    class PClose(ProcessEvent):
        def __init__(self, server, filename):
            self.server = server
            self.filename = filename

        def process_IN_CLOSE(self, event):
            print("HELLO!")
            conf = config.Config()
            conf = {'settings' : {'username':'test', 'password': 'test', 'contact_address': 'test'},
                    'scripts': {'f':'asdf.py'}}
            lock = self.server.lock
            username = conf['settings']['username']
            password = conf['settings']['password']
            patterns = conf['scripts']
            contact_address = conf['settings']['contact_address']
            lock.acquire()
            self.server.reload_values(username, password, contact_address, patterns)
            lock.release()
            nothing = """
            conf.read(self.filename)

            try:
                refresh_time = conf['settings']['refresh_time']
                username = conf['settings']['username']
                password = conf['settings']['password']
                patterns = conf['scripts']
                contact_address = conf['settings']['contact_address']

                lock = self.server.lock

                lock.acquire()
                self.server.reload_values(username, password, contact_address, patterns)
                lock.release()

            except KeyError as e:
                print("{0} could not be found in the config file. Consult the documentation for help.".format(e), file=sys.stderr)
                sys.exit(4)"""

    wm = WatchManager()
    notifier = ThreadedNotifier(wm, PClose(server, filename))
    wm.add_watch(filename, IN_CLOSE_WRITE|IN_CLOSE_NOWRITE, rec=True)

    notifier.start()

    return notifier

def shutdown(exitcode=0):
    """Shutdown makeme nicely.

    Keyword arguments:
    exitcode -- the exitcode to shutdown with. Defaults to 0.

    """
    logging.info("Shutting down makeme.")
    sys.exit(exitcode)


def get_time():
    """Returns the current minutes past."""
    return int(time.strftime("%M"))


def calculate_refresh(refresh_time, refresh_time_checked=False):
    """Calculate how long until instructions should be checked

    Keyword arguments:
    refresh_time -- String argument for processing. Consult documentation.
    refresh_time_checked -- For debugging, True the first time, False the rest.

    """
    try:
        return int(refresh_time) * 60
    except ValueError:
        start_char = refresh_time[:1]
        desired_time = int(refresh_time[1:])

        current_time = get_time()

        if start_char == ':':
            if not refresh_time_checked:
                logging.info("Checking at {0} past, on the hour"\
                    .format(desired_time))
            if desired_time == current_time:
                return 0
            elif desired_time > current_time:
                return (desired_time - current_time) * 60
            else:
                return ((current_time - desired_time) + 60) * 60
        elif start_char == '/':
            if not refresh_time_checked:
                logging.info("Next check at {0} minutes, normalised"\
                    .format(esired_time))

            if current_time % desired_time == 0:
                return desired_time * 60

            # make current_time divisible by 10.
            current_time = current_time % desired_time

            if desired_time > current_time:
                return (desired_time - current_time) * 60
            else:
                return current_time - desired_time + 60

        elif start_char == 's':
            if not refresh_time_checked:
                logging.info("Checking every {0} seconds"\
                    .format(desired_time))
            return desired_time
        elif start_char == 'h':
            if not refresh_time_checked:
                logging.info("Checking every {0} hours"\
                    .format(desired_time))
            return desired_time * 60 * 60
        else:
            return -1
