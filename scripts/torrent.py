#!/usr/bin/python2
import sys, os
import errno
import urllib
import re
import transmissionrpc
from threading import Thread

add_pattern = r'ADD (\S+)'
add_stop_pattern = r'ADD-STOP (\S+)'
server_pattern = r'SERVER (\S+)'

port = 9091
server = 'localhost'
should_stop = False

result = re.search(server_pattern, sys.argv[4])

if result is not None:
    if len(result.groups()) == 1:
        server = result.groups()[0]
    else:
        server = result.groups()[0]


def add_torrents(client):
    """Add all torrents to the server"""
    torrents = re.findall(add_pattern, sys.argv[4])

    for t in torrents:
        client.add_url(t)

    torrents = re.findall(add_stop_pattern, sys.argv[4])

    for t in torrents:
        id = client.add_url(t)

        client.stop(id)

def show_progress(client):
    """Display progress of all current torrents"""
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

def start_torrents(client):
    """start all or some of the torrents using START command"""
    magic_torrents(client, 'start')

def stop_torrents(client):
    magic_torrents(client, 'stop')

tc = transmissionrpc.Client(server, port=port)
