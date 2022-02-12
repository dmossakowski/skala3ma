import calendar
from datetime import datetime, date, time, timedelta
import numpy as np
import plotly.graph_objects as go
import datetime
import functools as functools
from sklearn.preprocessing import MinMaxScaler
import logging

import analyze

from sklearn.cluster import KMeans
from functools import lru_cache


def cache_clear():
    logging.info(" create_top_artists_graph cache_info:" + str(create_top_artists_graph.cache_info()))
    create_top_artists_graph.cache_clear()
    logging.info(" create_dataseries cache_info:" + str(create_dataseries.cache_info()))
    create_dataseries.cache_clear()


def _getFeatures(dataPath, keys=['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness',
                                 'instrumentalness', 'liveness',
                                 'valence', 'tempo']):
    dataOrig = analyze.loadAudioFeatures(dataPath)
    #fullLib = analyze.loadLibraryFromFiles(dataPath)
    # list: 3799 of dict:18
    # [{'danceability': 0.469, 'energy': 0.625, 'key': 4, 'loudness': -5.381, 'mode': 0, 'speechiness': 0.0306, 'acousticness': 0.00515, 'instrumentalness': 2.03e-05, 'liveness': 0.0682, 'valence': 0.325, 'tempo': 76.785, 'type': 'audio_features', 'id': '6PBzdsMi6YNdYAevzozBRi', 'uri': 'spotify:track:6PBzdsMi6YNdYAevzozBRi', 'track_href': 'https://api.spotify.com/v1/tracks/6PBzdsMi6YNdYAevzozBRi', 'analysis_url': 'https://api.spotify
    #  {'danceability': 0.76, 'energy': 0.608, 'key': 9, 'loudness': -8.673, 'mode': 0, 'speechiness': 0.0347, 'acousticness': 0.315, 'instrumentalness': 0.79, 'liveness': 0.121, 'valence': 0.727, 'tempo': 119.032, 'type': 'audio_features', 'id': '4dJYJTPbUgFK5pCQ5bYD4g', 'uri': 'spotify:track:4dJYJTPbUgFK5pCQ5bYD4g', 'track_href': 'https://api.spotify.com/v1/tracks/4dJYJTPbUgFK5pCQ5bYD4g', 'analysis_url': 'https://api.spotify.com/v1/audio-analysis/4dJYJTPbUgFK5pCQ5bYD4g', 'duration_ms': 254118, 'time_signature': 4}
    #  {'danc..
    dtype = [('danceability', '<f8'), ('energy', '<f8'), ('key', '<f8'), ('loudness', '<f8'), ('mode', '<f8'),
             ('speechiness', '<f8'), ('acousticness', '<f8'), ('instrumentalness', '<f8'), ('liveness', '<f8'),
             ('valence', '<f8'),
             ('tempo', '<f8'), ('type', '<f8'), ('id', '<f8'), ('duration_ms', '<f8'), ('time_signature', '<f8'), ]

    # ('danceability','energy','key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness',
    #      'valence', 'tempo'):

    dataArray = []

    if len(dataOrig) == 0:
        return dataArray

    dummyLine = {'danceability': 0, 'energy': 0, 'key': 8, 'loudness': -8, 'mode': 1, 'speechiness': 0,
     'acousticness': 0, 'instrumentalness': 0, 'liveness': 0, 'valence': 0, 'tempo': 102,
     'type': 'audio_features', 'id': 'dummyTrack', 'uri': 'spotify:track:dummyTrack',
     'track_href': 'https://api.spotify.com/v1/dummytrack',
     'analysis_url': 'https://api.spotify.com/v1/audio-analysis/dummytrack', 'duration_ms': 666,
     'time_signature': 4}


    for key in dataOrig[0]:
        if key in keys:
            # data[key] = [li[key] for li in dataOrig]
            for i,li in enumerate(dataOrig):
                #print (str(key)+str(li))
                if li is None:
                    dataOrig[i] = dummyLine
            t = [li[key] for li in dataOrig]

            dataArray.append(t)

    return dataArray


