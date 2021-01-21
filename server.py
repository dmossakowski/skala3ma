from gevent import monkey; monkey.patch_socket()
import base64
import io
import urllib
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, redirect, url_for, session, request, render_template, send_file, jsonify, Response, \
    stream_with_context, copy_current_request_context
#from flask_oauthlib.client import OAuth, OAuthException
from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError

import requests
import json
import pandas as pd
from matplotlib.backends.backend_template import FigureCanvas

import analyze
import graph as saagraph
import os
import traceback
import time
import datetime
import threading

load_dotenv()
# https://docs.authlib.org/en/latest/flask/2/index.html#flask-oauth2-server
# If you are developing on your localhost, remember to set the environment variable:
# export AUTHLIB_INSECURE_TRANSPORT=true

os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"


SPOTIFY_APP_ID = os.getenv('SPOTIFY_APP_ID')
SPOTIFY_APP_SECRET = os.getenv('SPOTIFY_APP_SECRET')

app = Flask(__name__, static_folder='public', template_folder='views')

app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

genres = {"test": "1"}
authenticated = False

session_dataLoadingProgressMsg = 'dataLoadingProgressMsg'

gdata = {}
templateArgs = {}

class ExportingThread(threading.Thread):
    def __init__(self):
        self.progress = 0
        super().__init__()

    def run(self):
        # Your exporting stuff goes here ...
        with app.app_context():
            _retrieveSpotifyData()



exporting_threads = {}

def login_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session != None and session.get('expires_at') is not None:
            now = int(datetime.datetime.now().timestamp())
            #expiresAt = session['expires_at']
            expiresAtLocaltime = session['expires_at_localtime']

            if expiresAtLocaltime < now:
                session["wants_url"] = request.url
                return redirect(url_for("login"))
            else:
                return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("login"))
    return decorated_function




def fetch_token():
    #log.info('fetch_token')
    print ("fetching token... ")
    return session.get('token')


def update_token(name, token, refresh_token=None, access_token=None):
    #log.info('update_token')
    print ("updating token... ")
    session['token'] = token
    return session['token']


spotify = oauth.register(
    name='spotify',
    client_id=SPOTIFY_APP_ID,
    client_secret=SPOTIFY_APP_SECRET,
    #consumer_key=SPOTIFY_APP_ID,
    #consumer_secret=SPOTIFY_APP_SECRET,
    # Change the scope to match whatever it us you need
    # list of scopes can be found in the url below
    # https://developer.spotify.com/web-api/using-scopes/
    access_token_params=None,
    #scope = 'playlist-read-private user-library-read	 user-top-read',
    base_url='https://accounts.spotify.com/',
    #request_token_url='https://accounts.spotify.com/api/token',
    access_token_url='https://accounts.spotify.com/api/token',
    refresh_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize',
    fetch_token=fetch_token,
    update_token=update_token,
    client_kwargs = {
            'scope': 'user-library-read user-top-read'
    #'scope': 'playlist-read-private  user-library-read  user-top-read'
    }
)


@app.route('/')
def index():
    session['hellomsg'] = 'Welcome to Spotify Analyzer'
    hellomsg = 'Welcome to Additive Spotify Analyzer'
    _setUserSessionMsg(None)
    library = analyze.loadLibraryFromFiles(_getDataPath())

    if session.get('username'):
        genres = analyze.getTopGenreSet(library)
        hellomsg = 'Welcome '+session.get('username')

        l = analyze.getLibrarySize(library)
        #_setUserSessionMsg("Library size: "+l)
        return render_template('index.html', subheader_message=hellomsg, genres=genres, library=library, **session)
    else:

        return render_template('index.html', subheader_message=hellomsg, genres={}, library={},  **session)

    #accessToken = session.get('access_token')
    #session2 = session

    #if (len(library) == 0):
    #    return redirect(url_for('login'))
    #else:
    #return redirect(url_for('getlibrary'))


@app.route('/login')
def login():
    print ("doing login",str(request.referrer)," client_id",str(SPOTIFY_APP_ID))

    callback = url_for('spotify_authorized', _external=True)

    #print(" request.referrer " + request.referrer)
    #print(" request.args.get('next') ="+request.args.get('next'))

    callback2 = url_for(
        'spotify_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True
    )
    return spotify.authorize_redirect(callback)


