'''
File: functions.py
Author: Nathan Hoad
Description: Misc. functions used in makeme.
'''
import logging
import sys
import time
import os
import math

from pyinotify import WatchManager, ThreadedNotifier, ProcessEvent, IN_CLOSE_WRITE, IN_CLOSE_NOWRITE

import config


def monitor(filename, server):
    """Monitor the config file for changes and update the server's values when they do.

    Using pyinotify, it checks the config file for changes and tells the server to make changes when they occur. Starts and returns the ThreadedNotifier that is created.

    Keyword arguments:
    filename -- the name of the file you want to monitor. Note that it won't actually monitor this file, but the directory it resides in.
    server -- the EmailServer currently running, to pass the new values to when they're changed.

    """
    print("Beginning Monitoring for {0}".format(filename))

    class PClose(ProcessEvent):
        def __init__(self, server, filename):
            self.server = server
            self.filename = filename

        def process_IN_CLOSE(self, event):
            if event.name != os.path.split(self.filename)[1]:
                return

            conf = config.Config()
            conf.read(self.filename)

            try:
                refresh_time = conf['settings']['refresh_time']
                username = conf['settings']['username']
                password = conf['settings']['password']
                patterns = conf['scripts']
                contact_address = conf['settings']['contact_address']

                lock = self.server.lock

                lock.acquire()
                self.server.reload_values(username, password, contact_address, patterns, refresh_time)
                lock.release()

            except KeyError as e:
                print("{0} could not be found in the config file. Consult the documentation for help.".format(e), file=sys.stderr)
                print(dir(e))
                raise e
                sys.exit(4)

    wm = WatchManager()
    notifier = ThreadedNotifier(wm, PClose(server, filename))
    notifier.name = 'MonitorThread'
    wm.add_watch(os.path.split(filename)[0], IN_CLOSE_WRITE, rec=True)

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
    """Returns the current minutes past the hour."""
    return int(time.strftime("%M"))


def get_imap_settings(conf):
    """Tries to get the imap options from the config file. If it can't find them, return defaults.

    Keyword arguments:
    conf -- the Config object to read from

    """
    try:
        imap_server = conf['settings']['imap_server']
        imap_port = conf['settings']['imap_port']
        imap_use_ssl = conf['settings']['imap_use_ssl']

        return imap_server, imap_port, imap_use_ssl
    except KeyError as e:
        imap_server = 'imap.gmail.com'
        imap_port = 993
        imap_use_ssl = True

        return imap_server, imap_port, imap_use_ssl


def get_smtp_settings(conf):
    """Tries to get the smtp options from the config file. If it can't find them, return defaults.

    Keyword arguments:
    conf -- the Config object to read from

    """
    try:
        smtp_server = conf['settings']['smtp_server']
        smtp_port = conf['settings']['smtp_port']
        smtp_use_ssl = conf['settings']['smtp_use_tls']

        return imap_server, imap_port, imap_use_ssl
    except KeyError as e:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_use_tls = True

        return smtp_server, smtp_port, smtp_use_tls


def get_log_settings(conf):
    """Tries to get the log file options from the config file. If it can't find them, return defaults.

    Keyword arguments:
    conf -- the Config object to read from

    """
    try:
        log_file = conf['settings']['log_file']
        log_format = conf['settings']['log_format']
        log_level = conf['settings']['log_level']
        date_format = conf['settings']['date_format']
        return log_file, log_level, log_format, date_format
    except KeyError as e:
        print("{0} could not be found in the config file. Defaults log options will be used.".format(e))

        log_file = 'makeme.log'
        log_level = 'debug'
        log_format = '[%(asctime)s] %(levelname)s: %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'

        return log_file, log_level, log_format, date_format


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

            if desired_time == 0:
                return 60 - current_time
            elif desired_time == current_time:
                return 3600  # wait an hour, don't go right now!
            elif desired_time > current_time:
                return (desired_time - current_time) * 60
            else:
                return int(math.fabs((current_time - (desired_time + 60)) * 60))
        elif start_char == '/':
            if not refresh_time_checked:
                logging.info("Next check at {0} minutes, normalised"\
                    .format(desired_time))

            if current_time % desired_time == 0:
                return desired_time * 60

            # make current_time divisible by 10.
            current_time = current_time % desired_time

            if desired_time > current_time:
                return (desired_time - current_time) * 60
            else:
                return int(math.fabs(current_time - (desired_time + 60)))

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