def _getTrackTuples(dataPath):
    fullLib = analyze.loadLibraryFromFiles(dataPath)

    # dataArray list:8  3799
    # one row per audio feature
    # [[0.469, 0.76, 0.598, 0.706, 0.756, 0.555, 0.53, 0.716, 0.481, 0.415, 0.684, 0.593, 0.395, 0.487, 0.671, 0.691, 0.155, 0.61, 0.171, 0.203, 0.181,
    #  [0.625, 0.608, 0.509, 0.653, 0.549, 0.71, 0.362, 0.685, 0.491, 0.42, 0.62, 0.626, 0.704, 0.757, 0.603, 0.669, 0
    #  [4, 9, 9, 7, 7, 10, 5, 4, 11, 3, 0, 4, 5, 0, 4, 1, 10, 11, 7, 2, 10, 10, 10, 0, 8, 9, 11, 6, 11, 6, 10, 1, 0, 3, 0,

    datesadded = []
    artists = []

    # date_time_str = '2020-02-16T19:54:58Z'
    # date_time_obj = datetime.datetime.strptime(date_time_str, '%Y-%m-%dT%H:%M:%SZ')
    dataSeries = []
    for i, item in enumerate(fullLib['tracks']):
        dataSeriesItem = []
        ts = datetime.datetime.strptime(item['added_at'], '%Y-%m-%dT%H:%M:%SZ')
        weekday = calendar.day_name[ts.weekday()]
        artist = fullLib['tracks'][i]['track']['artists'][0]['name']
        trackname = fullLib['tracks'][i]['track']['name']

        # print(str(i)+' '+str(track['track']['artists'][0]['name'])+ ' - '+
        #      str(track['track']['album']['name'])+ ' - '+
        #     str(track['track']['name'])+' song '+str(dataOrig[i])+' ' )
        # datesadded.append(ts)
        # artists.append(artist)
        # dataSeries.append((ts,artist,weekday))
        # print(str(i) + " " + str(item))
        # dataSeries.append(dataArray[i])
        dataSeriesItem.append(ts)
        dataSeriesItem.append(str(ts)+" - " + str(i) + " - " + artist + " - " + trackname)
        dataSeriesItem.append(weekday)
        dataSeries.append(dataSeriesItem)

    # dataSeries.append(datesadded)
    # dataSeries.append(artists)

    # dataArray.insert(0,dataSeries)
    # 2020-02-16T19:54:58Z
    return dataSeries


# this is called from Audio Features Graph
#
def create_dataseriesOrig(dataPath):
    keys = ['danceability', 'energy', 'key', 'loudness', 'speechiness', 'acousticness', 'instrumentalness']
    keys = ['danceability', 'energy', 'key', 'loudness', 'valence', 'speechiness', 'tempo', 'time_signature']
    keys = ['danceability', 'energy', 'key', 'loudness', 'valence', 'speechiness', 'tempo']

    # keys = ['danceability', 'energy', 'loudness']
    # keys = ['danceability', 'energy']

    dataToDisplay = _getFeatures(dataPath, keys)
    dataToDisplay = np.array(dataToDisplay)

    # this is an array [[0.1,0.2,0.3][1,2,3,4]etc..
    reshapen = dataToDisplay[2].reshape(-1, 1)

    # call MinMaxScaler object
    min_max_scaler = MinMaxScaler()
    # feed in a numpy array

    dataToDisplay[2] = min_max_scaler.fit_transform(dataToDisplay[2].reshape(-1, 1)).reshape(-1)
    dataToDisplay[3] = min_max_scaler.fit_transform(dataToDisplay[3].reshape(-1, 1)).reshape(-1)
    dataToDisplay[6] = min_max_scaler.fit_transform(dataToDisplay[6].reshape(-1, 1)).reshape(-1)

    # keyNormalized2 = keyNormalized.reshape(-1)

    # dataToDisplay = min_max_scaler.fit_transform(dataToDisplay)

    dataSeries = np.array(_getTrackTuples(dataPath))

    fig = go.Figure()

    for i, key in enumerate(keys):
        fig.add_trace(go.Scattergl(x=dataSeries[:, 0], y=dataToDisplay[i],
                                   mode="lines+markers",
                                   marker_symbol='diamond-wide',
                                   marker=dict(
                                       colorscale='Viridis',
                                       line_width=0,
                                       opacity=0.6,
                                       size=8
                                   ),
                                   name=keys[i],
                                   hoverinfo="text",
                                   hovertext=dataSeries[:, 1]))

    graphJSON = fig.to_json()
    return graphJSON

    # return fig


