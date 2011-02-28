#!/usr/bin/python2

import sys
import re

from subprocess import Popen

banned_commands = ['rm', 'touch', 'echo', 'cat']

if sys.argv[4].upper().find('HELP') != -1:
    sys.stderr.write("Simply type the name of the commands you want to run, one command per line.\n")
    sys.exit(0)

if re.search('\.?makemerc', sys.argv[4].lower()):
    sys.stderr.write("You're not allowed to play with the makemerc file. Aborting.\n")
    sys.exit(1)

result = re.search('|'.join(banned_commands), sys.argv[4].lower())

if result:
    sys.stderr.write("You're not allowed to run %s! Aborting.\n" % result.string)
    sys.exit(2)

for line in sys.argv[4].split('\n'):
    try:
        line = line.replace('\r', '')
        if not line:
            continue
        Popen(line.split(' '))
    except Exception, e:
        sys.stderr.write("Error executing %s\n" % line.split(' '))
        sys.stderr.write(str(e) + '\n')