@app.route('/revoke')
def revoke():
    print ("doing revoke")
    spotify.revoke()


@app.route('/logout')
def logout():
    print("doing revoke")
    session.pop('token', None)
    session.pop('username', None)
    session.pop('wants_url', None)
    session.pop('access_token', None)
    session['access_token'] = None
    session['logged_in'] = False
    session['refresh_token'] = None
    session['expires_at'] = None
    session['expires_in'] = None
    session.clear()
    _setUserSessionMsg('You have been logged out')
    spotify.token

    return render_template('login.html',
                           subheader_message="Logged out ",
                           library={}, **session)


#@app.route('/authorize')
#def authorize():
#    token = oauth.twitter.authorize_access_token()
#    # this is a pseudo method, you need to implement it yourself
#    #OAuth1Token.save(current_user, token)
#    return redirect(url_for('twitter_profile'))


@app.route('/login/authorized')
def spotify_authorized():
    print("spotify is calling /login/authorized ...")
    try:
        error = request.args.get('error')
        print(str(request))

        if str(error) == 'access_denied':
            print ("access is denied ",error)
            return render_template('index.html', subheader_message="Not authorized", library={}, **session)

        #acc = spotify.fetch_access_token(scope='user-library-read')
        resp = spotify.authorize_access_token()
        print ("spotify calls us now ", str(resp))
        if resp is None:
            return 'Access denied: reason={0} error={1}'.format(
                request.args['error_reason'],
                request.args['error_description']
            )
        #if isinstance(resp, OAuthException):
        #    return 'Access denied: {0}'.format(resp.message)

        session['token'] = resp
        session['access_token'] = (resp['access_token'], '')
        session['refresh_token'] = (resp['refresh_token'], '')
        session['expires_at'] = resp['expires_at']
        session['expires_in'] = resp['expires_in']
        session['expires_at_localtime'] = int(datetime.datetime.now().timestamp()+int(resp['expires_in'])-1000)
        session.dataLoadingProgressMsg = ''

        #
        # me = spotify.get('/v1/me')
        #getPlaylists(session['oauth_token'], 'dmossakowski')

        global authenticated
        authenticated = True
            #print me.data

        userId = getAllMeItems('')
        session['id'] = userId[0]
        session['username'] = userId[1]
        print(str(session.get("wants_url")))

        if session.get("wants_url") is not None:
            return redirect(session["wants_url"])
        else:
            return redirect("/dataload")
            #return redirect("/")
            #print('This should never happen. wants_url missing in session')

        #return render_template('index.html')
        #return me.data
        #return "logged in"
        #return 'logged in token '.format(session['oauth_token'])
        #return 'Logged in as id={0} name={1} redirect={2}'.format(
         #   me.data['id'],
          #  me.data['name'],
           # request.args.get('next')
        #)
    except OAuthError as e:
        print (" error in authentication ", traceback.format_exc())
        return render_template('index.html',
                               subheader_message="Authentication error "+str(traceback.format_exc()),
                               library={},
                               **session)


@app.route('/api/token')
def spotify_token():
    print ("spotify is calling /api/token ...")


def refreshToken():
    if (session==None or session.get('token')==None):
        print(" no valid seession, need to login")
        return login()

    oauthtoken = session['token']['refresh_token']

    basic = base64.standard_b64encode((SPOTIFY_APP_ID+':'+SPOTIFY_APP_SECRET).encode())
    auth_header = {'Authorization': 'Authorization Basic {basic}'.format(basic=basic)}
                 #  'Content-Type': 'application/x-www-form-urlencoded'}
    api_url = 'https://accounts.spotify.com/api/token'

    payload = {'grant_type': 'refresh_token', 'refresh_token': oauthtoken}
    payloadEncoded = urllib.parse.urlencode(payload)
    #payloadEncoded = requests.utils.requote_uri(payload)
    payloadEncoded = payloadEncoded.encode('ascii')

    #t = oauth.create_client("spotify")
    #token = t.fetch_token()
    responseraw = requests.post(api_url, data=payloadEncoded, headers=auth_header)
    if (responseraw.status_code==400):
        print(" error response received when refreshing the token "+responseraw.text)
        return
    response = json.loads(responseraw.text)


