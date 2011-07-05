#!/usr/bin/python
from makeme import MakeMe
server = MakeMe()

parse command line
parse config file

fork to background
set up logging

server = MakeMe(conf)
running = server.running
wait = server.wait
check_messages = server.check_messages

while running():
    check_messages()
    wait()

server.stop()
