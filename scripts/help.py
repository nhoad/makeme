#!/usr/bin/python
import os
import sys
from subprocess import Popen

path = os.path.join(os.getcwd(), 'messages/help')
with open(path, 'r') as f:
    message = ''.join(f.readlines())

def stderr_print(message):
    sys.stderr.write(message + '\n')

stderr_print(message)
directory = os.path.dirname(os.path.realpath(__file__))

for script in os.listdir(directory):
    print(script)
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