# this is called from Audio Features Graph
#
@lru_cache(maxsize=128)
def create_dataseries(dataPath):
    keys = ['danceability', 'energy', 'key', 'loudness', 'speechiness', 'acousticness', 'instrumentalness']
    keys = ['danceability', 'energy', 'key', 'loudness', 'valence', 'speechiness', 'tempo', 'time_signature']
    keys = ['danceability', 'energy', 'key', 'loudness', 'valence', 'speechiness', 'tempo']

    # keys = ['danceability', 'energy', 'loudness']
    # keys = ['danceability', 'energy']

    dataToDisplay = _getFeatures(dataPath, keys)
    dataToDisplay = np.array(dataToDisplay)

    # this is an array [[0.1,0.2,0.3][1,2,3,4]etc..
    reshapen = dataToDisplay[2].reshape(-1, 1)

    # call MinMaxScaler object
    min_max_scaler = MinMaxScaler()
    # feed in a numpy array

    dataToDisplay[2] = min_max_scaler.fit_transform(dataToDisplay[2].reshape(-1, 1)).reshape(-1)
    dataToDisplay[3] = min_max_scaler.fit_transform(dataToDisplay[3].reshape(-1, 1)).reshape(-1)
    dataToDisplay[6] = min_max_scaler.fit_transform(dataToDisplay[6].reshape(-1, 1)).reshape(-1)

    # keyNormalized2 = keyNormalized.reshape(-1)

    # dataToDisplay = min_max_scaler.fit_transform(dataToDisplay)

    dataSeries = np.array(_getTrackTuples(dataPath))
    dataSeriesMsk =[]
    fig = go.Figure()

    lastTs = dataSeries[0:0]
    lastIndex = 0

    dataSeriesMskA = []
    dataSeriesMsk = np.array(dataSeriesMskA)

    #dataSeriesMsk.append(dataToDisplay[0][dataToDisplay[0] != 1])
    u = np.array([])
    for i, key in enumerate(keys):
        #dataSeriesMsk.append(dataToDisplay[i][dataToDisplay[i] != 1])
        p = dataToDisplay[i]
        #s = r != 1
        r = [p == 0, p == 1]
        #s1 = np.where(r)
        s = functools.reduce(np.logical_or, r)
        #s = np.concatenate(r % 1 == 1)
        t1 = np.where(s)
        t = t1[0]
        u = np.append(u, t)
        #dataSeriesMsk = np.concatenate(dataSeriesMsk, t)

    #u = np.sort(u)
    dataToDisplay = np.delete(dataToDisplay, u, 1)
    dataSeries = np.delete(dataSeries, u, 0)

        #for j, value in enumerate(dataToDisplay[i]):
            #dataToDisplay[i] = value[value != 1]

        #dataSeries = np.delete(dataSeries, dataSeriesMsk, axis=0)
        #dataToDisplay = np.delete(dataToDisplay, dataSeriesMsk)
        #dataToDisplay = np.delete(dataToDisplay, dataSeriesMsk, axis=2)
    logging.info(" removed " )
    #dataToDisplay = np.delete(dataToDisplay, dataSeriesMsk)
    #for i, item in enumerate(dataSeries):
     #   for j, key in enumerate(keys):
      #      if dataToDisplay[j][i]==0 or dataToDisplay[j][i]==1:



       # if lastTs != item[0]:
        #    count = i - lastIndex
         #   np.median()


    for i, key in enumerate(keys):
        fig.add_trace(go.Scattergl(x=dataSeries[:, 0], y=dataToDisplay[i],
                                   mode="markers",
                                   marker_symbol='diamond-wide',
                                   marker=dict(
                                       colorscale='Viridis',
                                       line_width=0,
                                       opacity=0.6,
                                       size=8
                                   ),

                                   name=keys[i],
                                   hoverinfo="text",
                                   hovertext=dataSeries[:, 1]))

    graphJSON = fig.to_json()
    return graphJSON




