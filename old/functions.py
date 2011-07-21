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
import datetime
import configparser

from pyinotify import WatchManager, ThreadedNotifier, ProcessEvent, IN_CLOSE_WRITE, IN_CLOSE_NOWRITE


def encrypt(key, msg):
    """Simple encryption so passwords aren't stored in plain-text.

    Please note that this is quite weak security, and completely breakable
    with little or no effort. If you take issue with this method, don't
    hesitate to offer your own implementation. I know very little about
    security and would be happy for someone to school me on this.

    Keyword arguments:
    key -- the key to use for encryption. Supa-secret!
    msg -- the text to be encrypted.

    Returns msg in encrypted form.

    """
    enc = []

    for i, c in enumerate(msg):
        key_c = ord(key[i % len(key)])
        msg_c = ord(c)
        enc.append(chr((msg_c + key_c) % 127))

    return ''.join(enc)


def decrypt(key, enc):
    """Simple decryption. Reverse of the encryption function

    Please note that this is quite weak security, and completely breakable
    with little or no effort. If you take issue with this method, don't
    hesitate to offer your own implementation. I know very little about
    security and would be happy for someone to school me on this.

    Keyword arguments:
    key -- the key to use for encryption. Supa-secret!
    msg -- the text to be decrypted.

    Returns enc in decrypted form.

    """
    msg = []

    for i, c in enumerate(enc):
        key_c = ord(key[i % len(key)])
        msg_c = ord(c)
        msg.append(chr((msg_c - key_c) % 127))

    return ''.join(msg)


def save_emails_to_file(emails, filename, reason):
    """Save a list of emails to a file in the current working directory.

    Keyword arguments:
    emails -- list of Email objects to be saved to file.
    filename -- the filename to save unsent emails to.
    reason -- the text or exception reason the emails couldn't be sent.

    """
    now = datetime.datetime.now()
    date = '{0}-{1}-{2}'.format(now.day, now.month, now.year)
    time = '{0}:{1}:{2}'.format(now.hour, now.minute, now.second)
    with open(filename, 'a') as f:
        f.write('On the {0}, at {1}, the following emails could not be sent:\n'.format(date, time))
        f.write('The reason for this: {0}\n'.format(reason))

        for e in emails:
            f.write('{0}\n'.format(e))


class PClose(ProcessEvent):
    def __init__(self, server, filename):
        """Initialise the PClose object.

        Keyword arguments:
        server -- the EmailServer object to report config file changes back to.
        filename -- the file that PClose should monitor.

        """
        self.server = server
        self.filename = filename

    def process_IN_CLOSE(self, event):
        """Process IN_CLOSE events for the directory being monitored.

        Keyword arguments:
        event -- the event that has occurred. Mystical stuff!"""
        if event.name != os.path.split(self.filename)[1]:
            return

        conf = configparser.RawConfigParser()
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

        except configparser.NoOptionError as e:
            logging.info("{0}. Consult the documentation for help or add the missing option to your config file.".format(e), file=sys.stderr)
            self.stop()
            raise ShutdownException(15)


def monitor(filename, server):
    """Monitor the config file for changes and update the server's values when they do.

    Using pyinotify, it checks the config file for changes and tells the
    server to make changes when they occur. Starts and returns the
    ThreadedNotifier that is created.

    Keyword arguments:
    filename -- the name of the file you want to monitor. Note that it won't actually monitor this file, but the directory it resides in.
    server -- the EmailServer currently running, to pass the new values to when they're changed.

    """
    logging.info('Monitoring {0} for changes'.format(filename))

    wm = WatchManager()
    notifier = ThreadedNotifier(wm, PClose(server, filename))
    notifier.name = 'MonitorThread'
    # we actually watch the folder to the file, otherwise the handle is lost every time the file is modified.
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
