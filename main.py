#!/usr/bin/python3
'''
File: main.py
Author: Nathan Hoad
Description: makeme driver module.
'''

import logging
import os
import signal
import sys

from smtplib import SMTPAuthenticationError

import config
import functions
import threads

from emails import EmailServer
from exceptions import ShutdownException
from functions import shutdown, get_time, calculate_refresh
import threading

signal.signal(signal.SIGSEGV, shutdown)
signal.signal(signal.SIGTERM, shutdown)

global_file = "/usr/share/makeme/makemerc"
user_file = os.path.join(os.environ['HOME'], ".makemerc")
conf = config.get_config(user_file, global_file)

contact_address = None
monitor = None
monitor_config = False

if not conf:
    print("No .makemerc file could be found. Check the documentation for details.", file=sys.stderr)
    sys.exit(1)

try:
    refresh_time = conf['settings']['refresh_time']
    username = conf['settings']['username']
    password = conf['settings']['password']
    patterns = conf['scripts']
    log_file = conf['settings']['log_file']
    log_format = conf['settings']['log_format']
    log_level = conf['settings']['log_level']
    date_format = conf['settings']['date_format']
    should_fork = eval(conf['settings']['should_fork'])
    contact_address = conf['settings']['contact_address']
    first_email_sent = eval(conf['settings']['first_email_sent'])
    monitor_config = eval(conf['settings']['monitor_config'])
    reconnect_attempts = eval(conf['settings']['reconnect_attempts'])

except KeyError as e:
    print("{0} could not be found in the config file. Consult the documentation for help.".format(e), file=sys.stderr)
    sys.exit(4)

if should_fork:
    try:
        pid = os.fork()

        if pid != 0:
            sys.exit(0)
    except OSError as e:
        print("FATAL ERROR WHILE FORKING: {0}".format(e))
        sys.exit(12)

log_level = eval("logging.{0}".format(log_level.upper()))
# I explicitly don't start logging before forking to prevent deadlocks.
logging.basicConfig(filename=log_file, level=log_level, format=log_format, datefmt=date_format)

try:
    server = EmailServer(username, password)
    server.contact_address = contact_address
    server.patterns = patterns
    server.login_smtp()

    if not first_email_sent:
        server.send_intro_email()
        conf['settings']['first_email_sent'] = str(True)
        conf.save()

    # monitor MUST be done after sending the first email, otherwise the program may trigger reloading
    if monitor_config:
        monitor = functions.monitor(conf.file_name, server)

    server.run(refresh_time)
    #while True:
    #    refresh_time = self.refresh_time
    #    new_refresh = calculate_refresh(refresh_time, True)
    #    logging.info("Checking instructions in {0} seconds, calculated from {1}".format(new_refresh, refresh_time))
    #    time.sleep(new_refresh)
    #    logging.info("Checking for new instructions")
    #    server.check_messages()
except KeyboardInterrupt:
    if monitor:
        monitor.stop()
    shutdown()
except ShutdownException as e:
    if monitor:
        monitor.stop()
    shutdown(e.exitcode)
except ValueError as e:
    logging.critical("refresh_time in your config file MUST be a number! Consult the documentation.")
    if monitor:
        monitor.stop()
    shutdown(1)
#except Exception as e:
#    print("UNKNOWN ERROR OCCURRED: {0}".format(e))
#    logging.critical("UNKNOWN ERROR OCCURRED: {0}".format(e))
#    if monitor:
#        monitor.stop()
#    shutdown(5)