# this is called to create favorite artists graph
@lru_cache(maxsize=128)
def create_top_artists_graph(dataPath):
    fullLib = analyze.loadLibraryFromFiles(dataPath)

    topartists = []

    topartists.append([art['name'] for i, art in enumerate(fullLib['topartists_long_term'])][:50])
    topartists.append([art['name'] for art in fullLib['topartists_medium_term']][:50])
    topartists.append([art['name'] for art in fullLib['topartists_short_term']][:20])

    #topartists = np.array(topartists)
    #topartists = topartists.reshape(-1,1)
    topartistsranking = []
    topartistsrankingM = {}

    for i, artistlist in enumerate(topartists):
        topartistsranking.append([])
        for j, artist in enumerate(artistlist):
            topartistsrankingM.setdefault(artist, [None, None, None])

    for i in range(50):
        for j in range(3):
            artist = topartists[j][i:i+1]
            if len(artist) > 0:
                a = topartistsrankingM.get(artist[0])
                a[j] = i+1 # so that most favorite artist is at position 1 instead of 0

    #print(' done')

    #colors = [plotly.colors.DEFAULT_PLOTLY_COLORS[random.randrange(1, 10)] for i in range(len(topartistsrankingM))]
    color = ('rgba(' + str(np.random.randint(0, high=200)) + ',' +
             str(np.random.randint(0, high=250)) + ',' +
             str(np.random.randint(0, high=100)))

    colors = ['rgba(200,121,121','rgba(60,121,60','rgba(121,60,256','rgba(33,33,33',
              'rgba(200,180,60','rgba(121,200,33','rgba(33,121,255','rgba(121,66,33',
              'rgba(255,60,121', 'rgba(33,170,121', 'rgba(0,66,66', 'rgba(121,66,121',
              'rgba(255,60,0', 'rgba(33,155,0', 'rgba(66,200,0', 'rgba(121,66,0',
              'rgba(255,0,33','rgba(66,121,255','rgba(66,66,255','rgba(66,200,200']


    #weights = [random.randint(15, 35) for i in range(50)]
    xaxis = ['Long Term (several years)','Medium Term (last six months)', 'Very recent (last four weeks)']
    data = []
    for i, (artist, yaxis)  in enumerate(topartistsrankingM.items()):
        #weights2 = [*range(11, len(topartistsrankingM)+5)]
        #weights3 = [x/2 for x in range(1,len(topartistsrankingM))]
        weights2 = 10
        #color = colors[i % len(colors)]
        red = 200*((len(topartistsrankingM)-i)/len(topartistsrankingM))
        color = ('rgba(' + str(red) + ',' + \
                 str(np.random.randint(0, high=100)) + ',' + \
                 str(np.random.randint(0, high=120)))
        #color = yaxis
        #visibletrace = 'legendonly'
        yaxisStrings = yaxis.copy()
        for i,y in enumerate(yaxisStrings):
            if y is None:
                yaxisStrings[i] = '--'
            else:
                yaxisStrings[i] = str(yaxis[i])

        hovertemplatetext = '<b>' + artist + ' </b><br>All time popularity: ' + yaxisStrings[0] + \
               '<br>In the last six months: ' + yaxisStrings[1] + '<br>Recently: ' + yaxisStrings[2] + \
               '<extra></extra>'
        if len(list(filter(None, yaxis))) > 1:
            visibletrace = True
            mode = "markers+text+lines"
            text = ['<b>'+artist+'</b>','<b>'+artist+'</b>','<b>'+artist+'</b>']
            hovertemplate=hovertemplatetext
            marker = {'opacity': 0.1, 'size': 11, 'symbol': 'diamond-wide-dot'}
        else:
            mode = "markers+lines"
            text= ''
            visibletrace = True
            hovertemplate=hovertemplatetext
            marker = {'opacity': 0.7, 'size': 11, 'symbol': 'diamond-wide-dot'}
        #print("")

        data.append(go.Scatter(x=xaxis, y=yaxis,
                                mode=mode,
                                marker=marker,
                                line={'color':color+',0.5)', 'width':1, 'dash':'dot'},
                               #line={'width': 1, 'dash': 'dot'},
                                name = artist,
                                #hoverinfo='text',
                                text=text,
                                #hovertext = text,
                               hovertemplate=hovertemplate,
                               #color=color,
                                textfont={'size': weights2, 'color': color+',1)'},
                               #textfont={'size': weights2},
                               visible=visibletrace
                               )
                    )

    tickvals = [1,5,10,15,20,25,30,35,40,45,50]
    ticktext = ['1', '5', '10', 'Seven', 'Nine', 'Eleven']

    default_linewidth = 2
    highlighted_linewidth_delta = 2
    layout = go.Layout({'title':'Change of artist popularity over time',
                        'font':{ 'size':15},
                        'xaxis': {'showgrid': False, 'showticklabels': True, 'zeroline': False},
                        'yaxis': {'showgrid': True, 'showticklabels': True, 'zeroline': False,
                                  'autorange':'reversed',
                                  #'tick0':1, 'dtick':'2', 'nticks':10,
                                  'tickvals': tickvals,
                                  #'tickmode':'array', 'tickvals':tickvals, 'ticktext':ticktext
                                  },
                        'legend':{ 'font':{ 'size':11 }},
                        'hovermode':'y',
                        'hoverlabel_align' : 'right',
                        #'width' : 1200,
                        'height' : 750,
                        'margin' : { 'l':50, 'r':50, 'b':50, 't':80,'pad':4 }
    })

    #fig = go.Figure(data=data, layout=layout)
    #fig.update_yaxes(automargin=True)
    #fig.update_traces(textposition='top right')

    fig = go.FigureWidget(data=data, layout=layout)
    fig.layout.hovermode = 'closest'
    fig.layout.hoverdistance = -1  # ensures no "gaps" for selecting sparse data

    #fig.show()
    graphJSON = fig.to_json()
    return graphJSON



