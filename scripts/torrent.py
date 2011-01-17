#!/usr/bin/python2
import sys, os
import errno
import urllib
import re
import transmissionrpc

add_pattern = r'ADD (\S+)'
add_stop_pattern = r'ADD-STOP (\S+)'
server_pattern = r'SERVER (\S+)'
port_pattern = r'PORT (\S+)'
turtle_pattern = r'TURTLE-ON (\S+)'

def add_torrents(client):
    """Add all torrents to the server"""
    torrents = re.findall(add_pattern, sys.argv[4])

    for t in torrents:
        client.add_url(t)

    torrents = re.findall(add_stop_pattern, sys.argv[4])

    for t in torrents:
        id = client.add_url(t)
        print "%s added" % t

        client.stop(id)


def show_progress(client):
    """Display progress of all current torrents"""
    if sys.argv[4].find('PROGRESS') == -1:
        return

    torrents = client.list()

    for i in torrents.keys():
        name = torrents[i].name
        percent = torrents[i].progress
        print "%d - %s - %.2f%%" % (i, name, percent)


def magic_torrents(client, command):
    ids = []
    text = sys.argv[4]

    b = text.find(command.upper())

    if b == -1:
        return

    text = text[b:]
    text = text
    e = text.find('\n')
    ids = text[:e].split(' ')

    if len(ids) >= 2 and ids[1].upper() == "ALL":
        ids = client.list()
    else:
        ids = ids[1:]

    for i in ids:
        getattr(client, command)(i)

    print "All torrents have been %s'ed" % command


def turtle_on(client):
    result = re.search(turtle_pattern, sys.argv[4])

    if result:
        limit = int(result.groups()[0])

        client.set_session(alt_speed_enabled=True)
        print "TURTLE MODE TURNED ON"
        client.set_session(alt_speed_down=limit)
        print "SPEED LIMITED TO %d KiB/s" % limit


def turtle_off(client):
    if sys.argv[4].find("TURTLE-OFF") != -1:
        client.set_session(alt_speed_enabled=False)
        print "TURTLE MODE TURNED OFF"


def start_torrents(client):
    """start all or some of the torrents using START command"""
    magic_torrents(client, 'start')


def stop_torrents(client):
    magic_torrents(client, 'stop')


port = 9091
server = 'localhost'

result = re.search(server_pattern, sys.argv[4])

if result:
    server = result.groups()[0]

result = re.search(port_pattern, sys.argv[4])

if result:
    port = int(result.groups()[0])

tc = transmissionrpc.Client(server, port=port)

add_torrents(tc)
show_progress(tc)
start_torrents(tc)
stop_torrents(tc)
turtle_on(tc)
turtle_off(tc)
