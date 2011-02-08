#!/usr/bin/python
import os
import sys
from subprocess import Popen

path = os.path.join(os.getcwd(), '../messages/help')
f = open(path, 'r')
message = ''.join(f.readlines())
f.close()

def stderr_print(message):
    sys.stderr.write(message + '\n')

stderr_print(message)

for script in os.listdir(os.getcwd()):
    if not os.access(script, os.X_OK) or script == 'help.py':
        continue
    command = [script]
    command.append('help')
    command.append('help')
    command.append('help')
    command.append('help')

    stderr_print("\nHelp for {0}".format(script))
    p = Popen(command)
    p.wait()