@app.route('/datadownload')
@login_required
def downloadData():
    library = _retrieveSpotifyData(session)
    print(" datadownload")

    @copy_current_request_context
    def handle_sub_view(session):
        with app.test_request_context():
            from flask import request
            print(" starting new thread "+str(session.get('username')))
            #request = req
            print(request.url)
            # Do Expensive work
            _retrieveSpotifyData(session)

    #threading.Thread(target=handle_sub_view, args=(session,)).start()

    #with app.app_context():
    #
    #    global exporting_threads#

        #thread_id = random.randint(0, 10000)
    #    thread_id =1
    #    exporting_threads[thread_id] = ExportingThread()
    #    exporting_threads[thread_id].start()

    #return 'task id: #%s' % thread_id

    return "All data retrieved"
    #return render_template('index.html', sortedA=library.get('playlists'),
    #                       subheader_message="Playlists retrieved with track count "+str(len(library['tracks'])),
    #                       library=library,
    #                        **session)






@app.route('/orphanedTracks')
@login_required
def getOrphanedTracks():
    library = analyze.loadLibraryFromFiles(_getDataPath())
    if library is None:
        return render_template('dataload.html', subheader_message="",
                               library=library,
                               **session)
    tracks = analyze.getOrphanedTracks(analyze.loadLibraryFromFiles(_getDataPath()))
    library= {}
    library['tracks'] = tracks

    return render_template('orphanedTracks.html', sortedA=tracks,
                           subheader_message="Orphaned tracks count "+str(len(library['tracks'])),
                           library=library,
                            **session)




@app.route('/dataload')
@login_required
def dataload():

    return render_template('dataload.html', sortedA=None,
                           subheader_message="",
                           library={},
                            **session)


@app.route('/topartists')
@login_required
def getTopArtists():
    library = analyze.loadLibraryFromFiles(_getDataPath())
    if library is None:
        return render_template('dataload.html', subheader_message="",
                               library=library,
                               **session)
    tracks = analyze.getOrphanedTracks(analyze.loadLibraryFromFiles(_getDataPath()))
    library['tracks'] = tracks
    genres = analyze.getTopGenreSet(library)

    return render_template('topartists.html', sortedA=tracks,
                           subheader_message="Top artists  "+str(len(library['tracks'])),
                           library=library,
                           genres=genres,
                            **session)


@app.route('/topgenres')
@login_required
def getTopGenres():
    library = analyze.loadLibraryFromFiles(_getDataPath())
    if library is None:
        return render_template('dataload.html', subheader_message="",
                               library=library,
                               **session)
    tracks = analyze.getOrphanedTracks(analyze.loadLibraryFromFiles(_getDataPath()))
    library['tracks'] = tracks
    genres = analyze.getTopGenreSet(library)

    return render_template('topgenres.html', sortedA=tracks,
                           subheader_message="Top Genres "+str(len(library['tracks'])),
                           library=library,
                           genres=genres,
                            **session)


def _getGlobalKey(msgtype = ''):
    key = msgtype + 'backgroundMsg'
    if (session.get('id')):
        key = session['id'] + key
    return key


def _getUserSessionMsg(msgtype = ''):
    return gdata.get(_getGlobalKey(msgtype))


def _setUserSessionMsg(msg='', msgtype=''):
    gdata[_getGlobalKey(msgtype)] = msg


def _getDataPath():
    if (session.get('id')):
        return session['id'] + "-data/"
    return "data/"


@app.route('/progresstest')
@login_required
def progresspage():
    if session.get('dataLoadingProgressMsg') is None:
        session['dataLoadingProgressMsg'] = ''

    if gdata.get(session['id']+'backgroundMsg') is None:
        gdata[(session['id'] + 'backgroundMsg')] = ''

    x = 0
    #while x <= 20:
    #    session['dataLoadingProgressMsg'] = "x: "+str(x)+" - "+str(datetime.datetime.now())
    #    gdata[(session['id'] + 'backgroundMsg')] = "gdata: "+str(x)+" - "+str(datetime.datetime.now())
    #    print("long running  session id: " + str(id(session['dataLoadingProgressMsg']))
    #          + ' session: ' + session['dataLoadingProgressMsg']
    #          + ' gdata:' + gdata.get(session['id'] + 'backgroundMsg'))
    #    x = x + 1
    #    time.sleep(0.5)
    return render_template('progresstest.html',
                           subheader_message="Testing progress " + str(session['expires_at_localtime'])
                                             + "x: "+str(x)+" - "+str(datetime.datetime.now()),
                           **session)


