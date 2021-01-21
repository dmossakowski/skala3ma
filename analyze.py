

import json
import os
import random
from datetime import datetime, date, time, timedelta
import numpy as np
import pandas as pd
import numpy.random
from collections import Counter
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import plotly
import plotly.graph_objects as go
import plotly.express as px

from sklearn.cluster import KMeans

from collections import defaultdict

from matplotlib.figure import Figure
from sklearn.preprocessing import MinMaxScaler


def getEmptyLibrary():
    library = {}
    library['tracks'] = []
    library['albums'] = []
    library['playlists'] = []
    library['audio_features'] = []
    library['toptracks_short_term'] = []
    library['topartists_short_term'] = []
    library['toptracks_medium_term'] = []
    library['topartists_medium_term'] = []
    library['toptracks_long_term'] = []
    library['topartists_long_term'] = []
    return library

def getLibrarySize(library):
    s = ''
    if library is None:
        return s
    if library.get('playlists'):
        s = s + ' Playlists: '+str(len(library.get('playlists')))
    if library.get('albums'):
        s = s + ', Albums: '+str(len(library.get('albums')))
    if library.get('tracks'):
        s = s + ', Tracks: ' + str(len(library.get('tracks')))
    if library.get('audio_features'):
        s = s + ', Audio features: '+str(len(library.get('audio_features')))
    if library.get('toptracks_medium_term'):
            s = s + ', Top tracks: ' + str(len(library.get('toptracks_medium_term')))
    if library.get('topartists_medium_term'):
            s = s + ', Top artists: ' + str(len(library.get('topartists_medium_term')))

    return s


def getTopGenreSet(library):
    genres = []
    cnt = Counter()

    if library is None:
        return genres

    for track in library.get('topartists_medium_term'):
        genres.extend(track.get('genres'))

    for word in genres:
        cnt[word] += 1

    mostcommon=[]
    c=11
    # put the weight as the second param instead of number of time it appears
    for i, mc in enumerate(cnt.most_common(c)):
        mostcommon.append([mc[0],c-i])
    #return cnt.most_common(12)
    return mostcommon


