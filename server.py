#    Copyright (C) 2023 David Mossakowski
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.



import base64
import io
import urllib
import os
import traceback
import time
import datetime
import threading
import random

from functools import wraps

#import fastapi_test  
from dotenv import load_dotenv
load_dotenv(override=True)

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')
GODMODE = os.getenv('GODMODE') == 'true'

print("server DATA_DIRECTORY="+str(DATA_DIRECTORY))

if DATA_DIRECTORY is None:
    DATA_DIRECTORY = os.getcwd()
elif not os.path.exists(DATA_DIRECTORY):
    print("DATA_DIRECTORY '"+str(DATA_DIRECTORY)+"' does not exist. Creating it...'")
    os.makedirs(DATA_DIRECTORY)

from flask import Flask, redirect, url_for, session, Request, request, render_template, send_file, jsonify, Response, \
    stream_with_context, copy_current_request_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError

import requests
import json

import logging


from main_app_ui import app_ui, languages
from skala_api import skala_api_app

import competitionsEngine

from src.email_sender import EmailSender

# Initialize EmailSender with necessary configurations
email_sender = EmailSender(
    reference_data=competitionsEngine.reference_data
)
#import locale
import glob
from flask import Flask


from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer

#from flask_openapi3 import OpenAPI, Info, Tag

# https://docs.authlib.org/en/latest/flask/2/index.html#flask-oauth2-server
# If you are developing on your localhost, remember to set the environment variable:
# export AUTHLIB_INSECURE_TRANSPORT=true

os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"


# Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

FACEBOOK_CLIENT_ID=os.getenv("FACEBOOK_CLIENT_ID", None)
FACEBOOK_CLIENT_SECRET=os.getenv("FACEBOOK_CLIENT_SECRET", None)

SMTP_API_KEY = os.getenv("SMTP_API_KEY")

# workaround to hardcoded limit in Request class
# https://stackoverflow.com/questions/77949949/413-request-entity-too-large-flask-werkzeug-gunicorn-max-content-length
class CustomRequest(Request):
    def __init__(self, *args, **kwargs):
        super(CustomRequest, self).__init__(*args, **kwargs)
        self.max_form_parts = 2000

#info = Info(title='Skala3ma API', version='1.0.0', summary='API to interact with skala3ma', description='description of api')
#app = OpenAPI(__name__, static_folder='public', template_folder='views', info=info)
app = Flask(__name__, static_folder='public', template_folder='views')
app.request_class = CustomRequest
# limit image upload size to 4mb
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024
app.register_blueprint(app_ui)
app.register_blueprint(skala_api_app)

app.debug = True
app.secret_key = 'development'
oauth = OAuth(app)

bcrypt = Bcrypt(app)

from flask_simple_captcha import CAPTCHA
YOUR_CONFIG = {
    'SECRET_CAPTCHA_KEY': GOOGLE_CLIENT_SECRET,
    'CAPTCHA_LENGTH': 6,
    'CAPTCHA_DIGITS': False,
    'EXPIRE_SECONDS': 600,
}
SIMPLE_CAPTCHA = CAPTCHA(config=YOUR_CONFIG)
app = SIMPLE_CAPTCHA.init_app(app)


# Initialize the Limiter
limiter = Limiter(
    get_remote_address,
    app=app
    #default_limits=["2000 per day", "5000 per hour"]
)

# Custom rate limit exceeded handler
#@limiter.request_filter
#def rate_limit_exceeded():
##    remote_addr = request.remote_addr
 #   logging.warning(f"Rate limit exceeded by IP address: {remote_addr}")
 #   return True  # Continue processing the request

#from fastapi.middleware.wsgi import WSGIMiddleware
#fastapi_test.fastapitest.mount("/", WSGIMiddleware(app))

genres = {"test": "1"}
authenticated = False

# language set before any other request comes in
startup_language='fr_FR'

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


def init():
    print ('initializing server...')

    #init_logging(log_file=DATA_DIRECTORY+'/l.log',  console_loglevel=logging.DEBUG)
    #init_logging(console_loglevel=logging.DEBUG)
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
    # this sets up the initial language of the app
    langpack = competitionsEngine.reference_data['languages'][competitionsEngine.first_default_language]
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
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    #global LOG
    #LOG = logging.getLogger(__name__)
    




