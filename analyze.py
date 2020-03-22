

import json
import os
from datetime import datetime, date, time, timedelta

from collections import defaultdict


def loadLibraryFromFiles(directory="data/"):
    library = {}

    if not os.path.exists(directory):
        return None

    # Dream database. Store dreams in memory for now.
    dreamsA = ['Python. Python, everywhere.']
    numberA = 10
    strA = "someString"

    path = "data/"

    with open(path+"tracks.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['tracks'] = tracks

    with open(path+"albums.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['albums'] = tracks

    with open(path+"playlists.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['playlists'] = tracks

    return library



# orders artists by which had last added a song to
def process(library):
    artistsByDate = defaultdict(list)
    artistsRanking = {} #defaultdict(list)

    epoch = datetime.utcfromtimestamp(0)
    now = datetime.now()
    tracksbydate = {}
    trackA = library['tracks']
    alltracks = []
    c = 0
    for track in library['tracks']:
        rec = {}
        artists = track["track"]["artists"]
        rec["artist"] = artists[0]['name']
        rec["trackname"] = track["track"]["name"]
        rec["albumname"] = track["track"]["album"]["name"]
        rec["addedat"] = str(track["added_at"])
        dt = datetime.strptime(track["added_at"], "%Y-%m-%dT%H:%M:%SZ")
        rec["age"] = (now - dt).total_seconds()
        rec["type"] = "track"
        trackid = track["track"]["album"]["uri"]
        albumid = track["track"]["uri"]
        #print str(addedat)+" ||  "+trackname+" || "+artist
        #artistsByDate.setdefault(rec["addedat"], []).append(rec)
        ss = rec["addedat"]
        artistsByDate[rec["addedat"]].append(rec)

        #rank = { "songcount":1 , "albumcount":1, "addedcount":1 }
        if rec["artist"] in artistsRanking:
            rank = artistsRanking[rec["artist"]]
            rank["songcount"] = rank["songcount"] + 1
        else:
            artistsRanking[rec["artist"]] = { "songcount":1 , "albumcount":1, "addedcount":1 }

        c = c+1
        alltracks.append(rec)

    for album in library['albums']:
        rec = {}
        artists = album["album"]["artists"]
        rec["artist"] = artists[0]['name']
        rec["albumname"] = album["album"]["name"]
        rec["trackname"] = ""
        rec["addedat"] = album["added_at"]
        rec["type"] = "album"
        dt = datetime.strptime(track["added_at"], "%Y-%m-%dT%H:%M:%SZ")
        rec["age"] = (now - dt).total_seconds()
        #print str(addedat)+" ||  "+trackname+" || "+artist
        alltracks.append(rec)

    sortedA = artistsByDate.keys()
    sortedA = sorted(sortedA)
    print (len(artistsByDate))
    for key in sortedA:
        print (key, str(len(artistsByDate[key])))
        for rec in artistsByDate[key]:
            printinfo = (rec['artist']).encode('utf-8')
            #popularity = str(artistsByDate[key][0]['track']['popularity'])
            trackname = (rec['trackname']).encode('utf-8')
            albumname = (rec['albumname']).encode('utf-8')
            #print '-- ', rec["type"], printinfo, 'album:', albumname, ' track: ', trackname, rec["addedat"], rec["age"]

            #printinfo = (artistsByDate[key]['artist']).encode('utf-8')
            ##popularity = str(artistsByDate[key][0]['track']['popularity'])
            #trackname = (artistsByDate[key]['trackname']).encode('utf-8')
            #printinfo2 = str(len(artistsByDate[key]))
            #print '-- ', printinfo, trackname, printinfo2

    #return sortedA
    return artistsByDate



def getIds(library):
    artistsByDate = defaultdict(list)
    artistsRanking = {} #defaultdict(list)

    epoch = datetime.utcfromtimestamp(0)
    now = datetime.now()
    tracksbydate = {}
    trackA = library['tracks']
    alltracks = []
    c = 0
    for track in library['tracks']:
        rec = {}
        artists = track["track"]["artists"]
        rec["artist"] = artists[0]['name']
        rec["trackname"] = track["track"]["name"]
        rec["albumname"] = track["track"]["album"]["name"]
        rec["addedat"] = str(track["added_at"])
        dt = datetime.strptime(track["added_at"], "%Y-%m-%dT%H:%M:%SZ")
        rec["age"] = (now - dt).total_seconds()
        rec["type"] = "track"
        trackid = track["track"]["album"]["uri"]
        albumid = track["track"]["uri"]
        #print str(addedat)+" ||  "+trackname+" || "+artist
        #artistsByDate.setdefault(rec["addedat"], []).append(rec)
        ss = rec["addedat"]
        artistsByDate[rec["addedat"]].append(rec)

        #rank = { "songcount":1 , "albumcount":1, "addedcount":1 }
        if rec["artist"] in artistsRanking:
            rank = artistsRanking[rec["artist"]]
            rank["songcount"] = rank["songcount"] + 1
        else:
            artistsRanking[rec["artist"]] = { "songcount":1 , "albumcount":1, "addedcount":1 }

        c = c+1
        alltracks.append(rec)







def modify(nam=["default"]):
    print ("Adding "+str(nam))
    print ("Dreams are " + str(dreamsA))
    dreamsA.append(nam)

    #dreamsA = ["a","b"]
    print ("Dreams are "+str(dreamsA))
    #print "numberA="+str(strA)
    #strA = "llll"