@app.route('/progressStart')
@login_required
def progressstart():
    if session.get('dataLoadingProgressMsg') is None:
        session['dataLoadingProgressMsg'] = ''

    #_retrieveSpotifyData()
    x = 0
    max = 976
    _setUserSessionMsg("Starting fake data load at " + str(datetime.datetime.now()))
    time.sleep(3)
    while x <= max:
        #session['dataLoadingProgressMsg'] = "x: "+str(x)+" - "+str(datetime.datetime.now())
        _setUserSessionMsg("Loading fake data: "+str(x)+"/"+str(max)+" at "+str(datetime.datetime.now()))
        print("long running  session id: " + str(id(session['dataLoadingProgressMsg']))
              + ' session: ' + session['dataLoadingProgressMsg']
              + ' gdata:' + _getUserSessionMsg())
        x = x + 1
        time.sleep(0.2)

    _setUserSessionMsg("Fake data loaded: " + str(x) + "/" + str(max) + " at " + str(datetime.datetime.now()))
    #session['dataLoadingProgressMsg'] = 'starting at ' + str(datetime.datetime.now())
    return render_template('progresstest.html',
                           subheader_message="Testing progress " + str(session['username']),
                           **session)


def generate(sessionLocal):
    x = 0
    started = str(datetime.datetime.now())
    with app.app_context():
        #print("generator started...")
        #thread = Thread(target=_retrieveSpotifyData, args=(session))
        #thread.start()

        lib = analyze.loadLibraryFromFiles(_getDataPath())
        #session['dataLoadingProgressMsg'] = userId
        while _getUserSessionMsg():
            #s = "data: {x:" + str(x) + ', generator ' \
            s = 'data: ' + _getUserSessionMsg()
            #+ sessionLocal['dataLoadingProgressMsg'] \
            #+ ' library: '+analyze.getLibrarySize(lib) \

            yield s + "\n\n"
            #print("generator yielding: " + s)
            x = x + 10
            time.sleep(0.3)


@app.route('/progress')
def progress():
    if session.get('dataLoadingProgressMsg') is None:
        print('setting dataLoadingProgressMsg to empty')
        session['dataLoadingProgressMsg'] = ''

    if _getUserSessionMsg() is None:
        _setUserSessionMsg('')

    print('progress called. gdata:' + _getUserSessionMsg() + ' has: '+session.get('dataLoadingProgressMsg'))
    #@copy_current_request_context

    return Response(stream_with_context(generate(session)), mimetype='text/event-stream')



@app.route('/progressSimple')
def progressSimple():
    if session.get('dataLoadingProgressMsg') is None:
        session.dataLoadingProgressMsg = ''

    print("progress started")
    def generateOLD():
        x = 0
        print(str(datetime.datetime.now()))
        yield "data:" + str(x) + " - " + str(datetime.datetime.now()) + "\n\n"
        #while x <= 100:
        #    yield "data:" + str(x) + "\n msg: "+ str(datetime.date) + "\n\n"
        #    x = x + 10
        #    time.sleep(0.5)
    return Response(generateOLD(), mimetype='text/event-stream')