def login_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session != None and session.get('expires_at') is not None:
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


#@app.route('/')
#def index():
#    return redirect("/main")


@app.errorhandler(404)
@app.errorhandler(500)
def page_not_found(e):
    # You can render a custom 404 template or return a simple message
    return render_template('404.html', reference_data=competitionsEngine.reference_data,), 404

@app.errorhandler(Exception)
def handle_exception(error):
    logging.error(f"Unexpected error: {error}", exc_info=True)
    return render_template('404.html', reference_data=competitionsEngine.reference_data,error=error), 404


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
    session.pop('email', None)
    session['access_token'] = None
    session['logged_in'] = False
    session['refresh_token'] = None
    session['expires_at'] = None
    session['expires_in'] = None
    session['expires_at_localtime'] = None
    session['email'] = None
    session.clear()
    _setUserSessionMsg('You have been logged out')
    #spotify.token

    return redirect("/")

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

       
        global authenticated
        authenticated = True
       
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
        return after_login(user, None)

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

    user = competitionsEngine.user_authenticated_fb(profile['id'], profile['name'],profile['email'],profile['picture']['data']['url'])
    if competitionsEngine.is_god(user) or GODMODE:
        session['godmode'] = True   

    if session.get('wants_url') is not None:
        return redirect(session['wants_url'])
    else:
        return after_login(user, profile.get('email'))
    
    


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

    log_request_details('google auth')

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
        return redirect('/activities')

    logging.info(str(request))
    # check first if auth was succesful

    token = oauth.google.authorize_access_token()
    profile1 = oauth.google.get('https://www.googleapis.com/oauth2/v1/userinfo')
    profile = token.get('userinfo')
    #profile = oauth.google.parse_id_token(token)
    #print(" Google User ", profile)

    session['username']=profile['email']
    session['name']=profile['name']
    session['email']=profile['email']
    session['picture']=profile['picture']
    session['expires_at'] = token['expires_at']
    session['expires_at_localtime'] = session['expires_at_localtime'] = int(datetime.datetime.now().timestamp()+int(token['expires_in']))
    session['authsource'] = 'google'
    
    user = competitionsEngine.user_authenticated_google(profile['name'],profile['email'],profile['picture'])
    if competitionsEngine.is_god(user) or GODMODE:
        session['godmode'] = True   

    log_request_details('google auth successful '+profile['email'])

    if session.get('wants_url') is not None:
        return redirect(session['wants_url'])
    else:
        return after_login(user, profile.get('email'))




# first service to be called
# if email found and password matches then log the user in
@app.route('/email_login', methods=['POST'])
@limiter.limit("3 per minute")
def email_login():
    f = request.form
    #print(request.form)

    email = request.form.get('email')
    password = request.form.get('password')
    error = None

    if not email or not password:
        return render_template('competitionLogin.html',
                               reference_data=competitionsEngine.reference_data,
                               error=get_translation('User_does_not_exist_or_wrong_password'))
                        
    email = email.lower()
    user = competitionsEngine.get_user_by_email(email)

    if user is None:
        return render_template('competitionLogin.html',
                               reference_data=competitionsEngine.reference_data,
                               email=email,
                               error=get_translation('User_does_not_exist_or_wrong_password'))
    
    if user.get('password') is None:
        error = get_translation('You_must_set_your_password')
        return render_template('change_password.html',
                               reference_data=competitionsEngine.reference_data,
                               email=email,
                               error=error)

    if user.get('is_confirmed') is not None and user.get('is_confirmed') == False:
        error = get_translation('User_not_confirmed_Please_check_your_email_for_confirmation_link')
        return render_template('competitionLogin.html',
                               reference_data=competitionsEngine.reference_data,
                               email=email,
                               error=error)
    
    if user.get('fpictureurl') is not None or user.get('gpictureurl') is not None:
        error = get_translation('User_is_registered_with_Google_or_Facebook_Please_click_the_appropriate_button_to_login')
        return render_template('competitionLogin.html',
                               reference_data=competitionsEngine.reference_data,
                               email=email,
                               error=error)
    
    if bcrypt.check_password_hash(user.get('password'), password):
        log_request_details('user logged in with password: '+email)
        session['username'] = user.get('email')
        session['email']=user.get('email')
        session['picture']='/public/images/favicon.png'
        session['expires_at'] = int(datetime.datetime.now().timestamp()+int(1000*60*60*24))
        #session['expires_at_localtime'] = session['expires_at_localtime'] = int(datetime.datetime.now().timestamp()+int(token['expires_in']))
        session['authsource'] = 'self'
        
        if competitionsEngine.is_god(user) or GODMODE:
            session['godmode'] = True   

        return after_login(user, email)
        
    else:
        log_request_details('User failed login '+email)
        error=get_translation('User_does_not_exist_or_wrong_password')

    
    return render_template('competitionLogin.html',
                           reference_data=competitionsEngine.reference_data,
                           email=email,
                           error=error)



