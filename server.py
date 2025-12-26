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
from logging.handlers import TimedRotatingFileHandler
from logging_config import init_logging, attach_request_logging


from main_app_ui import app_ui, languages
from skala_api import skala_api_app, create_jwt

import competitionsEngine

from src.email_sender import EmailSender
from src.email_login import EmailLoginService

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
from flask_babel import Babel, format_date

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

# Spotify configuration (restored)
SPOTIFY_APP_ID = os.getenv("SPOTIFY_APP_ID", "")
SPOTIFY_APP_SECRET = os.getenv("SPOTIFY_APP_SECRET", "")

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
# Register spotify oauth client if credentials available
if SPOTIFY_APP_ID and SPOTIFY_APP_SECRET:
    oauth.register(
        name='spotify',
        client_id=SPOTIFY_APP_ID,
        client_secret=SPOTIFY_APP_SECRET,
        access_token_url='https://accounts.spotify.com/api/token',
        authorize_url='https://accounts.spotify.com/authorize',
        api_base_url='https://api.spotify.com/v1/',
        client_kwargs={'scope': 'user-read-email'}
    )
    spotify = oauth.create_client('spotify')
else:
    spotify = None

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

# Instantiate email login service AFTER bcrypt & captcha are set up
email_login_service = EmailLoginService(competitionsEngine, email_sender, bcrypt, SIMPLE_CAPTCHA)

# Shared helper: return HTML that stores JWT and redirects to target
def _jwt_handoff_redirect(token: str, target: str) -> Response:
    html = (
        """
        <!doctype html>
        <html><head><meta charset='utf-8'><title>Login Complete</title></head>
        <body>
        <script>
        (function(){
            try {
                var t = __TOKEN_PLACEHOLDER__;
                if (t) {
                    localStorage.setItem('skala3ma_jwt', t);
                    // Also set a cookie so normal link navigations include auth
                    var isHttps = (window.location.protocol === 'https:');
                    var secure = isHttps ? '; Secure' : '';
                    // Use SameSite=Lax so cookie is sent on same-site navigations
                    // Add cookie expiration (both Expires and Max-Age for compatibility)
                    var days = 120; // adjust as needed
                    var maxAge = days * 24 * 60 * 60; // seconds
                    var expires = new Date(Date.now() + maxAge * 1000).toUTCString();
                    document.cookie = 'skala3ma_jwt=' + encodeURIComponent(t)
                        + '; Path=/'
                        + '; SameSite=Lax'
                        + '; Expires=' + expires
                        + '; Max-Age=' + maxAge
                        + secure;
                }
            } catch(e) {}
            try {
                window.location.assign('__TARGET_PLACEHOLDER__');
            } catch(e) {
                window.location.href = '__TARGET_PLACEHOLDER__';
            }
        })();
        </script>
        </body></html>
        """
        .replace('__TOKEN_PLACEHOLDER__', json.dumps(token))
        .replace('__TARGET_PLACEHOLDER__', target)
    )
    return Response(html, mimetype='text/html')

# --- Session persistence/cookie settings (fix Android Chrome expiry) ---
# Ensure sessions are treated as permanent and cookies survive browser restarts.
from datetime import timedelta as _td
# OAuth redirects can be cross-site; require SameSite=None for compatibility.
# Note: requires HTTPS with Secure.
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
# Respect environment for Secure flag; default to True in production.
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'



# Initialize the Limiter
limiter = Limiter(
    get_remote_address,
    app=app
    #default_limits=["2000 per day", "5000 per hour"]
)

# Configure Babel
app.config['BABEL_DEFAULT_LOCALE'] = 'en_US'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en_US', 'fr_FR', 'de_DE']

def get_locale():# You can use request.args, request.cookies, or any other method to determine the locale
    return request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])

babel = Babel(app, locale_selector=get_locale)