def _retrieveSpotifyData(session):
    session["wants_url"] = None
    infoMsg = 'Loading profile...'
    _setUserSessionMsg(infoMsg)
    library = {}
    print("retrieving profile...")
    #userId = getAllMeItems('')

    file_path = _getDataPath()

    print("retrieving top artists...")
    #_setUserSessionMsg("Loading top artists..." + analyze.getLibrarySize(library))
    library['topartists_short_term'] = getAllMeItems('top/artists', file_path, "short_term")
    library['topartists_medium_term'] = getAllMeItems('top/artists', file_path, "medium_term")
    library['topartists_long_term'] = getAllMeItems('top/artists', file_path, "long_term")

    print("retrieving top tracks...")
    #_setUserSessionMsg("Top artists loaded. Loading top tracks..." + analyze.getLibrarySize(library))
    library['toptracks_short_term'] = getAllMeItems('top/tracks', file_path, "short_term")
    library['toptracks_medium_term'] = getAllMeItems('top/tracks', file_path, "medium_term")
    library['toptracks_long_term'] = getAllMeItems('top/tracks', file_path, "long_term")

    print("retrieving playlists...")
    #_setUserSessionMsg("Top artists loaded. Loading playlists..." + analyze.getLibrarySize(library))
    library['playlists'] = getAllMeItems('playlists', file_path)

    print("retrieving tracks...")
    #_setUserSessionMsg("Loading tracks..." + analyze.getLibrarySize(library))
    library['tracks'] = getAllMeItems('tracks', file_path)
    print("retrieving albums...")
    #_setUserSessionMsg("Loading albums..." + analyze.getLibrarySize(library))
    library['albums'] = getAllMeItems('albums', file_path)
    print("retrieving audio_features...")
    #_setUserSessionMsg("Loading audio features..." )
    library['audio_features'] = getAudioFeatures(library['tracks'], file_path)
    _setUserSessionMsg("All data loaded <br>"+analyze.getLibrarySize(library))
    print("All data downloaded "+analyze.getLibrarySize(library))
    return library


def getAllMeItems(itemtype, file_path="data/", time_range=""):
    print ("Retrieving data from spotify for type ", itemtype)
    _setUserSessionMsg('Loading ' + str(itemtype)+'...')
    oauthtoken = session['token']['access_token']

    auth_header = {'Authorization': 'Bearer {token}'.format(token=oauthtoken), 'Content-Type': 'application/json'}

    if len(time_range) > 0:
        api_url = 'https://api.spotify.com/v1/me/{}?time_range={}'.format(itemtype, time_range)
    else:
        api_url = 'https://api.spotify.com/v1/me/{}'.format(itemtype)
    # api_url = 'https://api.spotify.com/v1/me/playlists'

    print("url used " + str(api_url))
    limit = 50
    offset = 0
    lastbatch = []
    payload = {'limit': limit, 'offset': offset}
    responseraw = requests.get(api_url, params=payload, headers=auth_header)
    response = json.loads(responseraw.text)


    # check if message='The access token expired'
    # status 401
    if ('error' in response):
        print ("response had an error ", response['error']['status'])
        print ("")

    if len(itemtype) == 0:
        return [response.get('id'), response.get('display_name')]

    items = response['items']

    received = response['limit']*(response['offset'])
    ids=[]

    while (len(items) < response['total']):
        offset+=limit
        payload = {'limit': limit, 'offset': offset}
        response = json.loads(requests.get(api_url, params=payload, headers=auth_header).text)
        lastbatch = response['items']
        items = items + response['items']
        if (itemtype == 'tracks'):
            for track in items:
                ids.append(track["track"]["id"])
        _setUserSessionMsg('Loading '+str(itemtype)+'... '+str(len(items))+'/'+str(response['total']))

    print('retrieved '+str(itemtype)+' size '+str(len(items)))
    _setUserSessionMsg('Loaded '+str(len(items))+' '+str(itemtype))

    for item in items:
        if item.get('track'):
            item['track']['available_markets'] = None
            item['track']['album']['available_markets'] = None
            #item['track']['album']['images'] = None
            item['track']['album']['artists'] = None
            item['track']['album']['external_urls'] = None
            item['track']['artists'][0]['external_urls'] = None
            item['track']['external_urls'] = None
        if item.get('album'):
            item['album']['available_markets'] = None
            item['album']['copyrights'] = None
            item['album']['tracks'] = None
        if item.get('available_markets'):
            item['available_markets'] = None

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    itemtype = itemtype.replace("/", "")
    if len(time_range) > 0:
        time_range = "_"+time_range

    with (open(file_path+'/'+str(itemtype)+str(time_range)+'.json', "w")) as outfile:
        json.dump(items, outfile, indent=4)

    return items


@app.route('/audio_features')
@login_required
def getAudioFeatures(file_path='data/'):
    #print ("retrieving audio features...")
    library = analyze.loadLibraryFromFiles(_getDataPath())

    if library is None:
        return render_template('dataload.html', subheader_message="",
                               library={},
                               **session)

    audioFeatures = library['audio_features']
    if audioFeatures == None:
        audioFeatures = getAudioFeatures(library['tracks'])

    if audioFeatures == None:
        return render_template('index.html', subheader_message="Failed to get audio features ",
                               library=library,
                               **session)

    library['audio_features'] = audioFeatures
    #print (" done")

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


    bar = saagraph.create_dataseries(_getDataPath())

    return render_template('timeseries.html', sortedA=audioFeatures,
                           subheader_message=str(len(audioFeatures)),
                           plot=bar, **session)


