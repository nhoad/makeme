#!/usr/bin/python2

import sys

from subprocess import Popen

if sys.argv[4].upper().find('HELP') != -1:
    sys.stderr.write("Simply type the name of the commands you want to run, one command per line.\n")
    sys.exit(0)

for line in sys.argv[4].split('\n'):
    try:
        line = line.replace('\r', '')
        if not line:
            continue
        Popen(line.split(' '))
    except Exception, e:
        sys.stderr.write("Error executing %s\n" % line.split(' '))
        sys.stderr.write(str(e) + '\n')
