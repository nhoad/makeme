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
import traceback
import configparser

from smtplib import SMTPAuthenticationError

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

default_options = {}
monitor = None

# we set the default options for unrequired config file stuff here
default_options['contact_address'] = None
default_options['monitor_config'] = 'no'
default_options['should_fork'] = 'yes'
default_options['first_email_sent'] = 'no'
default_options['unsent_save_location'] = 'unsent_emails.log'
default_options['imap_server'] = 'imap.gmail.com'
default_options['imap_port'] = 993
default_options['imap_use_ssl'] = 'yes'
default_options['smtp_server'] = 'smtp.gmail.com'
default_options['smtp_port'] = 587
default_options['smtp_use_tls'] = 'yes'
default_options['log_file'] = 'makeme.log'
default_options['log_level'] = 'debug'
default_options['log_format'] = '[%(asctime)s] %(levelname)s: %(message)s'
default_options['date_format'] = '%Y-%m-%d %H:%M:%S'

conf = configparser.RawConfigParser(default_options)
conf.read(global_file)
if not conf.read(user_file):
    print("No .makemerc file could be found. Check the documentation for details.", file=sys.stderr)
    print(conf.get('settings', 'imap_server'))
    sys.exit(1)

# now let's get the config stuff that the user NEEDS to set.
try:
    refresh_time = conf.get('settings', 'refresh_time')
    username = conf.get('settings', 'username')
    password = functions.decrypt(username, conf.get('settings', 'password'))
    patterns = conf.items('scripts')
    contact_address = conf.get('settings', 'contact_address')
    reconnect_attempts = conf.getint('settings', 'reconnect_attempts')

except configparser.NoOptionError as e:
    print('{0}. Consult the documentation for help or add the missing option to your config file.'.format(e), file=sys.stderr)
    sys.exit(4)

should_fork = conf.getboolean('settings', 'should_fork')
first_email_sent = conf.getboolean('settings', 'first_email_sent')
monitor_config = conf.getboolean('settings', 'monitor_config')
unsent_save_location = conf.get('settings', 'unsent_save_location')
log_file = conf.get('settings', 'log_file')
log_level = conf.get('settings', 'log_level')
log_format = conf.get('settings', 'log_format')
date_format = conf.get('settings', 'date_format')
smtp_server = conf.get('settings', 'smtp_server')
smtp_port = conf.getint('settings', 'smtp_port')
smtp_use_tls = conf.getboolean('settings', 'smtp_use_tls')
imap_server = conf.get('settings', 'imap_server')
imap_port = conf.getint('settings', 'imap_port')
imap_use_ssl = conf.getboolean('settings', 'imap_use_ssl')

if should_fork:
    try:
        pid = os.fork()

        if pid != 0:
            sys.exit(0)
    except OSError as e:
        print("FATAL ERROR WHILE FORKING: {0}".format(e))
        sys.exit(12)

log_level = eval("logging.{0}".format(log_level.upper()))

# I explicitly don't start logging before forking to prevent deadlocks and prevent all sorts of nasty filesystem madness.
logging.basicConfig(filename=log_file, level=log_level, format=log_format, datefmt=date_format)

try:
    server = EmailServer(username, password)
    server.contact_address = contact_address
    server.patterns = patterns
    server.reconnect_attempts = reconnect_attempts
    server.unsent_save_location = unsent_save_location
    server.set_imap(imap_server, imap_port, imap_use_ssl)
    server.set_smtp(smtp_server, smtp_port, smtp_use_tls)
    server.login_smtp()

    if not first_email_sent:
        server.send_intro_email()
        conf.set('settings', 'first_email_sent', 'yes')
        with open(user_file, 'w') as f:
            conf.write(f)

    # monitor MUST be done after sending the first email, otherwise the program may trigger reloading
    if monitor_config:
        monitor = functions.monitor(conf.file_name, server)

    server.run(refresh_time)

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
except Exception as e:
    trace = traceback.format_exc()
    print(trace, file=sys.stderr)
    logging.critical("UNKNOWN ERROR OCCURRED: {0}".format(trace))
    logging.critical('PLEASE CONTACT THE DEVELOPERS REGARDING THIS ISSUE')
    if monitor:
        monitor.stop()
    shutdown(5)