def loadLibraryFromFiles(directory="data/"):
    library = {}

    if not os.path.exists(directory):
        return None

    if not os.path.exists(directory+"tracks.json"):
        return None

    if not os.path.exists(directory+"audio_features.json"):
        return None

    if not os.path.exists(directory+"topartists_medium_term.json"):
        return None

    # Dream database. Store dreams in memory for now.
    dreamsA = ['Python. Python, everywhere.']
    numberA = 10
    strA = "someString"

    #path = "data/"
    path = directory

    with open(path+"tracks.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['tracks'] = tracks

    with open(path+"albums.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['albums'] = tracks

    with open(path+"playlists.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['playlists'] = tracks

    with open(path + "toptracks_long_term.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['toptracks_long_term'] = tracks

    with open(path + "toptracks_medium_term.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['toptracks_medium_term'] = tracks

    with open(path + "toptracks_short_term.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['toptracks_short_term'] = tracks

    with open(path + "topartists_long_term.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['topartists_long_term'] = tracks

    with open(path + "topartists_medium_term.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['topartists_medium_term'] = tracks

    with open(path + "topartists_short_term.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['topartists_short_term'] = tracks

        library['audio_features'] = loadAudioFeatures(path)

    return library


def loadAudioFeatures(path="data/"):
    with (open(path+'audio_features.json', "r")) as f:
        data = json.load(f)
        return data


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
    #print (len(artistsByDate))
    for key in sortedA:
        #print (key, str(len(artistsByDate[key])))
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




# returns tracks of artists who have been added but whose albums were never added
# ordered by time added
def getOrphanedTracks(library):
    artistsByDate = defaultdict(list)
    artistsRanking = {} #defaultdict(list)

    epoch = datetime.utcfromtimestamp(0)
    now = datetime.now()
    tracksbydate = {}
    trackA = library['tracks']
    alltracks = []
    c = 0

    # ["track"]["artists"][0]['name']
    albumArtists = []
    for album in library['albums']:
        albumArtists.append(album['album']['artists'][0]['name'])

    albumArtists = set(albumArtists)



    for track in library['tracks']:
        artist = track["track"]["artists"][0]['name']

        if artist in albumArtists:
                continue

        dt = datetime.strptime(track["added_at"], "%Y-%m-%dT%H:%M:%SZ")

        track['track']['dateaddedDisplay'] =  dt.strftime('%B %Y')
        #rec["age"] = (now - dt).total_seconds()

        trackid = track["track"]["album"]["uri"]
        albumid = track["track"]["uri"]
        #print str(addedat)+" ||  "+trackname+" || "+artist
        #artistsByDate.setdefault(rec["addedat"], []).append(rec)
        #ss = rec["addedat"]

        #artistsByDate[rec["addedat"]].append(rec)

        #rank = { "songcount":1 , "albumcount":1, "addedcount":1 }
        #if rec["artist"] in artistsRanking:
        #    rank = artistsRanking[rec["artist"]]
        #    rank["songcount"] = rank["songcount"] + 1
        #else:
        #    artistsRanking[rec["artist"]] = { "songcount":1 , "albumcount":1, "addedcount":1 }

        #c = c+1
        alltracks.append(track)

    alltracks = sorted(alltracks, key=lambda k: k['added_at'], reverse=True)

    return alltracks


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


def create_figureTest():
    X = [1, 2, 3, 4]
    Ys = np.array([[4, 8, 12, 16],
                   [1, 4, 9, 16],
                   [17, 10, 13, 18],
                   [9, 10, 18, 11],
                   [4, 15, 17, 6],
                   [7, 10, 8, 7],
                   [9, 0, 10, 11],
                   [14, 1, 15, 5],
                   [8, 15, 9, 14],
                   [20, 7, 1, 5]])
    nCols = len(X)
    nRows = Ys.shape[0]

    colors = cm.rainbow(np.linspace(0, 1, len(Ys)))

    cs = [colors[i // len(X)] for i in range(len(Ys) * len(X))]  # could be done with numpy's repmat
    Xs = X * nRows  # use list multiplication for repetition
    plt.scatter(Xs, Ys.flatten(), color=cs)
    plt.figure(2)

    plt.clf()
    #plt.imshow(heatmap.T, extent=extent, origin='lower')
    plt.show()


def create_figure():
    dataOrig = loadAudioFeatures()
    fullLib = loadLibraryFromFiles()
    # list: 3799 of dict:18
    # [{'danceability': 0.469, 'energy': 0.625, 'key': 4, 'loudness': -5.381, 'mode': 0, 'speechiness': 0.0306, 'acousticness': 0.00515, 'instrumentalness': 2.03e-05, 'liveness': 0.0682, 'valence': 0.325, 'tempo': 76.785, 'type': 'audio_features', 'id': '6PBzdsMi6YNdYAevzozBRi', 'uri': 'spotify:track:6PBzdsMi6YNdYAevzozBRi', 'track_href': 'https://api.spotify.com/v1/tracks/6PBzdsMi6YNdYAevzozBRi', 'analysis_url': 'https://api.spotify
    #  {'danceability': 0.76, 'energy': 0.608, 'key': 9, 'loudness': -8.673, 'mode': 0, 'speechiness': 0.0347, 'acousticness': 0.315, 'instrumentalness': 0.79, 'liveness': 0.121, 'valence': 0.727, 'tempo': 119.032, 'type': 'audio_features', 'id': '4dJYJTPbUgFK5pCQ5bYD4g', 'uri': 'spotify:track:4dJYJTPbUgFK5pCQ5bYD4g', 'track_href': 'https://api.spotify.com/v1/tracks/4dJYJTPbUgFK5pCQ5bYD4g', 'analysis_url': 'https://api.spotify.com/v1/audio-analysis/4dJYJTPbUgFK5pCQ5bYD4g', 'duration_ms': 254118, 'time_signature': 4}
    #  {'danc..
    dtype= [('danceability', '<f8'), ('energy', '<f8'), ('key', '<f8'), ('loudness', '<f8'), ('mode', '<f8'),
            ('speechiness', '<f8'), ('acousticness', '<f8'), ('instrumentalness', '<f8'), ('liveness', '<f8'), ('valence', '<f8'),
            ('tempo', '<f8'), ('type', '<f8'), ('id', '<f8'), ('duration_ms', '<f8'), ('time_signature', '<f8'), ]

    keys = ['danceability', 'energy', 'key', 'loudness', 'mode','speechiness','acousticness', 'instrumentalness']
    #keys = ['danceability', 'energy', 'loudness']
    #keys = ['danceability', 'energy']

    # ('danceability','energy','key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness',
    #      'valence', 'tempo'):

    dataArray = []
    for key in dataOrig[0]:
        if key in keys:
            #data[key] = [li[key] for li in dataOrig]
            dataArray.append([li[key] for li in dataOrig])

    # dataArray list:8  3799
    # one row per audio feature
    # [[0.469, 0.76, 0.598, 0.706, 0.756, 0.555, 0.53, 0.716, 0.481, 0.415, 0.684, 0.593, 0.395, 0.487, 0.671, 0.691, 0.155, 0.61, 0.171, 0.203, 0.181,
    #  [0.625, 0.608, 0.509, 0.653, 0.549, 0.71, 0.362, 0.685, 0.491, 0.42, 0.62, 0.626, 0.704, 0.757, 0.603, 0.669, 0
    #  [4, 9, 9, 7, 7, 10, 5, 4, 11, 3, 0, 4, 5, 0, 4, 1, 10, 11, 7, 2, 10, 10, 10, 0, 8, 9, 11, 6, 11, 6, 10, 1, 0, 3, 0,

    dataArray = np.array(dataArray)

    # call MinMaxScaler object
    min_max_scaler = MinMaxScaler()
    # feed in a numpy array
    minmaxscaled = min_max_scaler.fit_transform(dataArray)
    # wrap it up if you need a dataframe
    #df = pd.DataFrame(X_train_norm)

    dataArrayMean = np.mean(dataArray)
    dataArrayStd = np.std(dataArray)
    allsongsstandardized = (dataArray - dataArrayMean) / dataArrayStd

    X_train_norm = allsongsstandardized
    X_train_norm = np.flip(np.rot90(X_train_norm, 1))

    #allsongs = []
    #for songOrig in dataArray:
    #    song = []
    #    for key in keys:
    #        song.append(dataArray[key])
    #    allsongs.append(song)

    # allsongs: list:3799 x 8\
    # one row per song
    #[[0.469, 0.625, 4, -5.381, 0, 0.0306, 0.00515, 2.03e-05],
    # [0.76, 0.608, 9, -8.673, 0, 0.0347, 0.315, 0.79],
    # [0.598, 0.509, 9, -9.719, 1, 0.0269, 0.593, 0.0503],

    #X1 = np.array(dataArray)
    #y = np.array(dataArray2)

    #kmeans = KMeans(algorithm='auto', copy_x=True, init='k-means++', max_iter=3000,
     #      n_clusters=5, n_init=10, n_jobs=1, precompute_distances='auto',
      #     random_state=None, tol=0.0001, verbose=0)
    kmeans = KMeans(n_clusters=17)
    kmeans.fit(X_train_norm)


    predict = kmeans.predict(X_train_norm)
    #data['cluster'] = predict

    fig = go.Figure(data=X_train_norm.__array__())
    fig.write_html('first_figure.html', auto_open=True)

    pd.plotting.parallel_coordinates(pd.array(X_train_norm),0)
    plt.show()
    #print(numpy.info(X1))

    centroids = kmeans.cluster_centers_
    correct = 0
    #for i in range(len(X1)):
    #    predict_me = np.array(X1[i].astype(float))
    #    predict_me = predict_me.reshape(-1, len(predict_me))
    #    prediction = kmeans.predict(predict_me)
    #    print(prediction[0])

    #print(correct / len(X1))
    X2 = dataArray[0]

    nCols = len(X2)
    nRows = dataArray.shape[0]

    colors = cm.rainbow(np.linspace(0, 1, len(dataArray)))

    cs1 = [colors[i // len(dataArray)] for i in range(len(dataArray) * len(dataArray))]  # could be done with numpy's repmat
    cs2 = kmeans.labels_.astype(float)
    # cs3 = cs2 ** nRows
    #cs3 = np.repeat(cs2, nRows)
    #Xs1 = dataArray * nRows  # use list multiplication for repetition

    for i, center in enumerate(kmeans.cluster_centers_):
        j = i%len(X_train_norm[0])
        k = (i+1)%len(X_train_norm[0])
        plt.figure(i)
        plt.suptitle("scatterplot "+str(i)+" "+str(j)+":"+str(k))
        #plt.scatter(X_train_norm[:, j], X_train_norm[:, k], c=cs2, s=5, alpha=0.4)
        #plt.scatter(centroids[:,j], centroids[:,k], c='black', s=5)
        plt.plot(X_train_norm[:, j], 'r.', markersize=1)
        plt.plot(centroids[:,j], 'b.', markersize=2)


    #plt.scatter(X_train_norm[:, 0], X_train_norm[:, 1], c=cs2, s=5, alpha=0.4)
    #plt.scatter(X_train_norm[:, 0], X_train_norm[:, 2], c=cs2, s=5, alpha=0.4)

    #plt.plot(allsongsstandardized)
    #plt.figure(2)
    #plt.plot(dataArray[0],' r.', markersize=1)
    #plt.figure(3)
    #plt.plot(dataArray[1], 'b.', markersize=1)
    #plt.figure(4)
    #plt.plot(dataArray[2], 'y.', markersize=1)

    #plt.scatter(dataArray[0], dataArray[3], c="blue", alpha=0.1)

    #plt.figure(5)
    #plt.scatter(dataArray[0], dataArray[0], c="blue", alpha=0.1)

    #plt.subplot(321, label="one")
    #plt.hist(dataArray[0], bins=200)
    #plt.title("exess")
    #plt.subplot(322, label="two")
    #plt.hist(dataArray[1], bins=200)
    #plt.title("222222")
    #plt.subplot(323)
    #plt.hist(dataArray[2], bins=200)
    #plt.title("ex333333ess")

    #plt.scatter(Xs1[1], Ys[1], c="blue", alpha=0.1)

    #plt.scatter(Xs1, Ys.flatten(), color=cs)

    plt.grid(True)
    plt.show()


    clusteredSongs = [[] for i in range(kmeans.n_clusters)]
    for i, cluster in enumerate(cs2):
        songCluster = clusteredSongs[int(cluster)]
        track = next((item for item in fullLib['tracks'] if item['track']['id'] == dataOrig[i]['id']), None)
        if (track is not None):
            songCluster.append({**track,**dataOrig[i]})
            #print(str(i)+' '+str(track['track']['artists'][0]['name'])+ ' - '+
            #      str(track['track']['album']['name'])+ ' - '+
             #     str(track['track']['name'])+' song '+str(dataOrig[i])+' ' )


    return plt.figure(3)



def dataofish():
    from pandas import DataFrame
    import matplotlib.pyplot as plt
    from sklearn.cluster import KMeans

    Data = {
        'x': [25, 34, 22, 27, 33, 33, 31, 22, 35, 34, 67, 54, 57, 43, 50, 57, 59, 52, 65, 47, 49, 48, 35, 33, 44, 45,
              38, 43, 51, 46],
        'y': [79, 51, 53, 78, 59, 74, 73, 57, 69, 75, 51, 32, 40, 47, 53, 36, 35, 58, 59, 50, 25, 20, 14, 12, 20, 5, 29,
              27, 8, 7]
        }

    df = DataFrame(Data, columns=['x', 'y'])

    kmeans = KMeans(n_clusters=3).fit(df)
    centroids = kmeans.cluster_centers_
    print(centroids)
    xs = df['x']
    ys = df['y']

    plt.scatter(df['x'], df['y'], c=kmeans.labels_.astype(float), s=50, alpha=0.5)
    plt.scatter(centroids[:, 0], centroids[:, 1], c='red', s=50)
    plt.show()


def create_figure_working():
    dataOrig = loadAudioFeatures()



    dtype= [('danceability', '<f8'), ('energy', '<f8'), ('key', '<f8'), ('loudness', '<f8'), ('mode', '<f8'),
            ('speechiness', '<f8'), ('acousticness', '<f8'), ('instrumentalness', '<f8'), ('liveness', '<f8'), ('valence', '<f8'),
            ('tempo', '<f8'), ('type', '<f8'), ('id', '<f8'), ('duration_ms', '<f8'), ('time_signature', '<f8'), ]

    data = {}
    dataArray = []
    for key in dataOrig[0]:
        if key in ('danceability', 'energy', 'key', 'loudness', 'mode','speechiness','acousticness', 'instrumentalness'):

            #('danceability','energy','key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness',
             #      'valence', 'tempo'):

            data[key] = [li[key] for li in dataOrig]
            dataArray.append([li[key] for li in dataOrig])


    Ys = np.array(dataArray)
    X = dataArray[0]


    #array = np.fromiter(data.iteritems(), dtype=dtype, count=len(data))

    #plt.figure(3)
    nCols = len(X)
    nRows = Ys.shape[0]

    colors = cm.rainbow(np.linspace(0, 1, len(Ys)))

    cs = [colors[i // len(X)] for i in range(len(Ys) * len(X))]  # could be done with numpy's repmat
    Xs = X * nRows  # use list multiplication for repetition
    plt.scatter(Xs, Ys.flatten(), color=cs)

    #plt.figure()

    #plt.clf()
    #plt.imshow(heatmap.T, extent=extent, origin='lower')
    plt.grid(True)
    plt.show()


    return plt.figure(3)




def create_figure11():
    # Generate some test data
    x = np.random.randn(8873)
    y = np.random.randn(8873)

    heatmap, xedges, yedges = np.histogram2d(x, y, bins=50)
    extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]

    plt.figure(3)
    plt.clf()
    plt.imshow(heatmap.T, extent=extent, origin='lower')
    #plt.show()
    return plt.figure(3)


def create_figure1():
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    xs = range(100)
    ys = [random.randint(1, 50) for x in xs]
    axis.plot(xs, ys)
    return fig



if __name__ == '__main__':
    library = loadLibraryFromFiles()

    getOrphanedTracks(library)
