import base64
import io
import urllib
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, redirect, url_for, session, request, render_template, send_file, jsonify, Response, \
    stream_with_context, copy_current_request_context

from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError

import requests
import json

import os
import traceback
import time
import datetime
import threading
import random
import logging
from competitionsApp import fsgtapp
from skala_api import skala_api_app
from competitionsApp import languages
import competitionsEngine
#import locale
import glob
from flask import Flask
#from flask_cors import CORS


from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)



load_dotenv()
# https://docs.authlib.org/en/latest/flask/2/index.html#flask-oauth2-server
# If you are developing on your localhost, remember to set the environment variable:
# export AUTHLIB_INSECURE_TRANSPORT=true

os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')

# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

FACEBOOK_CLIENT_ID=os.getenv("FACEBOOK_CLIENT_ID", None)
FACEBOOK_CLIENT_SECRET=os.getenv("FACEBOOK_CLIENT_SECRET", None)

app = Flask(__name__, static_folder='public', template_folder='views')
app.register_blueprint(fsgtapp)
app.register_blueprint(skala_api_app)

app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)
#CORS(app)

genres = {"test": "1"}
authenticated = False

session_dataLoadingProgressMsg = 'dataLoadingProgressMsg'

gdata = {}
templateArgs = {}
processedDataDir = "/additivespotifyanalyzer"

login_manager = LoginManager()
login_manager.init_app(app)
#login_manager.blueprint_login_views = {
#    'admin': '/admin/login',
#    'site': '/login',
#}

#logging.basicConfig(filename=DATA_DIRECTORY+'/std.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s',
 #                   encoding='utf-8', level=logging.DEBUG)



@login_manager.unauthorized_handler
def unauthorized():
    return "You must be logged in to access this content.", 403


# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    return user_id
    #return User.get(user_id)


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

    UPLOAD_FOLDER = os.path.join(DATA_DIRECTORY,'uploads')
    if not os.path.exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)
        print('Created uploads directory')

    #app_language = 'en_US'
    #locale.setlocale(locale.LC_ALL, app_language)

    #accepted_languages = request.accept_languages
    #print("accepted_languages="+str(accepted_languages))
    #session['language'] = request.accept_languages.best_match(competitionsEngine.supported_languages.keys())

    language_list = glob.glob("language/*.json")
    for lang in language_list:

        #filename = lang.split('\\')
        #lang_code = filename[1].split('.')[0]
        lang_code = lang[9:-5]  # skip language/ and .json

        with open(lang, 'r', encoding='utf8') as file:
            languages[lang_code] = json.loads(file.read())

    competitionsEngine.reference_data['languages'] = languages
    langpack = competitionsEngine.reference_data['languages']['fr_FR']
    competitionsEngine.reference_data['current_language'] = langpack

    competitionsEngine.init()


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
                            filemode=filemode_val
                            )
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


@app.route('/')
def index():
    return redirect("/main")


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
    session['expires_at_localtime'] = None
    session['email'] = None
    session.clear()
    _setUserSessionMsg('You have been logged out')
    spotify.token

    return render_template('login.html',
                           subheader_message="Logged out ",
                           library={}, **session)


@app.route('/logoutfb')
def logoutfb():
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
    session['expires_at_localtime'] = None

    session.clear()
    _setUserSessionMsg('You have been logged out')
    #spotify.token

    return redirect("/main")

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







@app.route('/facebook/')
def facebook():
    # Facebook Oauth Config
    print('client id and secret')
    #print(FACEBOOK_CLIENT_ID)
    #print(FACEBOOK_CLIENT_SECRET)
    oauth.register(
        name='facebook',
        client_id=FACEBOOK_CLIENT_ID,
        client_secret=FACEBOOK_CLIENT_SECRET,
        access_token_url='https://graph.facebook.com/oauth/access_token',
        access_token_params=None,
        authorize_url='https://www.facebook.com/dialog/oauth',
        authorize_params=None,
        api_base_url='https://graph.facebook.com/',
        client_kwargs={'scope': 'email'},
    )

    redirect_uri = url_for('facebook_auth', _external=True)
    return oauth.facebook.authorize_redirect(redirect_uri)


@app.route('/facebook/auth/')
def facebook_auth():
    error = request.args.get('error')
    if error is not None:
        if error == 'access_denied':
            print('access was denied')
        else:
            print('other auth error:')
            print(str(error))
        return redirect('/competitionDashboard')

    logging.info(str(request))
    # check first if auth was succesful

    token = oauth.facebook.authorize_access_token()
    resp = oauth.facebook.get(
        'https://graph.facebook.com/me?fields=id,name,email,picture{url}')
    profile = resp.json()
    print("Facebook User ", profile)
    session['username']=profile['id']
    session['name']=profile['name']
    session['email']=profile['email']
    session['picture']=profile['picture']['data']['url']
    session['expires_at'] = token['expires_at']
    session['expires_at_localtime'] = session['expires_at_localtime'] = int(datetime.datetime.now().timestamp()+int(token['expires_in']))
    session['authsource'] = 'facebook'
    competitionsEngine.user_authenticated_fb(profile['id'], profile['name'],profile['email'],profile['picture']['data']['url'])
    if session.get('wants_url') is not None:
        return redirect(session['wants_url'])
    else:
        return redirect('/competitionDashboard')


@app.route('/google/')
def googleauth():
    # Google Oauth Config
    # Get client_id and client_secret from environment variables
    # For developement purpose you can directly put it
    # here inside double quotes
    #GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    #GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

    CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'

    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url=CONF_URL,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    redirect_uri = url_for('googleauth_reply', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)



@app.route('/google/authaaa/')
def googleauth_replyqq():
    error = request.args.get('error')


@app.route('/google/auth/')
def googleauth_reply():
    error = request.args.get('error')
    if error is not None:
        if error == 'access_denied':
            print('access was denied')
        else:
            print('other auth error:')
            print(str(error))
        return redirect('/competitionDashboard')

    logging.info(str(request))
    # check first if auth was succesful

    token = oauth.google.authorize_access_token()
    profile = oauth.google.parse_id_token(token)
    print(" Google User ", profile)

    session['username']=profile['email']
    session['name']=profile['name']
    session['email']=profile['email']
    session['picture']=profile['picture']
    session['expires_at'] = token['expires_at']
    session['expires_at_localtime'] = session['expires_at_localtime'] = int(datetime.datetime.now().timestamp()+int(token['expires_in']))
    session['authsource'] = 'google'
    competitionsEngine.user_authenticated_google(profile['name'],profile['email'],profile['picture'])

    if session.get('wants_url') is not None:
        return redirect(session['wants_url'])
    else:
        return redirect('/competitionDashboard')






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


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


if __name__ == '__main__':
    print('Executing main')
    #init()


    #fetch_data()
    app.run(host='0.0.0.0', threaded=True, debug=True, ssl_context=('cert.pem', 'key.pem'))




