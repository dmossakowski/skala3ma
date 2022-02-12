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
import random
import logging
import sqlite3 as lite


load_dotenv()
# https://docs.authlib.org/en/latest/flask/2/index.html#flask-oauth2-server
# If you are developing on your localhost, remember to set the environment variable:
# export AUTHLIB_INSECURE_TRANSPORT=true

os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"


SPOTIFY_APP_ID = os.getenv('SPOTIFY_APP_ID')
SPOTIFY_APP_SECRET = os.getenv('SPOTIFY_APP_SECRET')
DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')


app = Flask(__name__, static_folder='public', template_folder='views')

app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

genres = {"test": "1"}
authenticated = False

session_dataLoadingProgressMsg = 'dataLoadingProgressMsg'

gdata = {}
templateArgs = {}
processedDataDir = "/additivespotifyanalyzer"


#logging.basicConfig(filename=DATA_DIRECTORY+'/std.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s',
 #                   encoding='utf-8', level=logging.DEBUG)

@app.before_first_request
def init():
    print ('initializing server...')

    r = random.randint(0, 10000)
    init_logging(log_file=DATA_DIRECTORY+'/log'+str(r)+'.log',  console_loglevel=logging.DEBUG)
    # init_logging(console_loglevel=logging.DEBUG)

    if not os.path.exists(DATA_DIRECTORY):
        print("DATA_DIRECTORY does not exist... this will not end welll....")

    if not os.path.exists(DATA_DIRECTORY+"/users"):
        os.mkdir(DATA_DIRECTORY+"/users")
        print('Created users directory')

    if not os.path.exists(DATA_DIRECTORY + "/db"):
        os.mkdir(DATA_DIRECTORY + "/db")
        print('Created db directory')

    analyze.init()

def init_logging(log_file=None, append=False, console_loglevel=logging.INFO):
    """Set up logging to file and console."""
    if log_file is not None:
        if append:
            filemode_val = 'a'
        else:
            filemode_val = 'w'
        logging.basicConfig(level=logging.DEBUG,
                            format="%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s",
                            # datefmt='%m-%d %H:%M',
                            filename=log_file,
                            filemode=filemode_val)
    # define a Handler which writes INFO messages or higher to the sys.stderr

    console = logging.StreamHandler()
    console.setLevel(console_loglevel)
    # set a format which is simpler for console use
    formatter = logging.Formatter("%(asctime)s %(message)s")
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    #global LOG
    #LOG = logging.getLogger(__name__)


init_logging(log_file=DATA_DIRECTORY+'/l.log',  console_loglevel=logging.DEBUG)
#init_logging(console_loglevel=logging.DEBUG)


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
    logging.info ("fetching token... ")
    return session.get('token')


def update_token(name, token, refresh_token=None, access_token=None):
    #log.info('update_token')
    logging.info ("updating token... ")
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
            'scope': 'user-library-read user-top-read playlist-read-private playlist-read-collaborative'
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
        profile = None
        if library is not None:
            profile = library.get('profile')
        if profile is None:
            profileimageurl=None
            display_name = session.get('username')
        else:
            profileimageurl = profile['images'][0]['url']
            display_name = profile['display_name']
            session['profileimageurl'] = profile['images'][0]['url']

        l = analyze.getLibrarySize(library)
        lastModifiedDt = analyze.getUpdateDtStr(_getDataPath())
        #_setUserSessionMsg("Library size: "+l)
        return render_template('index.html', subheader_message=hellomsg, genres=genres, library=library,
                               sizetext=l, lastmodified=lastModifiedDt,
                               display_name=display_name, **session)
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
    logging.info ("doing login "+str(request.referrer)+" client_id "+str(SPOTIFY_APP_ID))

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
    logging.info ("doing revoke")
    spotify.revoke()