@app.template_filter('strftime')
def format_datetime(date_str, format=None):
    formats = ["%Y-%m-%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            parsed_date = datetime.datetime.strptime(date_str, fmt)
            formatted_date = parsed_date.strftime("%d-%m-%Y")
            return formatted_date
        except ValueError:
            continue
    return date_str

    



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
    print('initializing server...')

    # Daily rotating log file (midnight) keeping up to 300 historical files
    log_path = os.path.join(DATA_DIRECTORY, 'app.log')
    init_logging(log_file=log_path, console_loglevel=logging.INFO, backup_count=300)
    # Avoid logging API blueprint requests twice by skipping its blueprint name
    attach_request_logging(
        app,
        app_name='web',
        skip_blueprints={'skala_api'},
        allowed_path_substrings=['/gyms', '/activities', '/myactivities', '/myresultats', '/contact', '/competitionDetails',
                                 '/competitionCalendar','/competitionRawAdmin','/competition_admin','/competitionResults',
                                 '/competitionDashboard','/competitions','/newCompetition','/user','/updateuser',
                                 '/competitionFullResults','/competitionStats','/competitionRoutesEntry','/competitionRoutes'])

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




## Logging configuration was refactored into logging_config.init_logging & attach_request_logging
    




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
    if not spotify:
        return render_template('index.html', subheader_message='Spotify not configured', library={}, **session)
    logging.info("doing login %s client_id %s", str(request.referrer), str(SPOTIFY_APP_ID))
    callback = url_for('spotify_authorized', _external=True)
    return spotify.authorize_redirect(callback)


@app.route('/revoke')
def revoke():
    logging.info ("doing revoke")
    return redirect("/")


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
    session['email'] = None
    session.clear()
    _setUserSessionMsg('You have been logged out')
    #spotify.token

    return redirect("/")
 



#@app.route('/authorize')
#def authorize():


@app.route('/login/authorized')
def spotify_authorized():
    if not spotify:
        return redirect('/')
    logging.info("spotify is calling /login/authorized ...")
    try:
        error = request.args.get('error')
        if error:
            logging.info("spotify auth error param: %s", error)
            return render_template('index.html', subheader_message='Not authorized', library={}, **session)
        resp = spotify.authorize_access_token()
        logging.info("spotify calls us now %s", str(resp))
        if not resp:
            return 'Access denied'
        session['token'] = resp
        session['access_token'] = (resp.get('access_token'), '')
        session['refresh_token'] = (resp.get('refresh_token'), '')
        session['expires_at'] = int(datetime.datetime.now().timestamp()+int(1000*60*60*24*365*100))
        session['expires_in'] = resp.get('expires_in')
        session.dataLoadingProgressMsg = ''
        global authenticated
        authenticated = True
        # Fallback if Spotify profile fetch helper not available
        try:
            meProfile = getAllMeItems('')  # type: ignore # legacy helper
        except Exception:
            meProfile = {'id': 'unknown', 'display_name': 'User'}
        session['id'] = meProfile.get('id')
        session['username'] = meProfile.get('display_name')
        if session.get("wants_url"):
            return redirect(session["wants_url"])
        else:
            return redirect("/")
    except OAuthError as e:  # single except
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
    session['expires_at'] = int(datetime.datetime.now().timestamp()+int(1000*60*60*24*365*100))
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
    #session['expires_at'] = token['expires_at']
    session['expires_at'] = int(datetime.datetime.now().timestamp()+int(1000*60*60*24*365*100))
    session['authsource'] = 'google'
    
    user = competitionsEngine.user_authenticated_google(profile['name'],profile['email'],profile['picture'])
    if competitionsEngine.is_god(user) or GODMODE:
        session['godmode'] = True   

    log_request_details('google auth successful '+profile['email'])

    # Issue a JWT and hand off to client via HTML redirect
    try:
        user_id = user.get('id') if isinstance(user, dict) else None
        token = create_jwt(
            session.get('email'),
            user_id,
            name=session.get('name'),
            authsource=session.get('authsource'),
            expires_at=session.get('expires_at'),
            picture=session.get('picture'),
        )
    except Exception:
        token = ''
    target = session.get('wants_url') or '/profile'
    return _jwt_handoff_redirect(token, target)




# first service to be called
# if email found and password matches then log the user in
@app.route('/email_login', methods=['POST'])
@limiter.limit("3 per minute")
def email_login():
    email = request.form.get('email')
    password = request.form.get('password')
    error = None

    if not email or not password:
        return render_template('competitionLogin.html', reference_data=competitionsEngine.reference_data, error=get_translation('User_does_not_exist_or_wrong_password'))

    email = email.lower()
    user = competitionsEngine.get_user_by_email(email)
    if user is None:
        return render_template('competitionLogin.html', reference_data=competitionsEngine.reference_data, email=email, error=get_translation('User_does_not_exist_or_wrong_password'))

    if user.get('password') is None:
        error = get_translation('You_must_set_your_password')
        return render_template('change_password.html', reference_data=competitionsEngine.reference_data, email=email, error=error)

    if user.get('is_confirmed') is not None and user.get('is_confirmed') is False:
        error = get_translation('User_not_confirmed_Please_check_your_email_for_confirmation_link')
        return render_template('competitionLogin.html', reference_data=competitionsEngine.reference_data, email=email, error=error)

    if user.get('fpictureurl') is not None or user.get('gpictureurl') is not None:
        error = get_translation('User_is_registered_with_Google_or_Facebook_Please_click_the_appropriate_button_to_login')
        return render_template('competitionLogin.html', reference_data=competitionsEngine.reference_data, email=email, error=error)

    if bcrypt.check_password_hash(user.get('password'), password):
        log_request_details('user logged in with password: '+email)
        session['username'] = user.get('email')
        session['email'] = user.get('email')
        session['picture'] = '/public/images/favicon.png'
        session['expires_at'] = int(datetime.datetime.now().timestamp()+int(1000*60*60*24*365*100))
        session['authsource'] = 'self'
        if competitionsEngine.is_god(user) or GODMODE:
            session['godmode'] = True
        # Also issue a JWT and hand off to the client for API calls
        try:
            user_id = user.get('id') if isinstance(user, dict) else None
            token = create_jwt(
                session.get('email'),
                user_id,
                name=session.get('username') or session.get('email'),  # or use user.get('firstname') if available
                authsource=session.get('authsource'),
                expires_at=session.get('expires_at'),
                picture=session.get('picture'),
            )
        except Exception:
            token = ''
        target = session.get('wants_url') or '/profile'
        return _jwt_handoff_redirect(token, target)

    log_request_details('User failed login '+email)
    error = get_translation('User_does_not_exist_or_wrong_password')
    return render_template('competitionLogin.html', reference_data=competitionsEngine.reference_data, email=email, error=error)



@app.route('/register', methods=['GET'])
def register_with_email():
    result = email_login_service.register_with_email()
    return render_template(result['template'], **result['context'])


# the user wants to register so send the confirmation email
# or the user needs to reset the password
@app.route('/register', methods=['POST'])
@limiter.limit("2 per minute")
def register():
    result = email_login_service.register(request.form)
    return render_template(result['template'], **result['context'])




@app.route('/forgot_password')
def forgot_password():
    result = email_login_service.forgot_password()
    return render_template(result['template'], **result['context'])


# this endpoint only gets two passwords from change_passsword.html
# the user must already be confirmed which means that their email is valid and they are in the database
# they would also then have the email put in their session
@app.route('/change_password', methods=['POST'])
@limiter.limit("5 per minute")
def change_password():
    result = email_login_service.change_password(request.form.get('password'), request.form.get('password2'))
    return render_template(result['template'], **result['context'])
    

@app.route('/confirm/<type>/<token>', methods=['GET'])
@limiter.limit("5 per minute")
def confirm_email(type, token):
    result = email_login_service.confirm_email(type, token)
    return render_template(result['template'], **result['context'])


def after_login(user, email):
    return render_template('user-home.html',
                        reference_data=competitionsEngine.reference_data,
                        email=email,
                        climber=user,
                        logged_email=email)

   


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




#################################################
#### CONTACT
#################################################
@app.route('/contact')
def contact():
    email = session.get('email')
    if email is None:
        email = ''
    name = session.get('name')
    if name is None:
        name = ''

    new_captcha_dict = SIMPLE_CAPTCHA.create()
    return render_template("contact.html",
                           reference_data=competitionsEngine.reference_data,
                           email=email,
                           name=name,
                           captcha=new_captcha_dict)



@app.route('/contact', methods=['POST'])
def contact_post():
    session_email = session.get('email')
    new_captcha_dict = SIMPLE_CAPTCHA.create()
    email = request.form.get('email')
    name = request.form.get('name')
    message = request.form.get('message')
    subject = request.form.get('subject')
    c_hash = request.form.get('captcha-hash')
    c_text = request.form.get('captcha-text')


    if not email or not name or not message or not subject:
        return render_template('contact.html',
                           reference_data=competitionsEngine.reference_data,
                           captcha=new_captcha_dict,
                           email=email,
                           name=name,
                           subject=subject,
                           message=message,
                           top_notification_label=get_translation('all_fields_required'),
                           top_notification_level='danger')

    if not SIMPLE_CAPTCHA.verify(c_text, c_hash):
        time.sleep(1)
        return render_template("contact.html",
                           reference_data=competitionsEngine.reference_data,
                           captcha=new_captcha_dict,
                            email=email,
                            name=name,
                            subject=subject,
                            message=message,
                            top_notification_label=get_translation('Bad_captcha'),
                            top_notification_level='danger')
    else:
        email_sender.send_contact_email(session_email, email, name, subject, message)
        return render_template('contact.html',
                           reference_data=competitionsEngine.reference_data,
                           captcha=new_captcha_dict,
                           email=email,
                           name=name,
                           subject=subject,
                           message=message,
                           top_notification_label=get_translation('Email_sent'),
                           top_notification_level='success')
                           







@app.route('/competition_contact/<competitionId>')
def competition_contact(competitionId):

    competition = None
    new_captcha_dict = SIMPLE_CAPTCHA.create()

    if competitionId is not None:
        competition = competitionsEngine.get_competition(competitionId)

    if competition is None:
        return redirect("/competitionDashboard")
    
    elif competition is LookupError:
        return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist was not found",
                                   library={},
                                   **session)
    elif len(competition) == 0:

        return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)
    subject=competition['name']+ ' - '+competition['date']
    subheader_message = "CompetitionDetails '" + competition['name'] + "' on "+competition['date']

    return render_template("competitionContact.html", 
                           competitionId=competitionId,
                           competition=competition,
                           subject=subject,
                           captcha=new_captcha_dict,
                           subheader_message=subheader_message,
                           reference_data=competitionsEngine.reference_data,
                           library=None,
                           **session)