def create_graphPerDay():
    keys = ['danceability', 'energy', 'key', 'loudness', 'speechiness', 'acousticness', 'instrumentalness']
    keys = ['danceability', 'energy', 'key', 'loudness', 'valence', 'speechiness', 'tempo', 'time_signature']
    # keys = ['danceability', 'energy', 'loudness']
    # keys = ['danceability', 'energy']

    dataToDisplay = _getFeatures(keys)
    dataToDisplay = np.array(dataToDisplay)
    dataSeries = np.array(_getTrackTuples())

    fig = go.Figure()

    for i, key in enumerate(keys):
        # y=dataToDisplay[:, 1:len(dataToDisplay)],
        fig.add_trace(go.Scattergl(x=dataSeries[:, 0],
                                   y=dataToDisplay[i],
                                   mode="markers",
                                   # marker_symbol='line-ew',
                                   marker_symbol='diamond-wide',
                                   # marker=dict(size=[2,2,3,4,5,2,3,4] , color=[0,1,2,3,4,5,6,7,8,9])
                                   marker=dict(
                                       # color="blue",
                                       colorscale='Viridis',
                                       line_width=0,
                                       opacity=0.6,
                                       size=8
                                   )
                                   ,
                                   name=keys[i],
                                   hoverinfo="text",
                                   hovertext=dataSeries[:, 1]))

    graphJSON = fig.to_json()

    return graphJSON

    # return fig


