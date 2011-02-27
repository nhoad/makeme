#!/usr/bin/python
'''
File: set-user.py
Author: Nathan Hoad
Description: Used to set the password in the user's config file in a reasonably secure manner
'''
import sys
import os
import configparser
import functions

if len(sys.argv) != 3:
    print("Usage: set-user.py [username] [password]")
    sys.exit(1)

username = sys.argv[1]
password = sys.argv[2]

conf_file = os.path.join(os.environ['HOME'], '.makemerc')
conf = configparser.RawConfigParser()

# read in the config so we don't stomp out other values
conf.read(conf_file)

conf.set('settings', 'username', username)
conf.set('settings', 'password', functions.encrypt(username, password))

with open(conf_file, 'w') as f:
    conf.write(f)

print('Your username and password have now been securely set.')