@app.route('/competition_contact/<competitionId>', methods=['POST'])
@limiter.limit("2 per minute")
def competition_contact_post(competitionId):
    new_captcha_dict = SIMPLE_CAPTCHA.create()
    email = request.form.get('email')
    name = request.form.get('name')
    message = request.form.get('message')
    subject = request.form.get('subject')
    c_hash = request.form.get('captcha-hash')
    c_text = request.form.get('captcha-text')

    if competitionId is not None:
        competition = competitionsEngine.get_competition(competitionId)

    if competition is None:
        return redirect("/competitionDashboard")
    

    if not email or not name or not message or not subject:
        return render_template('competitionContact.html',
                               competitionId=competitionId,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           captcha=new_captcha_dict,
                           email=email,
                           name=name,
                           subject=subject,
                           message=message,
                           top_notification_label=get_translation('all_fields_required'),
                           top_notification_level='danger')

    if not SIMPLE_CAPTCHA.verify(c_text, c_hash):
        time.sleep(1)
        return render_template("competitionContact.html",
                               competitionId=competitionId,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           captcha=new_captcha_dict,
                            email=email,
                            name=name,
                            subject=subject,
                            message=message,
                            top_notification_label=get_translation('Bad_captcha'),
                            top_notification_level='danger')
    else:

        competition_string = competition['name'] + ' - ' + competition['date']
        emails_to = competitionsEngine.get_user_emails_with_competition_id(competitionId)

        competition_url = url_for('competition_contact', competitionId=competitionId, _external=True)
      
        email_sender.send_email_to_organizer(email, name, subject, message, emails_to, competition_string, competition_url)
        
        return render_template('competitionContact.html',
                               competitionId=competitionId,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           captcha=new_captcha_dict,
                           email=email,
                           name=name,
                           subject=subject,
                           message=message,
                           top_notification_label=get_translation('Email_sent'),
                           top_notification_level='success')
                           



@app.route("/hello")
def hello():
    return "Hello mister"






# this is not executed by gunicorn but only when running direclty by Python
if __name__ == '__main__':
    print('Executing server main')
    init()

    # setting debug=True is not needed with vscode
    # after initial start the app server starts again with line:
    #     Restarting with stat 
    app.run(host='0.0.0.0', port=3000, threaded=True, debug=True, ssl_context=('cert.pem', 'key.pem'))

 