@app.route('/register', methods=['GET'])
def register_with_email():
    new_captcha_dict = SIMPLE_CAPTCHA.create()
    time.sleep(1)
    return render_template('register.html',
                           reference_data=competitionsEngine.reference_data,
                           captcha=new_captcha_dict
                           )


# the user wants to register so send the confirmation email
# or the user needs to reset the password
@app.route('/register', methods=['POST'])
@limiter.limit("2 per minute")
def register():
    new_captcha_dict = SIMPLE_CAPTCHA.create()
    email = request.form.get('email')
    if not email:
        return render_template('register.html',
                               reference_data=competitionsEngine.reference_data,
                               error=get_translation('Please_try_again'),
                               email=email,
                               captcha=new_captcha_dict)
    
    
    c_hash = request.form.get('captcha-hash')
    c_text = request.form.get('captcha-text')
    if not SIMPLE_CAPTCHA.verify(c_text, c_hash):
        time.sleep(1) # this is to slow down the brute force attack
        log_request_details('captcha failed '+email)
        return render_template('register.html',
                               reference_data=competitionsEngine.reference_data,
                               error=get_translation('Please_try_again'),
                               email=email,
                               captcha=new_captcha_dict)
    
    email = email.lower()
    
    user = competitionsEngine.get_user_by_email(email)

    if user is not None and user.get('is_confirmed') == False:
        send_registration_email(email)
        log_request_details('resending registration email to user already registered but not confirmed '+email)
        return render_template('competitionLogin.html',
                               reference_data=competitionsEngine.reference_data,
                               error=get_translation('Please_check_your_email_for_confirmation_link'),
                               email=email)

    if user is not None and user.get('is_confirmed') == True:
        token = generate_token(email)
        confirm_url = url_for('confirm_email', type='reset_password', token=token, _external=True)
        email_sender.send_password_reset_email(email, confirm_url)
        log_request_details("reset password email sent to "+email)
        return render_template('competitionLogin.html',
                               reference_data=competitionsEngine.reference_data,
                               error=get_translation('Link_to_reset_password_sent_to_email'))

    ## send email to confirm registration
    send_registration_email(email)
    log_request_details('sending registration email to '+email)
    return render_template('register.html',
                           reference_data=competitionsEngine.reference_data,
                           error=get_translation('Please_check_your_email_for_confirmation_link'),
                           email=email,
                           captcha=new_captcha_dict)




@app.route('/forgot_password')
def forgot_password():
    #if session.get('email') is None:
     #   return render_template('competitionLogin.html',
      #                         reference_data=competitionsEngine.reference_data,
       #                        error=get_translation('Login_first_to_change_your_password'),
        #                       email=session.get('email'))
    new_captcha_dict = SIMPLE_CAPTCHA.create()
    return render_template('register.html',
                           reference_data=competitionsEngine.reference_data,
                           action='forgot_password',
                           captcha=new_captcha_dict)