@app.route('/logout')
def logout():
    logging.info("doing revoke")
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
    logging.info("spotify is calling /login/authorized ...")
    try:
        error = request.args.get('error')
        logging.info(str(request))

        if str(error) == 'access_denied':
            logging.info ("access is denied ",error)
            return render_template('index.html', subheader_message="Not authorized", library={}, **session)

        #acc = spotify.fetch_access_token(scope='user-library-read')
        resp = spotify.authorize_access_token()
        logging.info ("spotify calls us now " + str(resp))
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

        meProfile = getAllMeItems('')

        session['id'] = meProfile['id']
        session['username'] = meProfile['display_name']
        #print(str(session.get("wants_url")))

        if session.get("wants_url") is not None:
            return redirect(session["wants_url"])
        else:
            if analyze.getUpdateDt(_getDataPath()) is not None:
                return redirect("/")
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
        logging.info(" error in authentication ", traceback.format_exc())
        return render_template('index.html',
                               subheader_message="Authentication error "+str(traceback.format_exc()),
                               library={},
                               **session)


@app.route('/api/token')
def spotify_token():
    logging.info("spotify is calling /api/token ...")


def refreshToken():
    if (session==None or session.get('token')==None):
        logging.info(" no valid seession, need to login")
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
        logging.info(" error response received when refreshing the token "+responseraw.text)
        return
    response = json.loads(responseraw.text)


@app.route('/datadownload')
@login_required
def downloadData():

    #dataAgeS = analyze.getUpdateDtStr(_getDataPath())
    #dataAge = analyze.getUpdateDt(_getDataPath())
    #maxAge = dataAge + 15 * 60 # one hour
    #currentTime = time.time()
    #newt = datetime.datetime.fromtimestamp(maxAge).strftime('%c')
    #if maxAge > currentTime:
     #   return "Your data was last loaded on " + dataAgeS

    #return dataAgeS+" loading <br>"+newt
    #print(" datadownload")
    library = _retrieveSpotifyData(session)

    @copy_current_request_context
    def handle_sub_view(session):
        with app.test_request_context():
            from flask import request
            logging.info(" starting new thread "+str(session.get('username')))
            #request = req
            logging.info(request.url)
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
#@login_required
def getOrphanedTracks():
    username = request.args.get('username')

    if username is None:
        dataPath = _getDataPath()
    else:
        dataPath = str(DATA_DIRECTORY)+"/users/"+username+ "/"

    library = analyze.loadLibraryFromFiles(dataPath)
    if library is None:
        return render_template('dataload.html', subheader_message="",
                               library=library,
                               **session)
    tracks = analyze.getOrphanedTracks(analyze.loadLibraryFromFiles(dataPath))
    library= {}
    library['tracks'] = tracks

    return render_template('orphanedTracks.html', sortedA=tracks,
                           subheader_message="Orphaned tracks count "+str(len(library['tracks'])),
                           library=library,
                            **session)







@app.route('/playlistDashboard')
#@login_required
def getPlaylistDashboard():

    username = request.args.get('username')

    if username is None:
        dataPath = _getDataPath()
    else:
        #dataPath = str(DATA_DIRECTORY)+"/"+username+ "/"
        dataPath = str(DATA_DIRECTORY) + "/users/127108998/"

    library = analyze.loadLibraryFromFiles(dataPath)
    if library is None:
        return render_template('dataload.html', subheader_message="",
                               library=library,
                               **session)

    playlistId = request.args.get('playlistId')
    playlistName = None
    playlist = None
    if playlistId is not None:
        playlist = analyze.getPlaylist(session['id'], library['playlists'], playlistId)
        playlist = playlist[0] #getPlaylist always returns a list
        playlistName = playlist['name']
        subheader_message = "Playlist " + playlistName
    else:
        subheader_message = "Playlists count: " + str(len(library['playlists']))
        library['playlists-tracks'] = analyze.getPlaylist(session['id'], library['playlists'])
        tracks = library['playlists']

    if playlist is None and library['playlists-tracks'] is None:
        return render_template('dataload.html', subheader_message="",
                                   library=library,
                                   **session)

    return render_template('playlistDashboard.html', playlistName=playlistName, playlist=playlist,
                           subheader_message=subheader_message,
                           library=library,
                            **session)




