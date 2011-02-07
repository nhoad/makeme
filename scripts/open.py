#!/usr/bin/python2

import sys

from subprocess import Popen

for line in sys.argv[4].split('\n'):
    try:
        line = line.replace('\r', '')
        if not line:
            continue
        Popen(line.split(' '))
    except Exception, e:
        sys.stderr.write("Error executing %s\n" % line.split(' '))
        sys.stderr.write(str(e) + '\n')