def create_figure_backup():
    dataOrig = analyze.loadAudioFeatures()
    fullLib = analyze.loadLibraryFromFiles()
    # list: 3799 of dict:18
    # [{'danceability': 0.469, 'energy': 0.625, 'key': 4, 'loudness': -5.381, 'mode': 0, 'speechiness': 0.0306, 'acousticness': 0.00515, 'instrumentalness': 2.03e-05, 'liveness': 0.0682, 'valence': 0.325, 'tempo': 76.785, 'type': 'audio_features', 'id': '6PBzdsMi6YNdYAevzozBRi', 'uri': 'spotify:track:6PBzdsMi6YNdYAevzozBRi', 'track_href': 'https://api.spotify.com/v1/tracks/6PBzdsMi6YNdYAevzozBRi', 'analysis_url': 'https://api.spotify
    #  {'danceability': 0.76, 'energy': 0.608, 'key': 9, 'loudness': -8.673, 'mode': 0, 'speechiness': 0.0347, 'acousticness': 0.315, 'instrumentalness': 0.79, 'liveness': 0.121, 'valence': 0.727, 'tempo': 119.032, 'type': 'audio_features', 'id': '4dJYJTPbUgFK5pCQ5bYD4g', 'uri': 'spotify:track:4dJYJTPbUgFK5pCQ5bYD4g', 'track_href': 'https://api.spotify.com/v1/tracks/4dJYJTPbUgFK5pCQ5bYD4g', 'analysis_url': 'https://api.spotify.com/v1/audio-analysis/4dJYJTPbUgFK5pCQ5bYD4g', 'duration_ms': 254118, 'time_signature': 4}
    #  {'danc..
    dtype = [('danceability', '<f8'), ('energy', '<f8'), ('key', '<f8'), ('loudness', '<f8'), ('mode', '<f8'),
             ('speechiness', '<f8'), ('acousticness', '<f8'), ('instrumentalness', '<f8'), ('liveness', '<f8'),
             ('valence', '<f8'),
             ('tempo', '<f8'), ('type', '<f8'), ('id', '<f8'), ('duration_ms', '<f8'), ('time_signature', '<f8'), ]

    keys = ['danceability', 'energy', 'key', 'loudness', 'speechiness', 'acousticness', 'instrumentalness']
    keys = ['danceability', 'energy', 'key', 'loudness', 'valence', 'speechiness', 'tempo', 'time_signature']

    # keys = ['danceability', 'energy', 'loudness']
    # keys = ['danceability', 'energy']

    # ('danceability','energy','key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness',
    #      'valence', 'tempo'):

    dataArray = []
    for key in dataOrig[0]:
        if key in keys:
            # data[key] = [li[key] for li in dataOrig]
            dataArray.append([li[key] for li in dataOrig])

    # dataArray list:8  3799
    # one row per audio feature
    # [[0.469, 0.76, 0.598, 0.706, 0.756, 0.555, 0.53, 0.716, 0.481, 0.415, 0.684, 0.593, 0.395, 0.487, 0.671, 0.691, 0.155, 0.61, 0.171, 0.203, 0.181,
    #  [0.625, 0.608, 0.509, 0.653, 0.549, 0.71, 0.362, 0.685, 0.491, 0.42, 0.62, 0.626, 0.704, 0.757, 0.603, 0.669, 0
    #  [4, 9, 9, 7, 7, 10, 5, 4, 11, 3, 0, 4, 5, 0, 4, 1, 10, 11, 7, 2, 10, 10, 10, 0, 8, 9, 11, 6, 11, 6, 10, 1, 0, 3, 0,

    dataArray = np.array(dataArray)
    dataArrayMean = np.mean(dataArray)
    dataArrayStd = np.std(dataArray)
    allsongsstandardized = (dataArray - dataArrayMean) / dataArrayStd

    X_train_norm = allsongsstandardized
    X_train_norm = np.flip(np.rot90(X_train_norm, 3))

    dataToDisplay = np.flip(np.rot90(dataArray, 3))

    # allsongs = []
    # for songOrig in dataArray:
    #    song = []
    #    for key in keys:
    #        song.append(dataArray[key])
    #    allsongs.append(song)

    # allsongs: list:3799 x 8\
    # one row per song
    # [[0.469, 0.625, 4, -5.381, 0, 0.0306, 0.00515, 2.03e-05],
    # [0.76, 0.608, 9, -8.673, 0, 0.0347, 0.315, 0.79],
    # [0.598, 0.509, 9, -9.719, 1, 0.0269, 0.593, 0.0503],

    # X1 = np.array(dataArray)
    # y = np.array(dataArray2)

    # kmeans = KMeans(algorithm='auto', copy_x=True, init='k-means++', max_iter=3000,
    #      n_clusters=5, n_init=10, n_jobs=1, precompute_distances='auto',
    #     random_state=None, tol=0.0001, verbose=0)
    kmeans = KMeans(n_clusters=7)
    kmeans.fit(X_train_norm)

    predict = kmeans.predict(X_train_norm)
    # data['cluster'] = predict

    # df = px.data.gapminder().query("country=='Canada'")
    # fig = px.line(df, x="year", y="lifeExp", title='Life expectancy in Canada')
    # fig.show()

    # fig = go.Figure(data=X_train_norm.__array__())
    # fig.write_html('first_figure.html', auto_open=True)

    # fig = px.scatter(kmeans.cluster_centers_)
    # pd.plotting.parallel_coordinates(pd.array(X_train_norm),0)
    # plt.show()
    # print(numpy.info(X1))

    centroids = kmeans.cluster_centers_
    correct = 0
    # for i in range(len(X1)):
    #    predict_me = np.array(X1[i].astype(float))
    #    predict_me = predict_me.reshape(-1, len(predict_me))
    #    prediction = kmeans.predict(predict_me)
    #    print(prediction[0])

    # print(correct / len(X1))
    X2 = dataArray[0]

    nCols = len(X2)
    nRows = dataArray.shape[0]

    # colors = cm.rainbow(np.linspace(0, 1, len(dataArray)))

    # cs1 = [colors[i // len(dataArray)] for i in range(len(dataArray) * len(dataArray))]  # could be done with numpy's repmat
    cs2 = kmeans.labels_.astype(float)
    # cs3 = cs2 ** nRows
    # cs3 = np.repeat(cs2, nRows)
    # Xs1 = dataArray * nRows  # use list multiplication for repetition

    fig = go.Figure()

    # fig.add_trace(go.Scatter(x=dataArray[0], y=dataArray[1] ** 2, mode='markers', marker_color=cs2))
    # fig.show()

    fig = go.Figure(data=go.Splom(
        dimensions=[dict(label=keys[0],
                         values=dataToDisplay[:, 0]),
                    dict(label=keys[1],
                         values=dataToDisplay[:, 1]),
                    dict(label=keys[2],
                         values=dataToDisplay[:, 2]),
                    dict(label=keys[3],
                         values=dataToDisplay[:, 3]),
                    dict(label=keys[4],
                         values=dataToDisplay[:, 4]),
                    dict(label=keys[5],
                         values=dataToDisplay[:, 5]),
                    dict(label=keys[6],
                         values=dataToDisplay[:, 6]),
                    dict(label=keys[7],
                         values=dataToDisplay[:, 7])
                    ],

        marker=dict(color=cs2,
                    showscale=False,  # colors encode categorical variables
                    line_color='white', line_width=0.5)
    ))
    fig.show()

    for i, center in enumerate(kmeans.cluster_centers_):
        j = i % len(X_train_norm[0])
        k = (i + 1) % len(X_train_norm[0])
        # plt.figure(i)
        # plt.suptitle("scatterplot "+str(i)+" "+str(j)+":"+str(k))
        # plt.scatter(X_train_norm[:, j], X_train_norm[:, k], c=cs2, s=5, alpha=0.4)
        # plt.scatter(centroids[:,j], centroids[:,k], c='black', s=5)
        fig.add_trace(go.Scatter(x=X_train_norm[:, j], y=np.arange(min(X_train_norm[:, j]), max(X_train_norm[:, j])),
                                 mode='lines'))
        # fig.add_trace(go.Scatter(centroids[:,j], 'b.', markersize=2))

    fig.show()

    # plt.scatter(X_train_norm[:, 0], X_train_norm[:, 1], c=cs2, s=5, alpha=0.4)
    # plt.scatter(X_train_norm[:, 0], X_train_norm[:, 2], c=cs2, s=5, alpha=0.4)

    # plt.plot(allsongsstandardized)
    # plt.figure(2)
    # plt.plot(dataArray[0],' r.', markersize=1)
    # plt.figure(3)
    # plt.plot(dataArray[1], 'b.', markersize=1)
    # plt.figure(4)
    # plt.plot(dataArray[2], 'y.', markersize=1)

    # plt.scatter(dataArray[0], dataArray[3], c="blue", alpha=0.1)

    # plt.figure(5)
    # plt.scatter(dataArray[0], dataArray[0], c="blue", alpha=0.1)

    # plt.subplot(321, label="one")
    # plt.hist(dataArray[0], bins=200)
    # plt.title("exess")
    # plt.subplot(322, label="two")
    # plt.hist(dataArray[1], bins=200)
    # plt.title("222222")
    # plt.subplot(323)
    # plt.hist(dataArray[2], bins=200)
    # plt.title("ex333333ess")

    # plt.scatter(Xs1[1], Ys[1], c="blue", alpha=0.1)

    # plt.scatter(Xs1, Ys.flatten(), color=cs)

    # plt.grid(True)
    # plt.show()

    clusteredSongs = [[] for i in range(kmeans.n_clusters)]
    for i, cluster in enumerate(cs2):
        songCluster = clusteredSongs[int(cluster)]
        track = next((item for item in fullLib['tracks'] if item['track']['id'] == dataOrig[i]['id']), None)
        if (track is not None):
            songCluster.append({**track, **dataOrig[i]})
            # print(str(i)+' '+str(track['track']['artists'][0]['name'])+ ' - '+
            #      str(track['track']['album']['name'])+ ' - '+
            #     str(track['track']['name'])+' song '+str(dataOrig[i])+' ' )

    return fig


