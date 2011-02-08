#!/usr/bin/python2
from mpd import MPDClient
import re
import sys

sys.argv[4] = sys.argv[4].upper()

def stderr_print(output):
    sys.stderr.write(output + '\n')

if sys.argv[4].find('HELP') != -1:
    stderr_print("prev - play previous song")
    stderr_print("next - play next song")
    stderr_print("play - play music")
    stderr_print("pause - pause music")
    stderr_print("stats - display uptime, db playtime, artists albums and songs count")
    stderr_print("volume - set the volume. Can be given a number to set it to (0 - 100) or + or - and a number to raise or lower it.")
    stderr_print("search - search for and display a list of all songs in the database. First argument should be the field type, i.e. artist, title, or even any. The second should be the search term.")
    sys.exit(0)

client = MPDClient()

client.connect(host='localhost', port='6600')

if sys.argv[4].find("NEXT") != -1:
    client.next()

if sys.argv[4].find("PREV") != -1:
    client.previous()

if sys.argv[4].find("PLAY") != -1:
    client.play()
    stderr_print("Playing music!")

if sys.argv[4].find("PAUSE") != -1:
    client.pause()
    stderr_print("Paused music!")

if sys.argv[4].find("STATS") != -1:
    results = client.stats()

    uptime = results['uptime']
    artists = results['artists']
    albums = results['albums']
    songs = results['songs']

    playtime = int(results['db_playtime'])
    remainder = playtime % 86400

    days = (playtime - remainder) / 86400

    playtime = remainder
    remainder = playtime % 3600

    hours = (playtime - remainder) / 3600

    playtime = remainder
    remainder = playtime % 60

    minutes = (playtime - remainder) / 60

    playtime = remainder
    seconds = playtime % 60

    stderr_print("Artists: %s" % artists)
    stderr_print("Albums: %s" % albums)
    stderr_print("Songs: %s\n" % songs)
    stderr_print("%d days, %d:%d:%d worth of music\n" % (days, hours, minutes, seconds))

    song = client.currentsong()

    print "Now Playing: %s - %s" % (song['artist'], song['title'])

result = re.search(r'VOLUME (\S+)', sys.argv[4])

if result:
    current_volume = int(client.status()['volume'])
    new_volume = result.groups()[0]

    if new_volume[0] == '+':
        new_volume = int(new_volume[1:])

        if new_volume + current_volume > 100:
            client.setvol(100)
        else:
            client.setvol(current_volume + new_volume)
    elif new_volume[0] == '-':
        new_volume = int(new_volume[1:])

        if current_volume - new_volume < 0:
            client.setvol(0)
        else:
            client.setvol(current_volume - new_volume)

    else:
        new_volume = int(new_volume)

        if new_volume < 0:
            client.setvol(0)
        elif new_volume > 100:
            client.setvol(100)
        else:
            client.setvol(new_volume)

b = sys.argv[4].find("SEARCH")
if b != -1:
    text = sys.argv[4][b:]

    e = text.find('\n')
    if e != -1:
        text = text[:e]

    text = text.split(' ')
    field = text[1].lower()
    text = ' '.join([ t for t in text[2:]])

    stderr_print("Search results for %s" % text)
    results = client.search(field, text)

    for line in results:
        artist = 'Unknown'
        album = 'Unknown'
        title = 'Unknown'

        try:
            artist = line['artist']
            album = line['album']
            title = line['title']
        except KeyError:
            pass

        stderr_print('%s - %s - %s' % (artist, album, title))
