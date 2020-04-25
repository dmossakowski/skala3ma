import base64
import io
import urllib
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, redirect, url_for, session, request, render_template, send_file, jsonify, Response
#from flask_oauthlib.client import OAuth, OAuthException
from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError
import requests
import json

from matplotlib.backends.backend_template import FigureCanvas

import analyze
import graph as saagraph
import os
import traceback
import time
import datetime

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

        #elif session != None and session.get('token') != None:
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
            'scope': 'user-library-read '
#'scope': 'playlist-read-private  user-library-read  user-top-read'
    }

)



@app.route('/')
def index():
    hellomsg = 'Welcome to Spotify Analyzer'
    if session.get('username'):
        hellomsg = 'Welcome '+session.get('username')+' to Spotify Analyzer'
    return render_template('index.html', subheader_message=hellomsg)

    #accessToken = session.get('access_token')
    #session2 = session

    #if (len(library) == 0):
    #    return redirect(url_for('login'))
    #else:
    #return redirect(url_for('getlibrary'))


@app.route('/login')
def login():
    print ("doing login",str(request))

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
    #spotify.revoke
    return render_template('index.html',
                           subheader_message="Logged out ")


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
            return render_template('index.html', subheader_message="Not authorized")

        acc = spotify.fetch_access_token(scope='user-library-read')
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
        #
        # me = spotify.get('/v1/me')
        #getPlaylists(session['oauth_token'], 'dmossakowski')

        global authenticated
        authenticated = True
            #print me.data

        userId = getAllMeItems('')
        session['username'] = userId

        if session["wants_url"] is not None:
            return redirect(session["wants_url"])

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
                               subheader_message="Authentication error "+str(traceback.format_exc()))




@app.route('/api/token')
def spotify_token():
    print ("spotify is calling /api/token ...")


def refreshToken():
    if (session==None or session.get('token')==None):
        print(" no valid seession, need to login")
        return login()

    oauthtoken = session['token']['refresh_token']

    # username = '127108998'
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




@app.route('/playlists')
@login_required
def get_playlists():
    #print ("getting playlist authenticated? ",authenticated)
    #return redirect(url_for('login'))

    session["wants_url"] = None
    library = {}
    print("retrieving profile...")
    userId = getAllMeItems('')


    file_path = userId+"-data/"

    print ("retrieving playlists...")
    library['playlists'] = getAllMeItems('playlists', file_path)
    print ("retrieving tracks...")
    library['tracks'] = getAllMeItems('tracks', file_path)
    print ("retrieving albums...")
    library['albums'] = getAllMeItems('albums', file_path)

    library['audio_features'] = getAudioFeatures(library['tracks'], file_path)

    #library = analyze.loadLibraryFromFiles()

    return render_template('index.html', sortedA=library['albums'],
                           subheader_message="Playlists retrieved with track count "+str(len(library['tracks'])))



def getAllMeItems(type, file_path="data/"):
    print ("Retrieving data from spotify for type ",type)
    oauthtoken = session['token']['access_token']
    #username = '127108998'
    auth_header = {'Authorization': 'Bearer {token}'.format(token=oauthtoken), 'Content-Type': 'application/json'}
    api_url = 'https://api.spotify.com/v1/me/{}'.format(type)
    # api_url = 'https://api.spotify.com/v1/me/playlists'

    limit = 50
    offset = 0
    lastbatch = []
    payload = {'limit': limit, 'offset': offset}
    responseraw = requests.get(api_url, params=payload, headers=auth_header)
    response = json.loads(responseraw.text)

    # check if message='The access token expired'
    # status 401
    if ('error' in response):
        print ("response had an error ",response['error']['status'])
        print ("")

    if len(type) == 0:
        return response.get('display_name')
    items = response['items']

    received = response['limit']*(response['offset'])
    ids=[]

    while (len(items) < response['total']):
        offset+=limit
        payload = {'limit': limit, 'offset': offset}
        response = json.loads(requests.get(api_url, params=payload, headers=auth_header).text)
        lastbatch = response['items']
        items = items + response['items']
        if (type == 'tracks'):
            for track in items:
                ids.append(track["track"]["id"])

    #Sif (len(ids)>0):

    print('retrieved '+str(type)+' size '+str(len(items)))

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    with (open(file_path+'/'+str(type)+'.json', "w")) as outfile:
        json.dump(items, outfile, indent=4)

    return items


@app.route('/audio_features')
@login_required
def getAudioFeatures(file_path='data/'):
    print ("retrieving audio features...")
    library = analyze.loadLibraryFromFiles()

    audioFeatures = library['audio_features']
    if audioFeatures == None:
        audioFeatures = getAudioFeatures(library['tracks'])

    if audioFeatures == None:
        return render_template('index.html', subheader_message="Failed to get audio features ")

    library['audio_features'] = audioFeatures
    #print (" done")

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


    bar = saagraph.create_dataseries()

    return render_template('index.html', sortedA=audioFeatures,
                           subheader_message="Audio features retrieved "+str(len(audioFeatures)),
                           plot=bar)


def getAudioFeatures(tracks, file_path='data/'):
    print ("Retrieving audio features from spotify for type ",type)
    if (session!=None and session.get('token')!=None):
        oauthtoken = session['token']['access_token']
    else:
        print("not loggged in")
        return render_template('index.html', subheader_message="No oauthtoken.. bad flow ")

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
            features+=featureBatch
            limit=100
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



@app.route("/analyze")
def analyzeLocal():

    library = analyze.loadLibraryFromFiles()

    if library:
        start = time.process_time()
        sortedA = analyze.process(library)
        return render_template('index.html', subheader_message="Local data processed in " +
                                                               str(time.process_time() - start)+"ms",
                               sortedA=sortedA, diagramVersion="test")
    else:
        return render_template('index.html', subheader_message="Local data not found. Click to retrieve.")


@app.route("/library")
def getlibrary():
    ds = request.args

    library = analyze.loadLibraryFromFiles()

    tracksWoAlbum = []
    analyze.process(library)

    #for ()

    bar = saagraph.create_dataseries()
    return render_template('index.html', plot=bar)



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


if __name__ == '__main__':
    app.run()

index()