def create_sol_multiview():
    dataOrig = analyze.loadAudioFeatures()
    fullLib = analyze.loadLibraryFromFiles()
    # list: 3799 of dict:18
    # [{'danceability': 0.469, 'energy': 0.625, 'key': 4, 'loudness': -5.381, 'mode': 0, 'speechiness': 0.0306, 'acousticness': 0.00515, 'instrumentalness': 2.03e-05, 'liveness': 0.0682, 'valence': 0.325, 'tempo': 76.785, 'type': 'audio_features', 'id': '6PBzdsMi6YNdYAevzozBRi', 'uri': 'spotify:track:6PBzdsMi6YNdYAevzozBRi', 'track_href': 'https://api.spotify.com/v1/tracks/6PBzdsMi6YNdYAevzozBRi', 'analysis_url': 'https://api.spotify
    #  {'danceability': 0.76, 'energy': 0.608, 'key': 9, 'loudness': -8.673, 'mode': 0, 'speechiness': 0.0347, 'acousticness': 0.315, 'instrumentalness': 0.79, 'liveness': 0.121, 'valence': 0.727, 'tempo': 119.032, 'type': 'audio_features', 'id': '4dJYJTPbUgFK5pCQ5bYD4g', 'uri': 'spotify:track:4dJYJTPbUgFK5pCQ5bYD4g', 'track_href': 'https://api.spotify.com/v1/tracks/4dJYJTPbUgFK5pCQ5bYD4g', 'analysis_url': 'https://api.spotify.com/v1/audio-analysis/4dJYJTPbUgFK5pCQ5bYD4g', 'duration_ms': 254118, 'time_signature': 4}
    #  {'danc..
    dtype = [('danceability', '<f8'), ('energy', '<f8'), ('key', '<f8'), ('loudness', '<f8'), ('mode', '<f8'),
             ('speechiness', '<f8'), ('acousticness', '<f8'), ('instrumentalness', '<f8'), ('liveness', '<f8'),
             ('valence', '<f8'),
             ('tempo', '<f8'), ('type', '<f8'), ('id', '<f8'), ('duration_ms', '<f8'), ('time_signature', '<f8'), ]

    keys = ['danceability', 'energy', 'key', 'loudness', 'speechiness', 'acousticness', 'instrumentalness']
    keys = ['danceability', 'energy', 'key', 'loudness', 'valence', 'speechiness', 'tempo', 'time_signature']

    # keys = ['danceability', 'energy', 'loudness']
    # keys = ['danceability', 'energy']

    # ('danceability','energy','key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness', 'liveness',
    #      'valence', 'tempo'):

    dataArray = []
    for key in dataOrig[0]:
        if key in keys:
            # data[key] = [li[key] for li in dataOrig]
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
    # df = pd.DataFrame(X_train_norm)

    dataArrayMean = np.mean(dataArray)
    dataArrayStd = np.std(dataArray)
    allsongsstandardized = (dataArray - dataArrayMean) / dataArrayStd

    X_train_norm = allsongsstandardized
    X_train_norm = np.flip(np.rot90(X_train_norm, 3))

    dataToDisplay = np.flip(np.rot90(dataArray, 3))

    # allsongs: list:3799 x 8\
    # one row per song
    # [[0.469, 0.625, 4, -5.381, 0, 0.0306, 0.00515, 2.03e-05],
    # [0.76, 0.608, 9, -8.673, 0, 0.0347, 0.315, 0.79],
    # [0.598, 0.509, 9, -9.719, 1, 0.0269, 0.593, 0.0503],

    kmeans = KMeans(n_clusters=7)
    kmeans.fit(X_train_norm)

    predict = kmeans.predict(X_train_norm)

    centroids = kmeans.cluster_centers_
    correct = 0
    # for i in range(len(X1)):
    #    predict_me = np.array(X1[i].astype(float))
    #    predict_me = predict_me.reshape(-1, len(predict_me))
    #    prediction = kmeans.predict(predict_me)
    #    print(prediction[0])

    cs2 = kmeans.labels_.astype(float)

    fig = go.Figure(data=go.Splom(
        dimensions=[dict(label=keys[0],
                         values=dataToDisplay[:, 0]),
                    dict(label=keys[1],
                         values=dataToDisplay[:, 1]),
                    dict(label=keys[2],
                         values=dataToDisplay[:, 2]),
                    dict(label=keys[3],
                         values=dataToDisplay[:, 3]),
                    dict(label=keys[4],
                         values=dataToDisplay[:, 4]),
                    dict(label=keys[5],
                         values=dataToDisplay[:, 5]),
                    dict(label=keys[6],
                         values=dataToDisplay[:, 6]),
                    dict(label=keys[7],
                         values=dataToDisplay[:, 7])
                    ],

        marker=dict(color=cs2,
                    showscale=False,  # colors encode categorical variables
                    line_color='white', line_width=0.5)
    ))
    fig.show()

    return fig


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
    #print(centroids)
    xs = df['x']
    ys = df['y']

    plt.scatter(df['x'], df['y'], c=kmeans.labels_.astype(float), s=50, alpha=0.5)
    plt.scatter(centroids[:, 0], centroids[:, 1], c='red', s=50)
    plt.show()


#create_dataseries('127108998-data/')

# dataofish()