# this endpoint only gets two passwords from change_passsword.html
# the user must already be confirmed which means that their email is valid and they are in the database
# they would also then have the email put in their session
@app.route('/change_password', methods=['POST'])
@limiter.limit("5 per minute")
def change_password():
    email = session.get('email')
    if email is None:
        return render_template('competitionLogin.html',
                           reference_data=competitionsEngine.reference_data,
                           error='Please login first')

    password = request.form.get('password')
    password2 = request.form.get('password2')
    email = email.lower()

    if not email or not password or not password2 or password != password2 or len(password) < 6:
        return render_template('change_password.html',
                           reference_data=competitionsEngine.reference_data,
                           error=get_translation('Invalid_parameters_passwords_do_not_match_or_password_too_short'),
                           email=email)
                        
    user = competitionsEngine.get_user_by_email(email)

    if user is None:
        new_captcha_dict = SIMPLE_CAPTCHA.create()
        return render_template('register.html',
                           reference_data=competitionsEngine.reference_data,
                           error=None,
                           captcha=new_captcha_dict)
    

    password = bcrypt.generate_password_hash(password).decode('utf-8')

    user = competitionsEngine.user_authenticated(email, password)
    
    
    return render_template('competitionLogin.html',
                           reference_data=competitionsEngine.reference_data,
                           error=get_translation('Please_login_again_with_your_new_password'),
                           email=email)
    

def send_registration_email(email):
    token = generate_token(email)
    confirm_url = url_for('confirm_email', type='register', token=token, _external=True)
    ret = email_sender.send_registration_email(email, confirm_url)
    return 'mail sent'+ret


def generate_token(email):
    serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
    return serializer.dumps(email, salt=os.getenv("SECURITY_PASSWORD_SALT"))


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(os.getenv("SECRET_KEY"))
    try:
        email = serializer.loads(
            token, salt=os.getenv('SECURITY_PASSWORD_SALT'), max_age=expiration
        )
        return email
    except Exception as e:
        print(e)
        return False
    

# this path is called when the user clicks the confirmation link in the email
# we will add the user to the db here because the mail is confirmed
# we add the email to the session so that we match it with the password change request
@app.route("/confirm/<type>/<token>", methods=["GET"])
@limiter.limit("5 per minute")
def confirm_email(type, token):
    
    email = confirm_token(token)

    if email is False:
        new_captcha_dict = SIMPLE_CAPTCHA.create()
        log_request_details('Invalid or expired token ')
        return render_template('register.html',
                           reference_data=competitionsEngine.reference_data,
                           error='Invalid or expired token. ',
                           captcha=new_captcha_dict)
    
    user = competitionsEngine.get_user_by_email(email)

    if user is not None and user.get('is_confirmed') == True and type == 'register':
        log_request_details('user already confirmed, need to login normallly '+email)
        return render_template('competitionLogin.html',
                           reference_data=competitionsEngine.reference_data,
                           error='User already confirmed. Please login. ')

    user = competitionsEngine.confirm_user(email)

    session['username'] = user.get('email')
    session['email']=user.get('email')
    session['access_token'] = token

    return render_template('change_password.html',
                           reference_data=competitionsEngine.reference_data,
                           error=None,)


def after_login(user, email):
    if user.get('club') is None or user.get('club').strip() == '' or user.get('firstname') is None or user.get('firstname').strip() == '':
        return render_template('climber.html',
                        reference_data=competitionsEngine.reference_data,
                        email=email,
                        climber=user,
                        logged_email=email)

    if user.get('gymid') is not None:
        return redirect("/gyms/"+user.get('gymid'))
    
    return redirect('/')
        #render_template('competitionDashboard.html',
            #              reference_data=competitionsEngine.reference_data,
            #             email=email,
            #            error=error)


def log_request_details(msg=''):
    logging.info('Event: '+msg+' URL: ' + request.url+' headers: ' + str(request.headers) + 
            ' Client IP: ' + request.remote_addr+' form data: ' + str(request.form))




def get_translation(key):
    if key in competitionsEngine.reference_data['current_language']:
        return competitionsEngine.reference_data['current_language'][key]
    else:
        return key  # or return a default message like "Translation not found"

    
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

@app.route('/test')
def test():
    return render_template('test.html')

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


# this is not executed by gunicorn but only when running direclty by Python
if __name__ == '__main__':
    print('Executing server main')
    init()

    # setting debug=True is not needed with vscode
    # after initial start the app server starts again with line:
    #     Restarting with stat 
    app.run(host='0.0.0.0', port=3000, threaded=True, debug=True, ssl_context=('cert.pem', 'key.pem'))






