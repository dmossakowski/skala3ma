from flask import Flask, redirect, url_for, session, request, render_template, jsonify
from flask_oauthlib.client import OAuth, OAuthException
import requests
import json
import analyze


SPOTIFY_APP_ID = '47821343906643e3a7a156c5a3376c6d'
SPOTIFY_APP_SECRET = '73e4faa12b224532ac22e57b39141435'

app = Flask(__name__, static_folder='public', template_folder='views')
app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)
library = {}
genres = {"test": "1"}
authenticated = False

spotify = oauth.remote_app(
    'spotify',
    consumer_key=SPOTIFY_APP_ID,
    consumer_secret=SPOTIFY_APP_SECRET,
    # Change the scope to match whatever it us you need
    # list of scopes can be found in the url below
    # https://developer.spotify.com/web-api/using-scopes/
    request_token_params={'scope': 'playlist-read-private user-library-read	 user-top-read'},
    base_url='https://accounts.spotify.com/',
    request_token_url=None,
    access_token_url='/api/token',
    authorize_url='https://accounts.spotify.com/authorize'

)


@app.route('/')
def index():
    return render_template('index.html')

    accessToken = session.get('access_token')
    session2 = session

    #if (len(library) == 0):
    #    return redirect(url_for('login'))
    #else:
    return redirect(url_for('getlibrary'))


@app.route('/login')
def login():
    print ("doing login first")
    callback = url_for(
        'spotify_authorized',
        _external=True
    )

    callback2 = url_for(
        'spotify_authorized',
        next=request.args.get('next') or request.referrer or None,
        _external=True
    )
    return spotify.authorize(callback=callback2)


@app.route('/login/authorized')
def spotify_authorized():

    resp = spotify.authorized_response()
    print ("spotify calls us now ",str(resp))
    if resp is None:
        return 'Access denied: reason={0} error={1}'.format(
            request.args['error_reason'],
            request.args['error_description']
        )
    if isinstance(resp, OAuthException):
        return 'Access denied: {0}'.format(resp.message)

    session['oauth_token'] = (resp['access_token'], '')

    #
    # me = spotify.get('/v1/me')
    #getPlaylists(session['oauth_token'], 'dmossakowski')

    global authenticated
    authenticated = True
        #print me.data
    return render_template('index.html')
    #return me.data
    #return "logged in"
    #return 'logged in token '.format(session['oauth_token'])
    #return 'Logged in as id={0} name={1} redirect={2}'.format(
     #   me.data['id'],
      #  me.data['name'],
       # request.args.get('next')
    #)




@app.route('/playlists')
def getPlaylists():
    #if (len(library) > 0):
     #   return redirect(url_for('library'))

    print ("getting playlist authenticated? ",authenticated)
    if not authenticated:
        login()

    print ("retrieving playlists...")
    library['playlists'] = getAllItems('playlists')
    print ("retrieving tracks...")
    #library['tracks'] = getAllItems('tracks')
    print ("retrieving albums...")
    #library['albums'] = getAllItems('albums')

    print "getPlaylist done"

    #analyze.modify()

    return render_template('index.html')


def getAllItems(type):
    print ("Retrieving data from spotify for type ",type)
    oauthtoken = get_spotify_oauth_token()[0]
    username = '127108998'
    auth_header = {'Authorization': 'Bearer {token}'.format(token=oauthtoken), 'Content-Type': 'application/json'}
    api_url = 'https://api.spotify.com/v1/users/{}/{}'.format(username ,type)
    # api_url = 'https://api.spotify.com/v1/me/playlists'

    limit = 50
    offset = 0
    lastbatch = []
    payload = {'limit': limit, 'offset': offset}
    response = json.loads(requests.get(api_url, params=payload, headers=auth_header).text)

    items = response['items']

    received = response['limit']*(response['offset'])
    while (len(items) < response['total']):
        offset+=limit
        payload = {'limit': limit, 'offset': offset}
        response = json.loads(requests.get(api_url, params=payload, headers=auth_header).text)
        lastbatch = response['items']
        items = items + response['items']

    print 'retrieved '+str(type)+' size '+str(len(items))

    with (open(str(type)+'.json', "w")) as outfile:
        json.dump(items, outfile, indent=4)

    return items


@spotify.tokengetter
def get_spotify_oauth_token():
    return session.get('oauth_token')



@app.route("/analyze/local")
def analyzeLocal():
    with open("tracks.json","r") as tracksfile:
        tracks = json.load(tracksfile)
        library['tracks'] = tracks

    with open("albums.json","r") as tracksfile:
        tracks = json.load(tracksfile)
        library['albums'] = tracks

    with open("playlists.json", "r") as tracksfile:
        tracks = json.load(tracksfile)
        library['playlists'] = tracks

    sortedA = analyze.process(**library)
    return render_template('index.html', sortedA=sortedA)


@app.route("/library")
def getlibrary():
    ds = request.args

    lib = library

    tracksWoAlbum = []
    analyze.process(**library)

    #for ()


    return render_template('index.html')


@app.route("/hello")
def hello():
    return "Hello mister"

if __name__ == '__main__':
    app.run()

index()