def getAudioFeatures(tracks, file_path='data/'):
    print ("Retrieving audio features from spotify for tracks ")
    if (session!=None and session.get('token')!=None):
        oauthtoken = session['token']['access_token']
    else:
        print("not loggged in")
        return render_template('index.html', subheader_message="No oauthtoken.. bad flow ", library={}, **session)

    auth_header = {'Authorization': 'Bearer {token}'.format(token=oauthtoken), 'Content-Type': 'application/json'}
    api_url_base = 'https://api.spotify.com/v1/audio-features/'
    # api_url = 'https://api.spotify.com/v1/me/playlists'

    limit = 100
    ids=[]
    features=[]
    lastFeatureBatch={}
    for track in tracks:
        trackid = track["track"]["id"]
        ids.append(trackid)
        limit-=1
        if (limit == 0 or (len(features)+len(ids))==len(tracks)):
            api_url = api_url_base+"?ids=" + ",".join(ids)
            featureBatch = retrieveAudioFeatures(api_url, auth_header)
            if featureBatch==None:
                print('no features returned')
                #break
                featureBatch = {'audio_features': {}} #dict.fromkeys(lastFeatureBatch,0)

            featureBatch = featureBatch.get('audio_features')
            lastFeatureBatch = featureBatch
            features += featureBatch
            _setUserSessionMsg('Loading audio features... ' + str(len(features)) + '/' + str(len(tracks)))
            limit = 100
            ids.clear()

    with (open(file_path+'/audio_features.json', "w")) as outfile:
        json.dump(features, outfile, indent=4)

    return features



def retrieveAudioFeatures(api_url, auth_header):
    payload = {}
    responseraw = requests.get(api_url, params=payload, headers=auth_header)
    response = json.loads(responseraw.text)

    # check if message='The access token expired'
    # status 401
    if 'error' in response:
        print ("response had an error ", response['error']['status'])
        if response['error']['status'] == 401:
            login()
            return None
    items = response

    return items



@app.route("/trackslist")
def analyzeLocal():

    library = analyze.loadLibraryFromFiles(_getDataPath())

    if library is None:
        return render_template('dataload.html', subheader_message="",
                               library=library,
                               **session)
    if library:
        start = time.process_time()
        sortedA = analyze.process(library)

        #data = {'First Column Name': ['First value', 'Second value', ...],
        #        'Second Column Name': ['First value', 'Second value', ...],
        #        ....
        #        }
        #data = pd

        return render_template('trackslist.html', subheader_message="Local data processed in " +
                                                               str(time.process_time() - start)+"ms. Track count "
                                +str(len(sortedA)),
                               sortedA=sortedA, diagramVersion="test", library=library, **session)
    else:
        return render_template('index.html', subheader_message="Local data not found. Click to retrieve.",
                               library={},
                               **session)


@app.route("/library")
def getlibrary():
    ds = request.args

    library = analyze.loadLibraryFromFiles(_getDataPath())

    if library is None:
        print(" library is None")
    tracksWoAlbum = []
    analyze.process(library)

    #for ()

    bar = saagraph.create_dataseries()
    return render_template('timeseries.html', plot=bar)



@app.route("/hello")
def hello():
    return "Hello mister"


@app.route('/plot.png')
def plot_png():
    fig = analyze.create_figure1()

    #output = io.BytesIO()
    #FigureCanvas(fig).print_figure(output)
    img = io.BytesIO()
    fig.savefig(img)
    img.seek(0)
    return send_file(img, mimetype='image/png')
    #return Response(output.getvalue(), mimetype='image/png')


@app.route('/contact-us.html')
def contactus():
    return render_template('contact-us.html')


@app.route('/contact.html')
def contact():
    return render_template('contact.html')


@app.route('/login.html')
def blog():
    return render_template('login.html', **session)


if __name__ == '__main__':
    app.run(host='127.0.0.1', threaded=True, debug=True)