@app.route('/publicPlaylistDashboard')
def getPublicPlaylistDashboard():
    library = analyze.loadLibraryFromFiles(str(DATA_DIRECTORY)+"/users/127108998/")
    if library is None:
        return render_template('dataload.html', subheader_message="",
                               library=library,
                               **session)

    playlistName = request.args.get('playlistName')
    playlist = None
    if playlistName is not None:
        subheader_message = "Playlist " + playlistName
        for playlist in library['playlists-tracks']:
            if playlist['name'] == playlistName:
                break
    else:
        subheader_message = "Playlists count: " + str(len(library['playlists-tracks']))
        tracks = library['playlists-tracks']



    #library= {}
    #library['tracks'] = tracks

    return render_template('playlistDashboard.html', playlistName=playlistName, playlist=playlist,
                           subheader_message=subheader_message,
                           library=library,
                            **session)




def publicPlaylist(playlist):
    return playlist['public'] is True and len(playlist['tracks']['items']) > 2


@app.route('/testdb')
def testDB():
    logging.info("testing db")
    playlistName = request.args.get('name')

    ret = "done"
    if playlistName is not None:
        ret = analyze.testDb(playlistName)

    #playlist = analyze.getRandomPlaylist(DATA_DIRECTORY, 'playlists-tracks', publicPlaylist)
    #playlistId = playlist['id']
    #logging.info("playlist " + str(playlist))
    return ret
    #return redirect(url_for('getRandomPlaylist', playlistId=playlistId))


@app.route('/playlist/<playlistId>')
@login_required
def getPlaylist(playlistId):
    #playlistId = request.args.get('playlistId')

    logging.info(session['id']+' getPlaylist '+playlistId)
    # r = request
    # username = request.args.get('username')

    playlist = None

    if playlistId is not None:
        playlist = analyze.getPublicPlaylist(playlistId)

    if playlist is None:
        playlist = {}
        playlist['id']=playlistId
        playlist['name']='unknown'
        playlists = []
        playlists.append(playlist)
        playlistsWithTracks = getPlaylistTracks(playlists)

        if playlistsWithTracks is None:
            return render_template('dataload.html', sortedA=None,
                               subheader_message="",
                               library={},
                               **session)
        elif playlistsWithTracks is LookupError:
            return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist was not found",
                                   library={},
                                   **session)
        elif len(playlistsWithTracks) == 0:
            return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)

        playlist=playlistsWithTracks[0][0]
    #https: // localhost: 5000 / playlist?playlistId = 6
    #HoWLyjABf4N7oSItTrv94
    #https: // localhost: 5000 / playlist?playlistId = 1
    #KQnGup7xI7Zyk9lBhcoD5
    #3Y7iQBZXTBoiScWRONJOAe

    playlistName = playlist['name']
    subheader_message = "Playlist '" + playlistName + "' by "+playlist['owner']['display_name']

    # library= {}
    # library['tracks'] = tracks
    # playlist = json.dumps(playlist)
    # u = url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message)
    # return redirect(url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message,
    #                       library=None,
    #                       **session))

    return render_template("randomPlaylist.html", playlistName=playlistName, playlist=playlist,
                           subheader_message=subheader_message,
                           library=None,
                           **session)


@app.route('/loadPlaylist')
def getLoadPlaylist():
    playlistInfo = request.args.get('playlistInfo')

    if playlistInfo is None:
        return render_template('index.html', sortedA=None,
                               subheader_message="",
                               library={},
                               **session)

    #https://open.spotify.com/playlist/0s5mcEiGHNj50h3k3bZLSJ?si=d621b68e570544b3&fbclid=IwAR1UfvoR-fUxXbzG4eTgd5ZaaNtbIWGQCjRA_qCG37dkgTrMJDt7fdIT2eM&nd=1
    #a = playlistInfo.split('https://')
    a = playlistInfo.split('spotify.com/playlist/')

    playlistId = None
    if len(a)>1:
        playlistIds = a[1].split('?')

        playlistId = playlistIds[0]
    elif len(a) == 1:
        if '/' not in a[0]:
            playlistIds = a[0].split('?')
            playlistId = playlistIds[0]


    if playlistId is not None:
        logging.info("found match "+playlistId)
        return redirect(url_for('getPlaylist', playlistId=playlistId))
    else:

        return redirect(url_for('index'))

        #return render_template('index.html', sortedA=None,
         #                      subheader_message="",
          #                     library={},
           #                    **session)





