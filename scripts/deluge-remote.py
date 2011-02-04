#!/usr/bin/python2
import sys, os
import errno
import urllib
import re
from download import DownloadThread

from deluge.ui.client import client
from twisted.internet import reactor
from deluge.core import torrentmanager

from deluge.log import setupLogger
setupLogger(level='debug')

add_pattern = r'ADD (\S+)' # DONE
add_stop_pattern = r'ADD-STOP (\S+)' # DONE, but no pausing.
server_pattern = r'SERVER (\S+)' # DONE
user_pattern = r'USERNAME (\S+)' # DONE
pass_pattern = r'PASSWORD (\S+)' # DONE
port_pattern = r'PORT (\S+)' # DONE
max_down_pattern = r'MAX-DOWN (\S+)' # HOPEFULLY DONE
max_up_pattern = r'MAX-UP (\S+)' # HOPEFULLY DOWN
start_pattern = r'START (\S+)'
stop_pattern = r'STOP (\S+)'

port = 58846
server = 'localhost'
password = 'apples!'
username = ''

method_count = 0
finished_count = 0

result = re.search(server_pattern, sys.argv[4])

if result:
    server = result.groups()[0]

result = re.search(port_pattern, sys.argv[4])

if result:
    port = int(result.groups()[0])

result = re.search(user_pattern, sys.argv[4])

if result:
    username = result.groups()[0]

result = re.search(pass_pattern, sys.argv[4])

if result:
    password = result.groups()[0]


#make it case insensitive
sys.argv[4] = sys.argv[4].upper()

def stderr_print(output):
    """Print output to stderr"""
    sys.stderr.write(output + '\n')

def on_done(value, message):
    global finished_count
    finished_count += 1
    print "finished_count %d out of %d" % (finished_count, method_count)
    stderr_print(message)

    if finished_count == method_count:
        client.disconnect()
        reactor.stop()

def add_torrents(result):
    """Add all torrents to the server"""
    torrents = re.findall(add_pattern, sys.argv[4])

    for t in torrents:
        DownloadThread(t, os.path.join(os.environ['HOME'], "Downloads")).start()
        stderr_print("%s added, " % t)

    torrents = re.findall(add_stop_pattern, sys.argv[4])

    for t in torrents:
        DownloadThread(t, os.path.join(os.environ['HOME'], "Downloads")).start()
        stderr_print("%s added, but stopping downloads isn't supported yet." % t)

    on_done(None, "")

def show_progress(ids):
    print "progress"
    torrents = client.core.torrentmanager

    for i in ids:
        name = torrents[i].name
        percent = torrents[i].progress
        state = torrents[i].state
        stderr_print("%s - %s - %.2f%% - %s" % (i, name, percent, state))
    on_done(None, "")

def get_progress(result):
    """Display progress of all current torrents"""
    print "progress pt 1"
    if sys.argv[4].find('PROGRESS') == -1:
        on_done(None, "")
        return

    global method_count
    method_count +=1

    torrentmanager.get_torrent_list().addCallback(show_progess)
    on_done(None, "")

def magic_torrents(command):
    print command
    ids = []
    text = sys.argv[4]

    b = text.find(command.upper())

    if b == -1:
        on_done(None, "")
        return

    text = text[b:]
    text = text
    e = text.find('\n')

    if e == -1:
        ids = text.split(' ')
    else:
        ids = text[:e].split(' ')

    print ids

    if len(ids) >= 2 and ids[1].upper() == "ALL":
        print "here I am!"
        func = client.core.resume_all_torrents

        if command.lower() == 'stop':
            func = client.core.pause_all_torrents

        func().addCallback(on_done, "All torrents have been %s'ed" % command)
        print "All torrents have been %s'ed" % command
    else:
        ids = [ i for i in ids[1:]]
        func = client.core.resume_torrent

        if command.lower() == 'stop':
            func = client.core.pause_torrent

        func(ids).addCallback(on_done, ' '.join(ids[:-1]) + "and %s have been %s'ed" % ids[-1])

def max_up(result):
    result = re.search(max_up_pattern, sys.argv[4])

    if result:
        limit = int(result.groups()[0])
        client.core.set_config({'max_upload_speed': limit}).addCallback(on_done, "UPLOAD SPEED LIMITED TO %d KiB/s" % limit)

def max_down(result):
    result = re.search(max_down_pattern, sys.argv[4])

    if result:
        limit = int(result.groups()[0])
        client.core.set_config({'max_download_speed': limit}).addCallback(on_done, "DOWNLOAD SPEED LIMITED TO %d KiB/s" % limit)


def start_torrents(result):
    """start all or some of the torrents using START command"""
    magic_torrents('start')


def stop_torrents(result):
    magic_torrents('stop')


def help():
    """Display help for the user to figure out how to use this script"""
    if sys.argv[4].find("HELP") != -1:
        stderr_print("ADD link -- Add the link to transmission and start right away")
        stderr_print("ADD-STOP link -- Add the link to transmission and stop")
        stderr_print("SERVER ip-or-domain-name -- the ip or domain name of the server hosting transmission. Default localhost")
        stderr_print("PORT port -- the port that Transmission is using on the server. Default 9091")
        stderr_print("TURTLE-ON -- down-speed turn on turtle mode, and set download limit to down-speed. Down-speed is optional")
        stderr_print("TURTLE-OFF -- turn turtle mode off")
        stderr_print("START ids -- space delimited ids of torrents to start. Accepts ALL to start all torrents")
        stderr_print("STOP ids -- space delimited ids of torrents to stop. Accepts ALL to stop all torrents")
        stderr_print("PROGRESS -- output torrent id, name and progress in percent")
        return True

    return False


if help():
    sys.exit(0)


def on_fail(result):
    stderr_print("Couldn't connect! Reason: %s", result)

methods = [max_up, max_down, stop_torrents, start_torrents, add_torrents, get_progress]
methods = [get_progress]
method_count = len(methods)
d = client.connect(server, port, username, password)

for m in methods:
    d.addCallback(m)

d.addErrback(on_fail)
reactor.run()
