from mpd import MPDClient
import sys

sys.argv[4] = sys.argv[4].upper()

client = MPDClient()

con_id = {'host':'localhost','port':'6600'}

client.connect{**con_id}

if sys.argv[4].find("NEXT") != -1:
    client.next()

if sys.argv[4].find("PREV") != -1:
    client.previous()

if sys.argv[4].find("PLAY") != -1:
    client.play()

if sys.argv[4].find("PAUSE") != -1:
    client.pause()

#TODO add volume control
#TODO add stats
#TODO add error handling and help