@app.route('/randomPlaylist')
def getRandomPlaylist():


    #playlistName = request.args.get('playlistName')

    #playlists = None

    #while playlists is None:
    #    username = analyze.getRandomUsername(DATA_DIRECTORY)
    #    library = analyze.loadLibraryFromFiles(DATA_DIRECTORY + "/" + username + "/")
    #    if library is not None and library['playlists'] is not None and len(library['playlists'])>0:
    #        playlists = library['playlists']

    #logging.info("getting random playlist")

    playlist = analyze.getRandomPlaylist(DATA_DIRECTORY, 'playlists-tracks', publicPlaylist)


    #playlist = None

    if playlist is None:
        return render_template('dataload.html', sortedA=None,
                               subheader_message="",
                               library={},
                               **session)


    playlistId = playlist['id']
    #logging.info("playlist " + str(playlist))

    return redirect(url_for('getPlaylist', playlistId=playlistId))


@app.route('/dataload')
@login_required
def dataload():

    dt = analyze.getUpdateDtStr(_getDataPath())
    l = None
    if dt is not None:
        library = analyze.loadLibraryFromFiles(_getDataPath())
        l = analyze.getLibrarySize(library)


    return render_template('dataload.html', sortedA=None,
                           subheader_message="",
                           library={}, lastmodified=dt, sizetext=l,
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
        return str(DATA_DIRECTORY)+"/users/"+session['id']+"/"
    return str(DATA_DIRECTORY)+"/"


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
        logging.info("long running  session id: " + str(id(session['dataLoadingProgressMsg']))
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
        logging.info('setting dataLoadingProgressMsg to empty')
        session['dataLoadingProgressMsg'] = ''

    if _getUserSessionMsg() is None:
        _setUserSessionMsg('')

    logging.info('progress called. gdata:' + _getUserSessionMsg() + ' has: '+session.get('dataLoadingProgressMsg'))
    #@copy_current_request_context

    return Response(stream_with_context(generate(session)), mimetype='text/event-stream')



@app.route('/progressSimple')
def progressSimple():
    if session.get('dataLoadingProgressMsg') is None:
        session.dataLoadingProgressMsg = ''

    logging.info("progress started")
    def generateOLD():
        x = 0
        logging.info(str(datetime.datetime.now()))
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
    logging.info("retrieving profile...")
    profile = getAllMeItems('')

    file_path = _getDataPath()

    logging.info("retrieving top artists...")
    #_setUserSessionMsg("Loading top artists..." + analyze.getLibrarySize(library))
    library['topartists_short_term'] = getAllMeItems('top/artists', file_path, "short_term")
    library['topartists_medium_term'] = getAllMeItems('top/artists', file_path, "medium_term")
    library['topartists_long_term'] = getAllMeItems('top/artists', file_path, "long_term")

    logging.info("retrieving top tracks...")
    #_setUserSessionMsg("Top artists loaded. Loading top tracks..." + analyze.getLibrarySize(library))
    library['toptracks_short_term'] = getAllMeItems('top/tracks', file_path, "short_term")
    library['toptracks_medium_term'] = getAllMeItems('top/tracks', file_path, "medium_term")
    library['toptracks_long_term'] = getAllMeItems('top/tracks', file_path, "long_term")


    logging.info("retrieving tracks...")
    #_setUserSessionMsg("Loading tracks..." + analyze.getLibrarySize(library))
    library['tracks'] = getAllMeItems('tracks', file_path)
    logging.info("retrieving albums...")
    #_setUserSessionMsg("Loading albums..." + analyze.getLibrarySize(library))
    library['albums'] = getAllMeItems('albums', file_path)
    logging.info("retrieving audio_features...")
    #_setUserSessionMsg("Loading audio features..." )
    library['audio_features'] = getAudioFeatures(library['tracks'], file_path)


    logging.info("retrieving playlists...")
    # _setUserSessionMsg("Top artists loaded. Loading playlists..." + analyze.getLibrarySize(library))
    library['playlists'] = getAllMeItems('playlists', file_path)

    logging.info("retrieving playlist tracks...")
    # _setUserSessionMsg("Top artists loaded. Loading playlists..." + analyze.getLibrarySize(library))
    # when retrieving all user playlists, tracks are not included so we need to do another request
    # in the end we will have all playlists with their tracks for the user
    library['playlists'] = getPlaylistTracks(library['playlists'])

    _setUserSessionMsg("All data loaded <br>" + analyze.getLibrarySize(library))
    logging.info("All data downloaded "+analyze.getLibrarySize(library))

    #expire cache in analyze to force reload files from disk
    analyze.cache_clear()
    saagraph.cache_clear()

    return library


def getAllMeItems(itemtype, file_path=None, time_range=""):
    logging.info ("Retrieving data from spotify for type " + str(itemtype))
    _setUserSessionMsg('Loading ' + str(itemtype)+'...')
    oauthtoken = session['token']['access_token']

    auth_header = {'Authorization': 'Bearer {token}'.format(token=oauthtoken), 'Content-Type': 'application/json'}

    if len(time_range) > 0:
        api_url = 'https://api.spotify.com/v1/me/{}?time_range={}'.format(itemtype, time_range)
    else:
        api_url = 'https://api.spotify.com/v1/me/{}'.format(itemtype)
    # api_url = 'https://api.spotify.com/v1/me/playlists'

    logging.info("url used " + str(api_url))
    limit = 50
    offset = 0
    lastbatch = []
    payload = {'limit': limit, 'offset': offset}
    responseraw = requests.get(api_url, params=payload, headers=auth_header)
    response = json.loads(responseraw.text)


    # check if message='The access token expired'
    # status 401
    if ('error' in response):
        logging.info("response had an error %s", str(response['error']['status']))
        logging.info("")

    #if len(itemtype) == 0:
    #    return [response.get('id'), response.get('display_name')]

    items = response.get('items')
    if items is None:
        saveData(str(DATA_DIRECTORY)+"/users/"+response.get('id')+"/", "profile", time_range, response)
        return response

    received = response['limit']*(response['offset'])
    ids = []

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

    logging.info('retrieved '+str(itemtype)+' size '+str(len(items)))
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

    saveData(file_path, itemtype, time_range, items)

    return items


def saveData(file_path, itemtype, time_range, d):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    itemtype = itemtype.replace("/", "")
    if len(time_range) > 0:
        time_range = "_"+time_range

    with (open(file_path+'/'+str(itemtype)+str(time_range)+'.json', "w")) as outfile:
        json.dump(d, outfile, indent=0)


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
    logging.info ("Retrieving audio features from spotify for tracks ")
    if (session!=None and session.get('token')!=None):
        oauthtoken = session['token']['access_token']
    else:
        logging.info("not loggged in")
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
            featureBatch = retrieveBatch(api_url, auth_header)
            if featureBatch==None:
                logging.info('no features returned')
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


# this expects a url that retrieves some batch of data
# the URL is not modified in the method and just the raw
# results are returned
def retrieveBatch(api_url, auth_header, iter=0):
    payload = {}
    responseraw = requests.get(api_url, params=payload, headers=auth_header)
    response = json.loads(responseraw.text)

    # check if message='The access token expired'
    # status 401
    if 'error' in response:
        logging.info ("response had an error "+str(response['error']['status']))
        if response['error']['status'] == 401:
            logging.info("relogin required... will retry "+str(iter))
            if iter>2:
                return None
            login()
            return retrieveBatch(api_url, auth_header, iter+1)
        if response['error']['status'] == 404:
            return None
    items = response

    return items




# playlists come with id for retrieval tracks:
# "tracks": {
#             "href": "https://api.spotify.com/v1/playlists/047sooHidTDdnTo9BMRANV/tracks",
#             "total": 23
#         },
# this method loops over all playlists downloaded (public and private)
# and it generates one json file for each playlist
def getPlaylistTracks(playlists):
    if (session!=None and session.get('token')!=None):
        oauthtoken = session['token']['access_token']
    else:
        logging.info("not loggged in")
        return render_template('index.html', subheader_message="No oauthtoken.. bad flow ", library={}, **session)

    logging.info(session.get('username')+" retrieving playlist tracks from spotify for all playlists ")

    auth_header = {'Authorization': 'Bearer {token}'.format(token=oauthtoken), 'Content-Type': 'application/json'}
    api_url_base = 'https://api.spotify.com/v1/playlists/'
    # api_url = 'https://api.spotify.com/v1/me/playlists'

    limit = 100
    ids=[]
    tracks=[]
    playlistsWithTracks=[]

    for playlist in playlists:
        oneplaylistWithTracks=[]
        id = playlist["id"]
        name = playlist["name"]
        #ids.append(id)
        limit-=1
        #if (limit == 0 or (len(tracks)+len(ids))==len(playlists)):
        #api_url = api_url_base+"" + id + "/?fields=tracks.items(track(name,href,album(!name,href,available_markets)))"
        api_url = api_url_base + "" + id

        featureBatch = retrieveBatch(api_url, auth_header)
        if featureBatch==None:
            #logging.info('no tracks returned')
            #break
            featureBatch = {'audio_features': {}} #dict.fromkeys(lastFeatureBatch,0)

        featureBatchTracks = featureBatch.get('tracks')
        if featureBatchTracks is None:
            logging.info('skipping playlist which has no tracks ' + str(name))
            continue

        if featureBatchTracks.get('next') is not None and len(featureBatch['tracks']['items']) < 80:
            next = featureBatch['tracks']['next']
            while next is not None:
                featureBatch2 = retrieveBatch(next, auth_header)
                featureBatch['tracks']['items'].extend(featureBatch2['items'])
                next = featureBatch2['next']


        #featureBatch = featureBatch.get('audio_features')
        #lastFeatureBatch = featureBatch
        #tracks += featureBatch
        _setUserSessionMsg('Loading playlists... ' + str(len(playlistsWithTracks)) + '/' + str(len(playlists)))
        #print (" size "+str(len(featureBatch['tracks']['items'])))
        #limit = 100
        #ids.clear()
        oneplaylistWithTracks.append(featureBatch)

        for item in featureBatch['tracks']['items']:
            if item.get('track'):
                item['track']['available_markets'] = None
                item['track']['album']['available_markets'] = None
                # item['track']['album']['images'] = None
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

        #with (open(file_path+'/playlists-tracks'+str(id)+'.json', "w")) as outfile:
        #    json.dump(oneplaylistWithTracks, outfile, indent=4)

        playlistsWithTracks.append(oneplaylistWithTracks)

    analyze.addPlaylists(playlistsWithTracks)
    return playlistsWithTracks





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

        trackCount = 0
        for l in sortedA:
            trackCount += len(sortedA[l])
        #data = {'First Column Name': ['First value', 'Second value', ...],
        #        'Second Column Name': ['First value', 'Second value', ...],
        #        ....
        #        }
        #data = pd

        return render_template('trackslist.html', subheader_message="Local data processed in " +
                                                               str(time.process_time() - start)+"ms. Artist count "
                                +str(len(sortedA))+". Track count "+str(trackCount),
                               sortedA=sortedA, diagramVersion="test", library=library, **session)
    else:
        return render_template('index.html', subheader_message="Local data not found. Click to retrieve.",
                               library={},
                               **session)



@app.route('/favorite_artists_over_time')
@login_required
def getFavoriteArtistsOverTime(file_path='data/'):
    #logging.info ("retrieving audio features...")

    library = analyze.loadLibraryFromFiles(_getDataPath())

    if library is None or library.get('topartists_short_term') is None:
        return render_template('dataload.html', subheader_message="",
                               library={},
                               **session)

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    bar = saagraph.create_top_artists_graph(_getDataPath())

    return render_template('favorite_artists_over_time.html', sortedA=None,
                           subheader_message='',
                           plot=bar, **session)




@app.route("/library")
def getlibrary():
    ds = request.args

    library = analyze.loadLibraryFromFiles(_getDataPath())

    if library is None:
        logging.info(" library is None")
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
    print('Executing main')
    #init()
    app.run(host='localhost', threaded=True, debug=True, ssl_context=('cert.pem', 'key.pem'))




