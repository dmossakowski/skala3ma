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

from copy import deepcopy
import json
import os
import io
import glob
import random
import uuid
import time
from datetime import datetime, date, timedelta
import competitionsEngine
import csv
from functools import wraps
from dataclasses import dataclass

from flask import Flask, redirect, url_for, session, request, render_template, send_file, send_from_directory, jsonify, Response, \
    stream_with_context, copy_current_request_context, g

import logging
from logging_config import attach_request_logging

from flask import Blueprint
import activities_db as activities_db

import skala_db

from io import BytesIO

from flask import send_file
from collections import defaultdict
#import Activity

#from flask_openapi3 import APIBlueprint, OpenAPI, Tag

#book_tag = Tag(name="book", description="Some Book")

#comp_tag = Tag(name="competition", description="""
#        Some competition
#        with multiple lines 
#        #header also
#        """)

# Third party libraries
from flask import Flask, redirect, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from oauthlib.oauth2 import WebApplicationClient
import requests

from pydantic import BaseModel
# Email login service (shared with server)
from src.email_login import EmailLoginService
from src.email_sender import EmailSender
import jwt
# Google auth (optional)
try:
    from google.oauth2 import id_token as google_id_token  # type: ignore
    from google.auth.transport import requests as google_requests  # type: ignore
    GOOGLE_AUTH_AVAILABLE = True
except Exception:
    GOOGLE_AUTH_AVAILABLE = False

from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError

languages = {}

grades = ['?', '1', '2', '3', '4a', '4b', '4c', '5a','5a+', '5b', '5b+', '5c','5c+', '6a', '6a+', '6b', '6b+', '6c', '6c+', '7a', '7a+', '7b', '7b+', '7c', '7c+', '8a', '8a+', '8b', '8b+', '8c', '8c+', '9a', '9a+', '9b', '9b+', '9c']
    

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')

if DATA_DIRECTORY is None:
    DATA_DIRECTORY = os.getcwd()

COMPETITIONS_DB = DATA_DIRECTORY + "/db/competitions.sqlite"

# ID, date, name, location
COMPETITIONS_TABLE = "competitions"
# ID, name, club, m/f, list of climbs
CLIMBERS_TABLE = "climbers"

FSGT_APP_ID = os.getenv('FSGT_APP_ID')
FSGT_APP_SECRET = os.getenv('FSGT_APP_SECRET')

GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

#skala_api_app = APIBlueprint('skala_api', __name__, url_prefix='/api1', doc_ui=True, abp_tags= [book_tag, comp_tag])
skala_api_app = Blueprint('skala_api', __name__, url_prefix='/api1')
attach_request_logging(
    skala_api_app,
    app_name='api',
    allowed_path_substrings=['/api1']
)

skala_api_app.debug = True
skala_api_app.secret_key = 'development'
oauth = OAuth(skala_api_app)

genres = {"test": "1"}
authenticated = False

# Initialize email login service (captcha None for API)
_email_sender = EmailSender(reference_data=competitionsEngine.reference_data)
email_login_service_api = EmailLoginService(competitionsEngine, _email_sender, bcrypt=None, simple_captcha=None)  # bcrypt later bound

try:
    # Attempt to import bcrypt instance from server if available
    from server import bcrypt as _bcrypt_instance  # type: ignore
    email_login_service_api.bcrypt = _bcrypt_instance
except Exception:
    pass

# Third party libraries
from flask import Flask, redirect, request, url_for

from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from oauthlib.oauth2 import WebApplicationClient
import requests

# Internal imports
# Flask app setup

skala_api_app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

UPLOAD_FOLDER = os.path.join(DATA_DIRECTORY,'uploads')
ALLOWED_EXTENSIONS = set(['txt', 'png', 'jpg', 'jpeg', 'gif'])

# skala_api_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


#from flask_openapi3 import Info, Tag
#from flask_openapi3 import OpenAPI


#info = Info(title="book API", version="1.0.0")
#book_tag = Tag(name="book", description="Some Book")



class Activity1(BaseModel):
    activity_name: str
    gym_id: str
    date: datetime
    

# User session management setup
# https://flask-login.readthedocs.io/en/latest

@skala_api_app.before_request
def x(*args, **kwargs):
    #logging.debug('api before request '+str(session.get('language'))+ ' accepted languages='+str(request.accept_languages))
    if not session.get('language'):
        #kk = competitionsEngine.supported_languages.keys()
        language = request.accept_languages.best_match(competitionsEngine.supported_languages.keys())
        if language is None:
            language = 'fr_FR'
        session['language'] = language
        recreate_session_from_jwt()
    #logging.debug ("api setting language to session language="+str(session['language']))
    set_language(session['language'])   
    


@skala_api_app.route('/api/language/<language>')
def set_language(language=None):
    if language is None:
        language = 'fr_FR'
    session['language'] = language
    #logging.debug('api setting language requested to '+str(language))
    langpack = competitionsEngine.reference_data['languages'].get(language)
    if langpack is None:
        if language.startswith('pl'):
            langpack = competitionsEngine.reference_data['languages']['pl_PL']
        elif language.startswith('en'):
            langpack = competitionsEngine.reference_data['languages']['en_US']
        elif language.startswith('fr'):
            langpack = competitionsEngine.reference_data['languages']['fr_FR']
        else:
            langpack = competitionsEngine.reference_data['languages']['fr_FR']
            logging.warning('api setting language not found '+str(language))

    competitionsEngine.reference_data['current_language'] = langpack
    return language


@skala_api_app.route('/language')
def get_translations():
    language = session.get('language')
    if language is None:
        language = 'fr_FR'
    langpack = competitionsEngine.reference_data['languages'].get(language)
    return langpack
    

@skala_api_app.route('/language')
def get_language():
    if not session.get('language'):
        return json.dumps({'language': 'fr_FR'})
    else:
        return json.dumps({'language': session['language']})


@skala_api_app.route('/langpack')
def get_default_langpack():
    if not session.get('language'):
        return json.dumps(competitionsEngine.reference_data['languages']['fr_FR'])
    else:
        return json.dumps(competitionsEngine.reference_data['languages'][session.get('language')])


@skala_api_app.route('/langpack/<language>')
def get_langpack(language=None):
    if not session.get('language'):
        return json.dumps(competitionsEngine.reference_data['languages']['fr_FR'])
    else:
        set_language(language)
        return json.dumps(competitionsEngine.reference_data['languages'][session.get('language')])




def is_logged_in():
    if session is not None and session.get('expires_at') is not None:
        return True
    else:
        session["wants_url"] = request.url
        return False


# ---------------- JWT SUPPORT -----------------
JWT_SECRET = os.getenv('JWT_SECRET', os.getenv('SECRET_KEY', 'dev-secret'))
JWT_ALG = 'HS256'
JWT_EXP_SECONDS = 60 * 60 * 24 * 356 * 100  # 100 years

def create_jwt(
    email: str,
    user_id: str | None = None,
    *,
    name: str | None = None,
    authsource: str | None = None,
    expires_at: int | None = None,
    picture: str | None = None,
):
    now = int(time.time())
    payload = {
        'sub': email,
        'uid': user_id,
        'iat': now,
        'exp': now + JWT_EXP_SECONDS,
    }
    # Prefer explicit parameters, fallback to session values
    if name or session.get('name'):
        payload['name'] = name if name is not None else session.get('name')
    if authsource or session.get('authsource'):
        payload['authsource'] = authsource if authsource is not None else session.get('authsource')
    if expires_at or session.get('expires_at'):
        payload['expires_at'] = expires_at if expires_at is not None else session.get('expires_at')
    if picture is not None:
        payload['picture'] = picture
    elif session.get('picture') is not None:
        payload['picture'] = session.get('picture')
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_jwt(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        return {'error': 'token_expired'}
    except Exception:
        return {'error': 'invalid_token'}


def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:].strip() if auth_header.startswith('Bearer ') else None
        if not token:
            return jsonify({'error': 'missing_token'}), 401
        decoded = decode_jwt(token)
        if 'error' in decoded:
            return jsonify({'error': decoded['error']}), 401
        request.jwt_email = decoded.get('sub')  # type: ignore
        return fn(*args, **kwargs)
    return wrapper


def session_or_jwt_required(fn):
    """Allow either JWT (Authorization: Bearer) or existing session email."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        recreate_session_from_jwt
        if not session.get('email'):
            return jsonify({'error': 'unauthorized'}), 401
        return fn(*args, **kwargs)
    return wrapper


def recreate_session_from_jwt():
    email = None
    expires_at = None
    picture = None
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        decoded = decode_jwt(auth_header[7:].strip())
        if isinstance(decoded, dict) and 'error' not in decoded:
            email = decoded.get('sub')
            expires_at = decoded.get('exp')
            picture = decoded.get('picture')
            session['email'] = email  # ensure session email set
            session['expires_at'] = expires_at  # type: ignore
            session['picture'] = picture  # type: ignore

    if not email:
        cookie_token = request.cookies.get('skala3ma_jwt')
        if cookie_token:
            decoded = decode_jwt(cookie_token)
            if isinstance(decoded, dict) and 'error' not in decoded:
                email = decoded.get('sub')
                expires_at = decoded.get('exp')
                picture = decoded.get('picture')
                session['email'] = email  # ensure session email set
                session['expires_at'] = expires_at  # type: ignore
                session['picture'] = picture  # type: ignore


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        email = session.get('email') if session else None
        if email:
            user = competitionsEngine.get_user_by_email(email)
            if user:
                perms = user.get('permissions', {}) or {}
                if perms.get('godmode') or user.get('godmode'):
                    return fn(*args, **kwargs)
                gen = perms.get('general') or []
                if isinstance(gen, list) and ('create_gym' in gen or 'manage_users' in gen):
                    return fn(*args, **kwargs)
        return jsonify({'error': 'admin_required'}), 403
    return wrapper


#@skala_api_app.get('/apitest', tags=[book_tag, comp_tag])
def testapi():
    return {"code": 0, "message": "ok"}



@skala_api_app.post('/competitionRawAdmin')
@session_or_jwt_required
def fsgtadmin():
    edittype = request.form.get('edittype')
    id = request.form.get('id')
    action = request.form.get('action')
    jsondata = request.form.get('jsondata')
    comp = {}
    jsonobject = None

    if jsondata is not None and len(jsondata) > 2:
        jsonobject = json.loads(jsondata)

    if edittype == 'user':
        if jsonobject is not None and action == 'update':
            competitionsEngine.upsert_user(jsonobject)

        if id is not None and action == 'find':
            jsonobject = competitionsEngine.get_user_by_email(id)

        if id is not None and action == 'findall':
            jsonobject = competitionsEngine.get_all_user_emails()

    elif edittype == 'competition':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            competitionsEngine._update_competition(jsonobject['id'],jsonobject)
        if id is not None  and action == 'delete':
            #jsonobject = {"success": "competition updated"}
            competitionsEngine.delete_competition(id)
        if id is not None and action == 'find':
            jsonobject = competitionsEngine.getCompetition(id)
        if id is not None and action == 'findall':
            jsonobject = competitionsEngine.get_all_competition_ids()

    elif edittype == 'gym':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            competitionsEngine.update_gym(jsonobject['id'], jsonobject)

        if id is not None and action == 'find':
            jsonobject = competitionsEngine.get_gym(id)
        if id is not None and action == 'findall':
            jsonobject = competitionsEngine.get_gyms()

    elif edittype == 'routes':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            # None is gymid but this is ok as the routes id will be found
            competitionsEngine.upsert_routes(id, None, jsonobject)


        if id is not None and action == 'find':
            jsonobject = competitionsEngine.get_routes(id)

        if id is not None and action == 'findall':
            jsonobject = competitionsEngine.get_all_routes_ids()

    else:
        jsonobject = {"error": "choose edit type" }

    return render_template('competitionRawAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@skala_api_app.post('/auth/login')
def api_email_login():
    """Email/password login returning JSON.
    Body form or JSON: {"email":"...","password":"..."}
    """
    data = request.get_json(silent=True) or request.form
    email = data.get('email') if data else None
    password = data.get('password') if data else None
    # Ensure bcrypt available
    if email_login_service_api.bcrypt is None:
        from flask_bcrypt import Bcrypt
        email_login_service_api.bcrypt = Bcrypt()
    result = email_login_service_api.login_with_password(email, password, apply_session=True)
    if result.get('success'):
        user = result.get('user') or {}
        user_obj = competitionsEngine.get_user_by_email(user.get('email')) if user else None
        token = create_jwt(user.get('email'), user_obj.get('id') if user_obj else None)
        result['token'] = token
    status = 200 if result.get('success') else 401
    return jsonify(result), status


@skala_api_app.post('/auth/google/login')
def api_google_login():
    """Exchange Google ID token for local JWT.
    Input JSON: {"id_token": "<google id token>"}
    """
    if not GOOGLE_AUTH_AVAILABLE:
        return jsonify({'success': False, 'error': 'google_auth_not_available'}), 501
    data = request.get_json(silent=True) or {}
    id_token_str = data.get('id_token')
    if not id_token_str:
        return jsonify({'success': False, 'error': 'missing_id_token'}), 400
    client_id = os.getenv('GOOGLE_WEB_CLIENT_ID') or os.getenv('GOOGLE_CLIENT_ID')
    try:
        info = google_id_token.verify_oauth2_token(id_token_str, google_requests.Request(), client_id)
        if info.get('iss') not in ('accounts.google.com', 'https://accounts.google.com'):
            return jsonify({'success': False, 'error': 'invalid_issuer'}), 401
        if not info.get('email'):
            return jsonify({'success': False, 'error': 'no_email'}), 400
        if info.get('email_verified') is False:
            return jsonify({'success': False, 'error': 'email_not_verified'}), 401
    except Exception as e:
        logging.warning(f"Google token verification failed: {e}")
        return jsonify({'success': False, 'error': 'invalid_token'}), 401

    email = info['email'].lower()
    sub = info.get('sub')
    firstname = info.get('given_name')
    lastname = info.get('family_name')
    picture = info.get('picture')

    user = competitionsEngine.get_user_by_email(email)
    created = False
    if not user:
        # Minimal user record; adapt fields based on competitionsEngine expectations
        user = {
            'email': email,
            'firstname': firstname,
            'lastname': lastname,
            'is_confirmed': True,
            'auth_provider': 'google',
            'google_sub': sub,
            'gpictureurl': picture,
            'permissions': {'general': []}
        }
        try:
            competitionsEngine.upsert_user(user)
            created = True
        except Exception as e:
            logging.error(f"Failed to create google user {email}: {e}")
            return jsonify({'success': False, 'error': 'user_creation_failed'}), 500
    else:
        # Update picture / names if changed
        updated = False
        if picture and picture != user.get('gpictureurl'):
            user['gpictureurl'] = picture; updated = True
        if firstname and firstname != user.get('firstname'):
            user['firstname'] = firstname; updated = True
        if lastname and lastname != user.get('lastname'):
            user['lastname'] = lastname; updated = True
        if not user.get('is_confirmed'):
            user['is_confirmed'] = True; updated = True
        if updated:
            try:
                competitionsEngine.upsert_user(user)
            except Exception as e:
                logging.warning(f"Failed to update google user {email}: {e}")

    # Issue JWT
    db_user = competitionsEngine.get_user_by_email(email) or user
    token = create_jwt(email, db_user.get('id'))
    return jsonify({
        'success': True,
        'token': token,
        'created': created,
        'user': {
            'email': db_user.get('email'),
            'firstname': db_user.get('firstname'),
            'lastname': db_user.get('lastname'),
            'picture': db_user.get('gpictureurl') or db_user.get('fpictureurl') or picture
        }
    })

@skala_api_app.post('/auth/logout')
def api_logout():
    """Clear server-side session (logout). Always returns success."""
    try:
        # Remove typical auth keys but fall back to full clear.
        for k in list(session.keys()):
            session.pop(k, None)
        session.clear()
    except Exception:
        pass
    return jsonify({'success': True})


# ---------------- Additional Email Auth API Endpoints -----------------

def _extract_json_or_form():
    return request.get_json(silent=True) or request.form or {}


@skala_api_app.post('/auth/register')
def api_email_register():
    """Initiate registration (or resend confirmation / password reset) via email.
    Input JSON/Form: {"email": "user@example.com"}
    Always returns 200 to avoid user enumeration besides obvious validation errors.
    """
    data = _extract_json_or_form()
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({
            'success': False,
            'error_key': 'invalid_email',
            'error': 'Invalid email'
        }), 400
    # Reuse service.register logic by crafting a form-like object
    service_result = email_login_service_api.register({'email': email})
    ctx = service_result.get('context', {})
    message = ctx.get('error')  # service uses 'error' key for human message
    # Heuristics for success (email dispatched)
    dispatched_messages = {
        'Please_check_your_email_for_confirmation_link',
        'Link_to_reset_password_sent_to_email'
    }
    success = False
    if message:
        # Compare against translation keys if available
        for key in dispatched_messages:
            if key in message:
                success = True
                break
    return jsonify({
        'success': success,
        'stage': 'register',
        'email': email,
        'message': message,
    }), 200 if success else 400


@skala_api_app.post('/auth/password/reset/request')
def api_request_password_reset():
    """Request password reset link (works even if user unconfirmed - resends confirm)."""
    data = _extract_json_or_form()
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'success': False, 'error_key': 'invalid_email', 'error': 'Invalid email'}), 400
    user = competitionsEngine.get_user_by_email(email)
    # Always respond success (prevent enumeration) but trigger appropriate email
    if user is None:
        pass  # pretend to send
    elif user.get('is_confirmed') is False:
        # resend confirmation
        email_login_service_api._send_registration_email(email)
    else:
        # confirmed -> send reset password email
        token = email_login_service_api._generate_token(email)
        confirm_url = url_for('confirm_email', type='reset_password', token=token, _external=True)
        email_login_service_api.email_sender.send_password_reset_email(email, confirm_url)
    return jsonify({
        'success': True,
        'stage': 'password_reset_request',
        'message': 'If the email exists a message has been sent.'
    })


@skala_api_app.get('/auth/confirm/<type>/<token>')
def api_confirm_email(type, token):
    """Confirm registration or reset password token. Returns JSON indicating next step."""
    service_result = email_login_service_api.confirm_email(type, token)
    ctx = service_result.get('context', {})
    template = service_result.get('template')
    if template == 'change_password.html':
        # Session now holds email granting ability to set password
        email = session.get('email')
        return jsonify({
            'success': True,
            'stage': 'confirm',
            'require_password_change': True,
            'email': email,
            'message': 'Token valid. Please set password.'
        })
    error_msg = ctx.get('error') or 'Invalid or expired token'
    return jsonify({
        'success': False,
        'stage': 'confirm',
        'error': error_msg
    }), 400


@skala_api_app.post('/auth/password/change')
def api_change_password():
    """Change password after confirmation (requires session email set by confirm)."""
    data = _extract_json_or_form()
    password = data.get('password')
    password2 = data.get('password2') or data.get('password_confirm')
    # Ensure bcrypt available
    if email_login_service_api.bcrypt is None:
        from flask_bcrypt import Bcrypt
        email_login_service_api.bcrypt = Bcrypt()
    service_result = email_login_service_api.change_password(password, password2)
    template = service_result.get('template')
    ctx = service_result.get('context', {})
    if template == 'competitionLogin.html':
        return jsonify({
            'success': True,
            'stage': 'change_password',
            'message': ctx.get('error'),  # service uses error slot for info message
        })
    return jsonify({
        'success': False,
        'stage': 'change_password',
        'error': ctx.get('error') or 'Unable to change password'
    }), 400


@skala_api_app.get('/auth/status')
def api_auth_status():
    """Return authentication status (session or JWT)."""
    # Check JWT first
    auth_header = request.headers.get('Authorization', '')
    status_source = None
    user_email = None
    if auth_header.startswith('Bearer '):
        decoded = decode_jwt(auth_header[7:])
        if 'error' not in decoded:
            user_email = decoded.get('sub')
            status_source = 'jwt'
    # Fallback to session
    if not user_email and session.get('email'):
        user_email = session.get('email')
        status_source = 'session'
    if not user_email:
        return jsonify({'authenticated': False}), 200
    user = competitionsEngine.get_user_by_email(user_email) or {}
    return jsonify({
        'authenticated': True,
        'source': status_source,
        'user': {
            'email': user.get('email'),
            'firstname': user.get('firstname'),
            'lastname': user.get('lastname'),
            'club': user.get('club'),
            'godmode': bool(user.get('permissions', {}).get('godmode') or user.get('godmode'))
        }
    })



#---------------- Activities API -----------------
# returns all activities for all users

@skala_api_app.get('/activities')
def get_activities():
   
    allActivities = activities_db.get_activities_all_anonymous()

    activities = {}
    activities['activities'] = allActivities

    avg_stats = []
    user_stats = []
    all_activities_stats = calculate_activities_stats(allActivities)


    # Create a dictionary for all_activities_stats for quick lookups
    all_activities_dict = {date: count for date, count in zip(all_activities_stats['dates'], all_activities_stats['routes_done'])}

    activities['stats'] = {}
    activities['stats']['routes_done'] = user_stats
    activities['stats']['routes_avg'] = avg_stats
    return activities



@skala_api_app.get('/myactivities')
@session_or_jwt_required
def get_useractivities():
    user = competitionsEngine.get_user_by_email(session['email'])
    activitiesA = activities_db.get_activities(user.get('id'))

    allActivities = activities_db.get_activities_all_anonymous()

    activities = {}
    activities['activities'] = activitiesA

    avg_stats = []
    user_stats = []
    user_activities_stats = calculate_activities_stats(activitiesA)
    all_activities_stats = calculate_activities_stats(allActivities)

    combined_dates = sorted(set(user_activities_stats['dates'] + all_activities_stats['dates']), reverse=False)

    # Limit the combined_dates list to only the last 26 items
    combined_dates = combined_dates[-25:]

    # Create a dictionary for all_activities_stats for quick lookups
    all_activities_dict = {date: count for date, count in zip(all_activities_stats['dates'], all_activities_stats['routes_done'])}

    # Loop through user_activities_stats and check if the date exists in all_activities_stats
    for date in combined_dates:
        if date in all_activities_dict:
            avg_stats.append(all_activities_dict[date])
        else:
            avg_stats.append(0)
        if date in user_activities_stats['dates']:
            user_stats.append(user_activities_stats['routes_done'][user_activities_stats['dates'].index(date)])
        else:
            user_stats.append(0)

    activities['stats'] = {}
    activities['stats']['dates'] = combined_dates
    activities['stats']['routes_done'] = user_stats
    activities['stats']['routes_avg'] = avg_stats
    return activities


#calculates number of routes done per day
def calculate_activities_stats_per_day(activities):
    # Get today's date
    today = datetime.today().date()
    stats  = {}
    # Create a dictionary with dates 30 days back from today as keys and 0 as initial values
    routes_done = {(today - timedelta(days=i)).strftime('%Y-%m-%d'): 0 for i in range(160, -1, -1)}

    for activity in activities:
        if activity.get('date') is None:
            continue
        # Parse the 'date' into a date object
        activity_date = activity['date']
        # If the activity date is in the routes_done dictionary, add the number of routes
        if activity_date in routes_done:    
            routes_done[activity_date] += len(activity['attempts'])

    # Convert the dictionary to a list of values
    routes_done_list = list(routes_done.values())

    stats['dates'] = list(routes_done.keys())
    stats['routes_done'] = routes_done_list

    return stats

# calculates number of activities per day
def calculate_activities_stats(activities):
    # Initialize a dictionary to store the count of routes done per week
    weekly_stats = defaultdict(int)

    for activity in activities:
        # Parse the date of the activity
        activity_date = datetime.strptime(activity['date'], '%Y-%m-%d')
        
        # Find the Monday of the week for the activity date
        start_of_week = activity_date - timedelta(days=activity_date.weekday())
        
        if activity.get('attempts') is None:
            logging.warning('activity has no attempts '+str(activity))
        # Increment the count of routes done for that week
        weekly_stats[start_of_week] += len(activity.get('attempts', []))

    # Convert the weekly_stats dictionary to a sorted list of tuples
    sorted_weekly_stats = sorted(weekly_stats.items())

    # Initialize the result dictionary with dates and routes_done lists
    result = {'dates': [], 'routes_done': []}

    # Populate the result dictionary
    for week_start, count in sorted_weekly_stats:
        result['dates'].append(week_start.strftime('%Y-%m-%d'))
        result['routes_done'].append(count)

    return result


@skala_api_app.get('/activities/all')
def get_activities_all():
    activities = activities_db.get_activities_all_anonymous()
    #return json.dumps(activities)
    return activities


@skala_api_app.post('/activity')
@session_or_jwt_required
def journey_add():
    user = competitionsEngine.get_user_by_email(session['email'])

    data = request.get_json()
    #data = request.get_data()
    # get the data from the body of the request

    date = data.get('date')
    gym_id = data.get('gym_id')
    name = data.get('activity_name')
    comp = {}
    gym = competitionsEngine.get_gym(gym_id)
    routesid = gym.get('routesid')


    #a = Activity1(**data)

    activity_id = activities_db.add_activity(user, gym, routesid, name, date)
    activity = activities_db.get_activity(activity_id)
    # journey_id = user.get('journey_id')
    
    #journeys = activities_db.get_activities(user.get('id'))
    return activity.to_dict()




@skala_api_app.delete('/activity/<activity_id>')
@session_or_jwt_required
def delete_activity(activity_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    activity = activities_db.get_activity(activity_id)
    if (activity is None):
        return {"error":"activity not found"}   
    #a = Activity1(**data)

    activities_db.delete_activity(activity_id)
    # journey_id = user.get('journey_id')

    #journeys = activities_db.get_activities(user.get('id'))
    return {}





@skala_api_app.get('/activity/<activity_id>')
@session_or_jwt_required
def get_activity(activity_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    activity = activities_db.get_activity(activity_id)
    if (activity is None):
        return {"error":"activity not found"}   
    #a = Activity1(**data)
    #activity = activities_db.get_activity(activity_id)
    #activity = calculate_activity_stats(activity)

    # journey_id = user.get('journey_id')
    #journeys = activities_db.get_activities(user.get('id'))
    return activity.to_dict()
    #return json.dumps(activity)
    


# add an attempt to an activity
@skala_api_app.post('/activity/<activity_id>')
@session_or_jwt_required
def add_activity_route_attempt(activity_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    data = request.get_json()
    #data = request.get_data()
    # get the data from the body of the request

    gym_id = data.get('gym_id')
    routes_id = data.get('routes_id')
    routes = competitionsEngine.get_routes(routes_id)

    route_id = data.get('route_id')
    note = data.get('note')
    route_finish_status = data.get('route_finish_status')
    grade = data.get('grade')
    user_grade = data.get('route-grade-user')
    route_stars = data.get('route_stars')
    route = competitionsEngine.get_route(routes_id, route_id)
    
    activity = activities_db.add_activity_attempt(activity_id, route, route_finish_status, note, user_grade, (route_stars or 0))

    # journey_id = user.get('journey_id')
    #journeys = activities_db.get_activities(user.get('id'))
    return activity




@skala_api_app.get('/activity/user/<user_id>')
@session_or_jwt_required
def get_activities_by_user(user_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    # Fetch activities for provided user_id (authorization: allow only self unless admin)
    if str(user.get('id')) != str(user_id):
        # basic permission check: only allow self for now
        return jsonify({'error': 'forbidden'}), 403
    activities = activities_db.get_activities(user.get('id'))
    if activities is None:
        activities = []
    return json.dumps(activities)



@skala_api_app.get('/activity/gym/<gym_id>/routes/<routes_id>')
def get_activities_by_gym_by_routes(gym_id, routes_id):
   
    activities = activities_db.get_activities_by_gym_routes(gym_id, routes_id)
    if (activities is None or len(activities) == 0):
        return {"error":"activity not found"}   
    #a = Activity1(**data)

    # journey_id = user.get('journey_id')
    # calculate_activity_stats(activity)
    #journeys = activities_db.get_activities(user.get('id'))
    return json.dumps(activities)




@skala_api_app.delete('/activity/<activity_id>/route/<route_id>')
@session_or_jwt_required
def delete_activity_route(activity_id, route_id):
    #user = competitionsEngine.get_user_by_email(session['email'])


    activity = activities_db.get_activity(activity_id)
    if (activity is None):
        return {"error":"activity not found"}   
    #a = Activity1(**data)

    activity = activities_db.delete_activity_route(activity_id, route_id)
    # journey_id = user.get('journey_id')
    
    #journeys = activities_db.get_activities(user.get('id'))
    return activity


# Update whole activity (currently supports updating name only)
@skala_api_app.put('/activity/<activity_id>')
@session_or_jwt_required
def update_activity_meta(activity_id):
    """Update Activity level fields (e.g., name).

    JSON body may include:
      - name: new activity name/title
    Returns updated Activity (lean representation if attempts present).
    """
    data = request.get_json(silent=True) or {}
    activity = activities_db.get_activity(activity_id)
    if activity is None:
        return jsonify({'error': 'activity_not_found'}), 404
    # Allow name change
    if 'name' in data:
        new_name = (data.get('name') or '').strip()
        if not new_name:
            return jsonify({'error': 'invalid_name'}), 400
        activity.name = new_name[:200]  # basic length guard
    # Persist (legacy flattened to preserve current storage format)
    activities_db.update_activity(activity)
    return jsonify(activity.to_dict())


# update a specific route attempt inside an activity using attempt_id (no creation on miss)
@skala_api_app.put('/activity/<activity_id>/attempt/<attempt_id>')
@session_or_jwt_required
def update_activity_route(activity_id, attempt_id):
    """Update a single existing RouteAttempt within an Activity by attempt_id.

    Path: /activity/{activity_id}/attempt/{attempt_id}

    JSON body fields accepted (all optional):
      - status: one of VALID_STATUSES or a recognized synonym
      - user_grade: user proposed grade (string)
      - note: free-form note (string)
      - attempt_time: ISO8601 timestamp (e.g. 2025-10-30T18:42:00Z)

    Behavior changes vs previous version:
      - Lookup is by RouteAttempt.attempt_id only (not route id)
      - Will NOT create a new attempt if not found (returns 404)
      - Still rehydrates legacy flattened 'routes' list into attempts once if needed
    Returns updated Activity (lean form: distinct routes + attempts arrays).
    """
    from src.RouteAttempt import VALID_STATUSES, STATUS_SYNONYMS, RouteAttempt  # local import to avoid circular

    data = request.get_json(silent=True) or {}

    activity = activities_db.get_activity(activity_id)
    if activity is None:
        return jsonify({'error': 'activity_not_found'}), 404

    # Attempt lookup by attempt_id
    attempt = next((a for a in activity.attempts if a.attempt_id == attempt_id), None)

    # Lazy rehydrate from legacy flattened list if attempts list empty and attempt not found
    if attempt is None and not activity.attempts and activity.routes:
        for rdict in activity.routes:
            try:
                activity.attempts.append(RouteAttempt.from_dict(rdict))
            except Exception:
                pass
        attempt = next((a for a in activity.attempts if a.attempt_id == attempt_id), None)

    if attempt is None:
        return jsonify({'error': 'route_attempt_not_found'}), 404

    # Apply field updates
    if 'status' in data and data.get('status') is not None:
        raw_status = (data.get('status') or '').strip().lower()
        norm = STATUS_SYNONYMS.get(raw_status, raw_status)
        if norm not in VALID_STATUSES:
            return jsonify({'error': 'invalid_status', 'allowed': list(VALID_STATUSES)}), 400
        attempt.status = norm

    if 'user_grade' in data:
        attempt.user_grade = data.get('user_grade') or None

    if 'note' in data:
        attempt.note = data.get('note') or ''

    # Allow updating star rating (0-3). 0 treated as no-comment but stored.
    if 'route_stars' in data:
        try:
            stars_val = int(data.get('route_stars') or 0)
        except Exception:
            stars_val = 0
        # clamp to 0..3
        if stars_val < 0:
            stars_val = 0
        if stars_val > 3:
            stars_val = 3
        try:
            # RouteAttempt has route_stars field; assign directly
            attempt.route_stars = stars_val
        except Exception:
            pass

    if 'attempt_time' in data and data.get('attempt_time'):
        try:
            iso = data.get('attempt_time').replace('Z', '')
            attempt.attempt_time = datetime.fromisoformat(iso)
        except Exception:
            return jsonify({'error': 'invalid_attempt_time_format'}), 400

    # Persist (legacy flattened to keep storage backward compatible)
    activities_db.update_activity(activity)

    return jsonify(activity.to_dict())


def calculate_activity_stats(activity):
    routes = activity.get('routes')
    routes_count = len(routes)
    grades_climbed = []
    for route in routes:
        route['grade_index'] = grades.index(route['grade'])
        #route['grade_points'] = np.exp(-((route['grade_index'] - mean) / std_dev) ** 2 / 2)
        if route['status'] == 'climbed' or route['status'] == 'flashed':
            grades_climbed.append(route['grade'])
    
    avg_grade_climbed = avg_grade(routes)
    activity['stats'] = {}
    activity['stats']['routes_count'] = routes_count
    activity['stats']['avg_grade_climbed'] = avg_grade_climbed

    return activity

    


def avg_grade(routes, flash_weight=2, climb_weight=1, attempt_weight=0.1):
    if not routes:
        return None

    # Convert grades to indices and apply weights
    weighted_indices = []
    for route in routes:
        grade = route['grade']
        status = route['status']
        if status == 'flashed':
            weight = flash_weight
        elif status == 'climbed':
            weight = climb_weight
        else:  # status is 'attempted' or anything else
            weight = attempt_weight
        weighted_indices.append(grades.index(grade) * weight)

    # Calculate average index
    average_index = sum(weighted_indices) / sum(flash_weight if route['status'] == 'flashed' else climb_weight if route['status'] == 'climbed' else attempt_weight for route in routes)

    # Round to nearest integer
    average_index = round(average_index)

    # Convert index back to grade
    average_grade = grades[average_index]

    return average_grade



@skala_api_app.route('/journey/<journey_id>/add', methods=['POST'])
@session_or_jwt_required
def journey_session_entry_add(journey_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    route_finish_status = request.form.get('route_finish_status')
    route_id = request.form.get('route')
    notes = request.form.get('notes')

    comp = {}

    journey = activities_db.get_journey_session(journey_id)

    journey = activities_db.add_journey_session_entry(journey_id,route_id, route_finish_status, notes)
    routes = competitionsEngine.get_routes(journey.get('routes_id'))


    return render_template('skala-journey-session.html',
                           user=user,
                           journey=journey,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@skala_api_app.route('/journey/<journey_id>/<route_id>/remove', methods=['GET'])
@session_or_jwt_required
def journey_session_remove(journey_id, route_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    journey = activities_db.get_journey_session(journey_id)

    testid = request.args.get('testid')
    if journey is None:
        return {}
    activities_db.remove_journey_session(journey_id, route_id)
    routes = competitionsEngine.get_routes(journey.get('routes_id'))

    return {}


# this is used by calendar so it has a specific format 
@skala_api_app.route('/competition/list')
def getCompetitionDashboard():
    comps = competitionsEngine.getCompetitions()
    compsreturnd = []
    language = session.get('language', 'fr')[:2]
    # for each competition remove object climbers
    for compid in comps:
        c={}
        c['title'] = comps[compid]['name'] 
        c['id'] = comps[compid]['id']
        #c['start'] = comps[compid]['date']+ "T11:00:00"
        #c['end'] = comps[compid]['date']+ "T15:59:59"
        c['date'] = comps[compid]['date']
        c['competition_type'] = comps[compid].get('competition_type')
        c['status'] = comps[compid]['status']
        c['url'] = '/competitionDetails/'+compid
        c['text'] = {}
        c['text']['status'] = competitionsEngine.reference_data['current_language'].get('competition_status_'+str(comps[compid]['status']))
        c['text']['competition_type'] = competitionsEngine.reference_data['current_language'].get('competition_type_'+str(comps[compid].get('competition_type','standard')))
        c['gym'] = comps[compid].get('gym')
        c['gym_id'] = comps[compid].get('gym_id')
        c['calc_type'] = comps[compid].get('calc_type','standard')
        #comps[compid]['climbers'] = None
        #comps[compid]['routes'] = None
        #c['extendedProps'] = deepcopy(c)
        
        compsreturnd.append(c)
    return compsreturnd


@skala_api_app.route('/competition/<competition_id>')
def get_competition_by_id(competition_id):
    competition = competitionsEngine.getCompetition(competition_id)
    
    if competition is None:
        return {}

    for climber in competition.get('climbers').values():
        climber.pop('email', None)


    if request.args.get('remove') == 'routesClimbed2':
        for climber in competition.get('climbers').values():
            climber.pop('routesClimbed2', None)

    if competition is None:
        return {"error": "competition not found"}
    return jsonify(competition)



@skala_api_app.route('/competition/year/<year>')
def competitions_by_year(year):

    username = session.get('username')
    #if username:
    #    return 'logged in '+str(username)
    #print(username)

    #username = request.args.get('username')
    name = request.args.get('name')
    date = request.args.get('date')
    gym = request.args.get('gym')
    comp = {}
    competitionId=None
    if not year.isdigit():
        year = datetime.now().year

    user = competitionsEngine.get_user_by_email(session.get('email'))
    subheader_message = request.accept_languages
    langs = competitionsEngine.reference_data['languages']
    competitions = competitionsEngine.getCompetitions()
    #test_list = [datetime(year, 1, 1), datetime(year, 12, 31)]
    date_strt, date_end = datetime(int(year), 1, 1), datetime(int(year), 12, 31)

    input_format = "%Y-%m-%d"
    competitions2 = {}
    for competition_id in competitions:
        competition = competitions.get(competition_id)
        competition_date = competition.get('date')
        try:
            parsered_date = datetime.strptime(competition_date, input_format)
            if parsered_date >= date_strt and parsered_date <= date_end:
                res = True
                competitions2[competition['id']] = competition

        except ValueError:
            print("This is the incorrect date string format.")

    return competitions2


@skala_api_app.route('/competition/create', methods=['POST'])
@session_or_jwt_required
def new_competition_post():
    username = session.get('username')

    routedata = request.get_json()
    routedata = json.loads(routedata)


    #username = request.args.get('username')
    name = request.form.get('name')
    date = request.form.get('date')
    #gym = request.form.get('gym')
    routesid = request.form.get('routes')
    comp = {}
    competitionId = None

    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is None or not competitionsEngine.can_create_competition(user):
        return "{ 'error'; 'Not authorized'}"

    if name is not None and date is not None and routesid is not None:
        # Basic defaults for API-based creation
        max_participants = request.form.get('max_participants') or 80
        competition_type = request.form.get('competition_type') or 0
        instructions = request.form.get('instructions') or ""
        calc_type = request.form.get('calc_type')

        competitionId = competitionsEngine.addCompetition(
            None,
            user.get('id') if user else None,
            name,
            date,
            routesid,
            max_participants,
            competition_type=competition_type,
            instructions=instructions,
            calc_type=calc_type
        )
        competitionsEngine.modify_user_permissions_to_competition(user, competitionId, "ADD")
        comp = competitionsEngine.getCompetition(competitionId)
        return comp
    return "{ 'error'; 'Not created. Something missing'}"


@skala_api_app.route('/competition/<competitionId>/register')
#@session_or_jwt_required
def addCompetitionClimber(competitionId):
    return None


# Statistics for a competition for apex charts
@skala_api_app.route('/competition/<competitionId>/stats')
#@session_or_jwt_required
def getCompetitionStats(competitionId):
    competition = None

    if competitionId is not None:
        competition = competitionsEngine.recalculate(competitionId)

    if competition is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No competition found",
                               **session)
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

    routesid = competition.get('routesid')
    routesDict = competitionsEngine.get_routes(routesid)
    routes = routesDict['routes'] if routesDict else []
    # Categories used for statistics (mirrors other endpoint logic)
    categories = ["F0","F1","F2","M0","M1","M2"]
#				reference_data['current_language'].ranking_titan_women,
#				reference_data['current_language'].ranking_senior_women,
#				reference_data['current_language'].ranking_diament_men,
#				reference_data['current_language'].ranking_titan_men,
#				reference_data['current_language'].ranking_senior_men]
	
    statistics = {}
    for category in categories:
        repeatArray = [0]*len(routes) 
        statistics[str(category)]=repeatArray

    for climber in competition['climbers'].values():

        key = str(climber.get('sex'))+str(climber.get('category'))
        stats = statistics.get(key)
        for routenum in climber.get('routesClimbed'):
            if climber.get('sex') == 'M':
                stats[routenum-1]=stats[routenum-1]+1
            else:
                stats[routenum-1]=stats[routenum-1]+1  # can make -1 to have a stacked chart with males and females

    statout = []
    for category in categories:     
        statout.append( {  #"name":category,
                           "data": statistics.get(category)})

    statresponse = { "chartdata": statout,
                    "routedata" : routes}
    
    return json.dumps(statresponse)


# Statistics for a competition for apex charts
@skala_api_app.route('/competition/<competitionId>/fullresults')
#@session_or_jwt_required
def getCompetitionFlatFullTable(competitionId):
    competition = None

    if competitionId is not None:
        competition = competitionsEngine.recalculate(competitionId)

    if competition is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No competition found",
                               **session)
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

    routesid = competition.get('routesid')
    
    routes = []
    if (competition.get('routes') is None) or (len(competition.get('routes')) == 0):
        routes = competition.get('routes')
    else:
        routesDict = competitionsEngine.get_routes(routesid)
        routes = routesDict['routes']

    #rankings = competitionsEngine.get_sorted_rankings(competition)
    # we need 6 categories:
    categories = ["F0","F1","F2","M0","M1","M2"]
    #category_names =  [reference_data['current_language'].ranking_diament_women,
#				reference_data['current_language'].ranking_titan_women,
#				reference_data['current_language'].ranking_senior_women,
#				reference_data['current_language'].ranking_diament_men,
#				reference_data['current_language'].ranking_titan_men,
#				reference_data['current_language'].ranking_senior_men]


    statistics = {}
    for category in categories:
        repeatArray = [0]*len(routes) 
        statistics[str(category)]=repeatArray
                
    statout = []
    for category in categories:     
        statout.append( {  #"name":category,
                           "data": statistics.get(category)})

    full_routes_table = []
    table_entry = {}
    for route in competition.get('routes'):
        for climber in competition['climbers'].values():
            if int(route.get('routenum')) in climber.get('routesClimbed'):
                if len(climber.get('routesClimbed2')) != len(climber.get('routesClimbed')) :
                    logging.error("getCompetitionFlatFullTable climber routesClimbed2 length mismatch "+climber.get('id'))

                table_entry = {}
                index = climber.get('routesClimbed').index(int(route.get('routenum')))
                try:
                    if climber.get('routesClimbed2') and route.get('id') != climber.get('routesClimbed2')[index].get('id'):  # there is a potential bug here on routeseClimbed2 not there
                        logging.error("getCompetitionFlatFullTable route id is not matching or climber doesn't have a routeClimbed"+climber.get('id'))
                except Exception as e:
                    logging.error("getCompetitionFlatFullTable error checking routeClimbed2 "+str(e)+ " climber id "+str(climber.get('id')))
                    
                points = climber.get('points_earned')[index]

                table_entry.update(route)
                table_entry['points'] = round(points,2)
                table_entry['category'] = climber.get('category')
                table_entry['firstname'] = climber.get('firstname')
                table_entry['lastname'] = climber.get('lastname')
                table_entry['club'] = climber.get('club')
                table_entry['rank'] = climber.get('rank')
                table_entry['sex'] = climber.get('sex')

                
                #full_routes_table.append(route)
                full_routes_table.append(table_entry)
    

    statresponse = { "chartdata": statout,
                    "routedata" : routes}
    
    return json.dumps(full_routes_table)
    #return full_routes_table




# Statistics for a competition for apex charts
@skala_api_app.route('/competition/<competitionId>/climber/<climberId>/present/<present>', methods=['POST'])
@session_or_jwt_required
def setClimberAsPresent(competitionId,climberId,present):
    user = competitionsEngine.get_user_by_email(session['email'])
    competition = competitionsEngine.getCompetition(competitionId)

    if not competitionsEngine.can_update_routes(user,None):
        return {"error": "not authorized"}

    if climberId is not None:
        climber = competitionsEngine.getClimber(competitionId,climberId)

    if climber is None:
        return {"error": "climber not found"}

    competition = competitionsEngine.getCompetition(competitionId)
    if competition is None:
        return {"error": "competition not found"}

    # parse the present variable to resolve to boolean
    if present.lower() == 'true' or present == '1':
        present = True
    else:
        present = False
    competitionsEngine.setClimberPresence(competitionId, climberId, present)
    return {"success": True}



### USER
@skala_api_app.route('/user')
@session_or_jwt_required
def get_user():
    """Return basic user profile (requires JWT or session)."""
    email = session.get('email')
    if not email:
        return jsonify({'error': 'unauthorized'}), 401
    user = competitionsEngine.get_user_by_email(email)
    if not user:
        return jsonify({'error': 'not_found'}), 404
    picture = user.get('gpictureurl') or user.get('fpictureurl') or user.get('picture')
    user['picture'] = picture
    if competitionsEngine.can_create_gym(user):
        user['permissions']['general'].append("create_gym")
    return user


@skala_api_app.route('/user/email')  
@admin_required
def get_users():
    if session is None or session.get('email') is None:
        return {}
    
    user = competitionsEngine.get_user_by_email(session['email'])
    
    if user is None:
        return {}

    if competitionsEngine.can_edit_users(user):
        users = skala_db.get_all_user_emails()
        return json.dumps(users)
    
    return json.dumps(user)


@skala_api_app.route('/user/email/<email>')
@admin_required
def get_user_by_email(email):
    climber = competitionsEngine.get_user_by_email(email)

    if climber is None:
        #return "{'error_code':'No such user'}", 400
        return {}
    return climber



@skala_api_app.route('/gym/<gym_id>/users')
def get_users_by_gym(gym_id):
    users=  skala_db.get_users_by_gym_id(gym_id)
    # remove email and permissions from the response
    for user in users:
        user.pop('email', None)
        #user.pop('permissions', None)
        user.pop('isgod',None)
        
        if user.get('fpictureurl') is not None:
            user['pictureurl'] = user.get('fpictureurl')
        if user.get('gpictureurl') is not None:
            user['pictureurl'] = user.get('gpictureurl')
        if user.get('fpictureurl') is None and user.get('gpictureurl') is None:
            #user['pictureurl'] = '/public/images/sentiment_satisfied_FILL0_wght600_GRAD200_opsz48.png'
            user['pictureurl'] = '/public/images/favicon.png'
        if user.get('firstname') is None:
            user['firstname'] = user.get('name') 
    return users



@skala_api_app.route('/users/search/')
def get_all_users():
    search_string = request.args.get('q')
    if search_string is None or len(search_string) < 2 or not search_string.isalnum():
        return []

    users=  skala_db.search_all_users(search_string=search_string)
    # remove email and permissions from the response
    for user in users:
        user.pop('email', None)
        #user.pop('permissions', None)
        user.pop('isgod',None)
        
        if user.get('fpictureurl') is not None:
            user['pictureurl'] = user.get('fpictureurl')
        if user.get('gpictureurl') is not None:
            user['pictureurl'] = user.get('gpictureurl')
        if user.get('fpictureurl') is None and user.get('gpictureurl') is None:
            #user['pictureurl'] = '/public/images/sentiment_satisfied_FILL0_wght600_GRAD200_opsz48.png'
            user['pictureurl'] = '/public/images/favicon.png'
        if user.get('firstname') is None:
            user['firstname'] = user.get('name') 
    #json.dumps(users)
    return json.dumps(users)



@skala_api_app.route('/updateuser')
def update_user():
    if session.get('email') is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No competition found",
                               **session)

    climber = competitionsEngine.get_user_by_email(session.get('email'))

    firstname = request.args.get('firstname')
    lastname = request.args.get('lastname')
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    subheader_message = request.args.get('update_details')

    email = session.get('email')
    name = session.get('name')

    if firstname is None or sex is None or club is None or email is None:
        #subheader_message = "Update"

        return render_template('climber.html',
                               error_message = request.args.get('all_fields_required'),
                               subheader_message=subheader_message,
                               competitionId=None,
                               climber=climber,
                               reference_data=competitionsEngine.reference_data,
                               logged_email=email,
                               logged_name=name,
                               **session)

    else:
        climber = competitionsEngine.user_self_update(climber, name, firstname, lastname, nick, sex, club, category)
        subheader_message = request.args.get('details_saved')

    if name is None:
        name = ""

    return render_template('climber.html',
                           subheader_message=subheader_message,
                           competitionId=None,
                           climber=climber,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=name,
                            **session)




## RESULTS

@skala_api_app.route('/competition_results/<competitionId>')
#@session_or_jwt_required
def get_competition_results(competitionId):
    competition = None

    if competitionId is not None:
        competition = competitionsEngine.recalculate(competitionId)

    if competition is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message=request.args.get('no_competition_found'),
                               **session)
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
    rankings = competitionsEngine.get_sorted_rankings(competition)

    return rankings


@skala_api_app.route('/competition/<competitionId>/climber/<climberId>', methods=['GET'])
def getCompetitionClimber(competitionId, climberId):
    climber = None
    
    if climberId is not None:
        climber = competitionsEngine.getClimber(competitionId,climberId)


    if climber is None:
        return {"error": "climber not found"}
    elif climber is LookupError:
        return {"error": "climber not found"}
    elif len(climber) == 0:
        return {"error": "climber not found"}


    competition = competitionsEngine.getCompetition(competitionId)
    if competition is None:
        return {"error": "competition not found"}
    
    return climber



@skala_api_app.route('/competition/<competitionId>/climber/<climberId>', methods=['POST'])
def update_climber(competitionId, climberId):
    climber = competitionsEngine.getClimber(competitionId, climberId)
    if climber is None:
        return {"error": "climber not found"}
    elif climber is LookupError:
        return {"error": "climber not found"}
    elif len(climber) == 0:
        return {"error": "climber not found"}

    competition = competitionsEngine.getCompetition(competitionId)
    if competition is None:
        return {"error": "competition not found"}


    data = request.get_json()


    return climber


@skala_api_app.route('/competition_results/<competitionId>/csv')
def get_competition_results_csv(competitionId):
    competition = competitionsEngine.getCompetition(competitionId)
    out = {}
    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(competition['climbers'])

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

    data_file = open('jsonoutput.csv', 'w', newline='')
    csv_writer = csv.writer(data_file)

    count = 0
    for climberid in competition['climbers']:
        data = competition['climbers'][climberid]
        for i in range(100):
            if (i in competition['climbers'][climberid]['routesClimbed']):
                data['r' + str(i)] = 1
            else:
                data['r' + str(i)] = 0

        if count == 0:
            header = data.keys()
            csv_writer.writerow(header)
            writer.writerow(header)
            count += 1
        out = {}
        routesClimbed = flatten(data['routesClimbed'])

        csv_writer.writerow(data.values())
        writer.writerow(data.values())

    data_file.close()

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                     "attachment; filename=competitionresults.csv"})




# enter competition climbed routes for a climber and save them
@skala_api_app.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['GET'])
@login_required
def routes_climbed(competitionId, climberId):

    if climberId is not None:
        climber = competitionsEngine.getClimber(competitionId,climberId)

    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message=request.args.get('no_climber_found'),
                               **session)
    elif climber is LookupError:
        return render_template('competitionDashboard.html', sortedA=None,
                                   getPlaylistError="error  ",
                                   library={},
                                   **session)
    elif len(climber) == 0:
        return render_template('competitionDashboard.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)

    user = competitionsEngine.get_user_by_email(session['email'])
    competition = competitionsEngine.getCompetition(competitionId)

    if not competitionsEngine.can_update_routes(user,competition):
        return redirect(url_for('skala_api_app.competitionRoutesList', competitionId=competitionId))


    routesid = competition.get('routesid')
    routes = competitionsEngine.get_routes(routesid)
    #routes = routes['routes']
    subheader_message = climber['name']+" - "+climber['club']

    return render_template("competitionRoutesEntry.html", climberId=climberId,
                           climber=climber,
                           routes=routes,
                           subheader_message=subheader_message,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)


@skala_api_app.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['POST'])
@login_required
def update_routes_climbed(competitionId, climberId):
    # generate array of marked routes from HTTP request
    routesUpdated = []
    for i in range(100):
        routeChecked = request.form.get("route"+str(i)) != None
        if routeChecked:
            routesUpdated.append(i)

    competition = None

    if climberId is not None:
        user = competitionsEngine.get_user_by_email(session['email'])
        if not competitionsEngine.has_permission_for_competition(competitionId, user):
            return render_template('competitionLogin.html')

        if len(routesUpdated) > 0:
            competitionsEngine.setRoutesClimbed(competitionId, climberId, routesUpdated)
            competition = competitionsEngine.getCompetition(competitionId)
            return render_template('competitionClimberList.html',
                                   competition=competition,
                                   competitionId=competitionId,
                                   subheader_message=request.args.get('routes_saved'),
                                    reference_data=competitionsEngine.reference_data,
                                   **session)

        climber = competitionsEngine.getClimber(competitionId,climberId)

    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message=request.args.get('no_climber_found'),
                               **session)
    elif climber is LookupError:
        return render_template('competitionDashboard.html', sortedA=None,
                                   getPlaylistError="error  ",
                                   library={},
                                   **session)
    elif len(climber) == 0:
        return render_template('competitionDashboard.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)

    competition = competitionsEngine.getCompetition(competitionId)

    routesid = competition.get('routesid')
    routes = competitionsEngine.get_routes(routesid)
    routes = routes['routes']
    subheader_message = climber['name']+" - "+climber['club']

    return render_template("competitionRoutesEntry.html", climberId=climberId, climber=climber,
                           routes=routes,
                           subheader_message=subheader_message,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)



@skala_api_app.route('/migrategyms')
def migrategyms():
    gyms = competitionsEngine.get_gyms()

    nanterre = gyms["1"]
    nanterre['logoimg'] = 'logo-ESN-HD-copy-1030x1030.png'
    nanterre['homepage'] = 'https://www.esnanterre.com/'

    competitionsEngine.update_gym("1", "667", json.dumps(nanterre))
    return {}




@skala_api_app.route('/competition_results/<competitionId>/stats_points_per_difficulty')
def get_competition_stats(competitionId):
    comp = competitionsEngine.get_competition(competitionId)
    routes = competitionsEngine.get_routes(comp['routesid'])

    if comp is None:
        return {}
    
    results = {}

    pointsPerRouteM = competitionsEngine.get_route_repeats("M", comp)
    pointsPerRouteF = competitionsEngine.get_route_repeats("F", comp)

    for index, route in enumerate(routes['routes']):
        route['pointsM'] = pointsPerRouteM[index+1]
        route['pointsF'] = pointsPerRouteF[index+1]

    #grades = ["4a", "4b", "4","4c", "5a", "5b", "5c", "6a", "6a+", "6b", "6b+", "6c", "7a"] # list of french climbing grades
    #grades = ["5b", "5c", "6a"] # list of french climbing grades
    
    routes['rangeData'] = transform_json(routes)
    routes['rangeDataOld']  =transform_jsonold(routes)

    #routes['grades']
    return routes



@skala_api_app.route('/competition_results/<competitionId>/stats_repeats_per_route')
def stats_repeats_per_route(competitionId):
    comp = competitionsEngine.get_competition(competitionId)
    
    if comp is None:
        return {}
    
    routes_dict = competitionsEngine.get_routes(comp['routesid'])
    if not routes_dict or 'routes' not in routes_dict:
        return {}
    
    routes = routes_dict['routes']
    categories = ["M0", "M1", "M2", "F0", "F1", "F2"]
    
    # Initialize repeat counts and climber names for each category and route
    repeats = {cat: [0 for _ in routes] for cat in categories}
    climber_names = {cat: [[] for _ in routes] for cat in categories}
    
    # Build route index lookup
    route_id_to_index = {route.get('id'): idx for idx, route in enumerate(routes)}
    
    # Count repeats per route per category and collect climber names
    for climber in comp.get('climbers', {}).values():
        sex = climber.get('sex')
        category = climber.get('category')
        cat_key = f"{sex}{category}"
        
        if cat_key not in repeats:
            continue
        
        # Get climber name (firstname + lastname)
        firstname = climber.get('firstname', '')
        lastname = climber.get('lastname', '')
        climber_name = f"{firstname} {lastname}".strip() or climber.get('name', 'Unknown')
        
        # Check routesClimbed2 for detailed route info
        for route in climber.get('routesClimbed2', []):
            route_id = route.get('id')
            if route_id in route_id_to_index:
                idx = route_id_to_index[route_id]
                repeats[cat_key][idx] += 1
                climber_names[cat_key][idx].append(climber_name)
    
    # Prepare series data for ApexCharts
    series = []
    for cat in categories:
        series.append({
            "name": cat,
            "data": repeats[cat]
        })
    
    # Y-axis labels: route number | line | grade
    y_labels = []
    for route in routes:
        routenum = route.get('routenum', '?')
        line = route.get('line', '?')
        grade = route.get('grade', '?')
        y_labels.append(f"{routenum} - {grade}")
    
    return {
        "chartdata": series,
        "routedata": routes,
        "y_labels": y_labels,
        "climber_names": climber_names
    }



@skala_api_app.route('/climber/stats')
@session_or_jwt_required
def get_myskala():
    username = session.get('email')
    stats = {}
    competitions = skala_db.get_all_competitions()
    competition_routes_total = 0
    
    for competition in competitions.values():
        #competition = skala_db.get_competition(id)
        routesid = competition.get('routesid')
        routes = competitionsEngine.get_routes(routesid)
        if routes is None:
            continue
        routes = routes.get('routes')
    
        competition_routes_total += len(routes)
        
    competition_ids = skala_db.get_competitions_for_email(username)

    user = competitionsEngine.get_user_by_email(session['email'])
    
    all_competitions = []
    stats['personalstats']={}
    stats['personalstats']['all_grades'] = []
    routes_climbed_count = 0
    
    for id in competition_ids:
        ##competition = skala_db.get_competition(id)
        #pointsEarned = competitionsEngine._calculatePointsPerClimber(id, user['id'], competition)
        competition = competitionsEngine.recalculate(id)
        routesid = competition.get('routesid')
        routes = competitionsEngine.get_routes(routesid)
        if routes is None:
            continue
        routes = routes.get('routes')
        #all_competitions.append(competition)

        climber = competition.get('climbers').get(user['id'])
        competition['climber'] = climber
        routes_climbed2 = {}
        if climber is not None:
            
            routes_climbed2=climber['routesClimbed2']
            routes_climbed_count += len(climber['routesClimbed2'] )
            #grades_climbed = []
            for idx, route in enumerate(routes_climbed2):
                route['competitionName'] = competition['name']
                route['competitionDate'] = competition['date']
                route['gym'] = competition['gym']
                grade = route.get('grade')
                points = round(climber['points_earned'][idx])
                stats['personalstats']['all_grades'].append(route.get('grade'))
                route['points'] = points
                route['rank']  = climber['rank']
                #grades_climbed.append(' '+str(grade) + ' ('+str(points)+')')
            #competition['grades_climbed'] = grades_climbed
            competition['points_earned'] = climber['points_earned']
            competition['routesClimbed2'] = routes_climbed2
            competition
        # clear unnecessary data for other
        competition.get('climbers').clear()
        all_competitions.extend(routes_climbed2)

        competition_points_per_route = {}
        
    stats['user'] = user

    stats['personalstats']['competitions_count'] = len(competition_ids)
    stats['personalstats']['total_competitions_count'] = len(competitions)
    
    stats['personalstats']['routes_climbed_count'] = routes_climbed_count
    stats['personalstats']['competition_routes_total'] = competition_routes_total

    stats['competitions'] = all_competitions
    stats['thursday'] = datetime.today().weekday() == 3
    # return well formatted json
    return json.dumps(stats, indent=4)




def transform_json_bubble(input_data):
    # Create a dictionary to hold the data for each grade
    seriesH = {'name': 'Homme', 'data': []}
    seriesF = {'name': 'Femme', 'data': []}

    # Create a dictionary to track grades and their corresponding data
    grade_data_h = {}
    grade_data_f = {}

    
    # Loop over the routes and add them to the appropriate grade
    for route in input_data['routes']:
        grade = route['grade']
        points_m = int(route['pointsM'])
        points_f = int(route['pointsF'])
        routenum = int(route['routenum'])

    # Add points_m to seriesH
        if grade not in grade_data_h:
            grade_data_h[grade] = {'x': grade, 'y': [points_m]}
        else:
            grade_data_h[grade]['y'].append(points_m)

        # Add points_f to seriesF
        if grade not in grade_data_f:
            grade_data_f[grade] = {'x': grade, 'y': [points_f]}
        else:
            grade_data_f[grade]['y'].append(points_f)

        
        #seriesH.get('data').append({'x': routenum, 'y': [points_m, points_m]})
        #seriesF.get('data').append({'x': routenum, 'y': [points_f, points_f]})
        
        seriesH.get('data').append([grade, points_m, points_m])
        seriesF.get('data').append([grade, points_f, points_f])
        
        
    #sorted_grades = sorted(grades.keys(), key=lambda x: (x  if x else 'ZZZ'))

    
    return [seriesH, seriesF]




def transform_json(input_data):
    # Create a dictionary to hold the data for each grade
    grades = {}
    
    # Loop over the routes and add them to the appropriate grade
    for route in input_data['routes']:
        grade = route['grade']
        points_m = int(route['pointsM'])
        points_f = int(route['pointsF'])
        
        # If this is the first route we've seen for this grade, create a new dictionary for it
        if grade not in grades:
            grades[grade] = {'homme': {'min': points_m, 'max': points_m, 'goals': []}, 
                             'femme': {'min': points_f, 'max': points_f, 'goals': []}}
        # Otherwise, update the min and max points for this grade
        else:
            if points_m < grades[grade]['homme']['min']:
                grades[grade]['homme']['min'] = points_m
            if points_m > grades[grade]['homme']['max']:
                grades[grade]['homme']['max'] = points_m
            if points_f < grades[grade]['femme']['min']:
                grades[grade]['femme']['min'] = points_f
            if points_f > grades[grade]['femme']['max']:
                grades[grade]['femme']['max'] = points_f
        
        # Add the route to the appropriate gender's goals list
        if points_m not in grades[grade]['homme']['goals']:
            grades[grade]['homme']['goals'].append(points_m)
        if points_f not in grades[grade]['femme']['goals']:
            grades[grade]['femme']['goals'].append(points_f)
    
    sorted_grades = sorted(grades.keys(), key=lambda x: (x  if x else 'ZZZ'))

    # Create a list of series data for each gender
    series = []
    for gender in ['homme', 'femme']:
        data = []
        for grade in sorted_grades:
            if grade in grades:
                #grade_data = {'x': grade, 'y': [grades[grade][gender]['min'], grades[grade][gender]['max']]}
                grade_data = {'x': grade, 'y': [grades[grade][gender]['min'], 1000]}
                if grades[grade][gender]['goals']:
                    goals = []
                    for goal in grades[grade][gender]['goals']:
                        goal = {'name': str(goal), 'value': goal, 'strokeColor': '#333333', 'strokeWidth': 4}
                        goals.append(goal)
                    grade_data['goals'] = goals
                data.append(grade_data)
        series.append({'name': gender.capitalize(), 'data': data})
    
    return series




def transform_jsonold(input_json):
    # Create two empty lists to store male and female data
    male_data = []
    female_data = []
    
    # Create a dictionary to store route data by grade
    data_by_grade = {}
    
    # Loop through each route in the input JSON
    for route in input_json['routes']:
        grade = route['grade']
        pointsM = int(route['pointsM'])
        pointsF = int(route['pointsF'])
        
        # Add the route to the data for its grade
        if grade not in data_by_grade:
            data_by_grade[grade] = {'goals': []}
        data_by_grade[grade]['goals'].append({
            'name': route['routenum'],
            'value': pointsM,
            'strokeColor': route['color1']
        })
        
        # Update the min and max points for male and female data
        if not any(d['x'] == grade for d in male_data):
            male_data.append({'x': grade, 'y': [pointsM, pointsM]})
        else:
            for d in male_data:
                if d['x'] == grade:
                    d['y'][0] = min(d['y'][0], pointsM)
                    d['y'][1] = max(d['y'][1], pointsM)
                    break
                
        if not any(d['x'] == grade for d in female_data):
            female_data.append({'x': grade, 'y': [pointsF, pointsF]})
        else:
            for d in female_data:
                if d['x'] == grade:
                    d['y'][0] = min(d['y'][0], pointsF)
                    d['y'][1] = max(d['y'][1], pointsF)
                    break
    
    # Sort male and female data by grade
    male_data.sort(key=lambda x: x['x'])
    female_data.sort(key=lambda x: x['x'])

    # Combine male and female data into the output series JSON
    series_json = [
        {'name': 'Male', 'data': male_data},
        {'name': 'Female', 'data': female_data}
    ]
    
    # Add the data for each grade to the appropriate object in the series JSON
    for grade, data in data_by_grade.items():
        for d in male_data:
            if d['x'] == grade:
                d.update(data)
                break
    
    return series_json








######## GYMS
@skala_api_app.route('/gym')
def gyms():
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    gyms = competitionsEngine.get_gyms()

    email = session.get('email')
    user = None
    if email is not None:
        user = competitionsEngine.get_user_by_email(email)
    name = session.get('name')

    if name is None:
        name = ""

    return gyms


@skala_api_app.route('/gyms')
def gyms_list(field=None, value=None):
    return gyms_list_by_field('status', 'created')



@skala_api_app.route('/gyms/search/')
def search_gyms():
    search_string = request.args.get('q')
    if search_string is None or len(search_string) < 2 or not search_string.isalnum():
        return []

    gyms=  skala_db.search_gym_by_name_address(search_string=search_string)
    # remove email and permissions from the response
    for gym in gyms:
        gym.pop('email', None)
        #user.pop('permissions', None)
        gym.pop('isgod',None)
        
        if gym.get('fpictureurl') is not None:
            gym['pictureurl'] = gym.get('fpictureurl')
        if gym.get('gpictureurl') is not None:
            gym['pictureurl'] = gym.get('gpictureurl')
       
    #json.dumps(users)
    return gyms



@skala_api_app.route('/gyms/names')
def gyms_names(field=None, value=None):
    return skala_db.get_all_gym_names()


@skala_api_app.route('/gyms/<field>/<value>')
def gyms_list_by_field(field=None, value=None):

    if field == 'status':
        s = competitionsEngine.reference_data.get('gym_status').get(value)
        gyms = competitionsEngine.get_gyms(status=s)
    #gyms = competitionsEngine.get_gyms()

    newgyms = []

    if gyms is None:
        return json.dumps(newgyms)
    
    for gymid in gyms:
        gym = gyms.get(gymid)
        
        if 'added_by' in gym:
            gym['added_by'] = gym['added_by'].split('@')[0]  # Remove part after @
        newgyms.append(gym)

        # sort gyms by name
    newgyms = sorted(newgyms, key=lambda x: x.get('name', '').lower())

    return newgyms


@skala_api_app.route('/gym/<gymid>')
def gym_by_id(gymid):
    gym = competitionsEngine.get_gym(gymid)
    return gym


@skala_api_app.route('/gym/<gymid>/')
def gym_by_id_default_route(gymid):

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(gym.get('routesid'))

    return routes


@skala_api_app.route('/gym/<gymid>/routes')
def routes_by_gym_id(gymid):
    gym = competitionsEngine.get_gym(gymid)

    routes = competitionsEngine.get_routes(gym.get('routesid'))
    return json.dumps(routes.get('routes'))

@skala_api_app.route('/gym/<gymid>/routes/list')
def route_sets_list(gymid):
    """Return list of all route sets for given gym id.
    Each entry: {id: <routeset id>, name: <display name>}.
    Uses skala_db.get_routes_by_gym_id.
    """
    try:
        route_sets = skala_db.get_routes_by_gym_id(gymid) or {}
        # Normalize to list for simpler front-end consumption
        normalized = []
        for rid, rdata in route_sets.items():
            name = rdata.get('name') or ''
            normalized.append({'id': rid, 'name': name})
        return json.dumps(normalized)
    except Exception as e:
        logging.error(f"Error fetching route sets list for gym {gymid}: {e}")
        return json.dumps({'status': 'error', 'message': 'Could not retrieve route sets'})



@skala_api_app.route('/gym/<gymid>/routes/<routesid>/delete', methods=['POST'])
def delete_gym_routes(gymid, routesid):
    user = competitionsEngine.get_user_by_email(session['email'])
    gym = competitionsEngine.get_gym(gymid)
    routes_set = competitionsEngine.get_routes_by_gym_id(gymid)

    if not competitionsEngine.can_edit_gym(user, gym):
        return json.dumps({'status': 'error', 'message': 'You do not have permission to delete routes'})

    if routesid not in routes_set:
        return json.dumps({'status': 'error', 'message': 'Routes do not belong to gym {gymid}'})
    
    result = competitionsEngine.delete_routes(routesid)
    return json.dumps(result)


def compute_difficulty_rating(status_array):
    if not status_array:
        return 0

    status_values = {
        'attempted': 3,
        'climbed': 2,
        'flashed': 1
    }

    total_score = sum(status_values[status] for status in status_array if status in status_values)
    average_score = total_score / len(status_array)

    # Normalize to a scale of 0 to 4
    difficulty_rating = (average_score - 1) / 2 * 4
    return difficulty_rating


def compute_average_user_grade(user_grades, original_grade):
    if not user_grades:
        return ""

    if original_grade not in grades:
        return ""

    # Convert grades to numerical values based on their index in the grades list
    total_grade = sum(grades.index(grade) for grade in user_grades if grade in grades)
    average_grade_index = total_grade / len(user_grades)
    
    # Convert the average grade index back to a grade
    average_grade = grades[int(round(average_grade_index))]

    # Compare with the original grade
    original_index = grades.index(original_grade)
    average_index = grades.index(average_grade)
    difference = average_index - original_index

    if difference == 0:
        return "&#10003;"
    elif difference == 1:
        return "&#8593;" #up arrow
    elif difference > 1:
        return "&#8593;&#8593;"
    elif difference == -1:
        return "&#8595;"
    elif difference < -1:
        return "&#8595;&#8595;"
    else: 
        return "*"


@skala_api_app.route('/gym/<gymid>/<routesid>')
def gym_by_id_route(gymid, routesid):

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(routesid)

    activities = activities_db.get_activity_routes_by_gym_id(gymid)
    route_map = {}
    route_counts = {}
    total_routes = len(set(activity['route_id'] for activity in activities))

    # Count the number of times each route appears
    for activity in activities:
        route_id = activity['route_id']
        if route_id not in route_counts:
            route_counts[route_id] = 0
        route_counts[route_id] += 1

    # Create the route map and assign ranks
    for activity in activities:
        route_id = activity['route_id']
        if route_id not in route_map:
            route_map[route_id] = {
                'id': route_id,
              
                'user_grade': [],
                'status': [],
                'note': [],
                'popularity_rank': 0,
                'difficulty_rating': 0
            }

        if 'user_grade' in activity and activity['user_grade']:
            route_map[route_id]['user_grade'].append(activity['user_grade'])
        if 'status' in activity and activity['status']:
            route_map[route_id]['status'].append(activity['status'])
        if 'note' in activity and activity['note']:
            route_map[route_id]['note'].append(activity['note'])

      
    # Compute aggregated star ratings (avg/count) across activities
    try:
        ratings_map = activities_db.compute_route_ratings(gymid, routesid)
    except Exception:
        ratings_map = {}

    for route in routes['routes']:
        route_id = route['id']
        if route_id in route_map:
            route_data = route_map[route_id]
            route_data['average_user_grade'] = compute_average_user_grade(route_data['user_grade'], route['grade'])
            route.update(route_data)
        else:
            route['average_user_grade'] = ""
            route['user_grade'] = []
        # Attach aggregated ratings if available
        rating = ratings_map.get(route_id)
        if isinstance(rating, dict):
            route['rating_avg'] = rating.get('rating_avg', 0)
            route['rating_count'] = rating.get('rating_count', 0)
        else:
            route['rating_avg'] = 0
            route['rating_count'] = 0

    return routes



@skala_api_app.route('/gym/<gymid>/routes/<routesid>/')
def get_gym_routes_enhanced_with_activities_stats(gymid, routesid):

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(routesid)



    #activities = activities_db.get_activity_routes_by_gym_id(gymid)

    #routes2 = activitiy_engine.enhance_routes(routes)
    #routes2 = activitiy_engine.enhance_routes(routes)
    #routs2 = get_activity_routes_by_gym_id(gymid)



    return routes




@skala_api_app.route('/gym/<gymid>/<routesid>/add', methods=['POST'])
@session_or_jwt_required
def route_add(gymid, routesid):

    routedata = request.get_json()
    routedata = json.loads(routedata)

    
    user = competitionsEngine.get_user_by_email(session['email'])

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return redirect(url_for("skala_api_app.fsgtlogin"))

    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    allroutes = all_routes.get(routesid)

    routeset = allroutes.get('routes')
    if not isinstance(routeset, list):
        return jsonify({'error': 'routeset_not_list'}), 400
    # Update or append the route by id
    updated = False
    for idx, existing in enumerate(routeset):
        if existing.get('id') == routedata.get('id'):
            routeset[idx] = routedata
            updated = True
            break
    if not updated:
        routeset.append(routedata)

    return json.dumps(allroutes)


# the input is json of a single route
# the response is all the routes as they have been saved
# this should be made thread safe but it isn't right now
@skala_api_app.route('/gym/<gymid>/<routesid>/saveone', methods=['POST'])
@session_or_jwt_required
def route_save(gymid, routesid):

    routedata = request.get_json()
    routedata = json.loads(routedata)

    user = competitionsEngine.get_user_by_email(session.get('email'))

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return Response("{'a':'b'}", status=401, mimetype='application/json')

    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    routeset = all_routes.get(routesid)

    logging.info("routesid: "+routedata['id'])
    routes = routeset.get('routes')
    if routedata['id'] is None or routedata['id'] == '':
        routedata['id'] = str(uuid.uuid4().hex)
    
    #idx = 0
    #while idx < int(routedata['routenum']):
    renumerate = False

    for idx, x in enumerate(routes):
            
        if x['id'] == routedata['id']:
            if routedata['routenum'] == '-1':
                routes.pop(idx)
            else:
                x.update(routedata)
            break
        # check if routenum is 3.5
        ##if float(routedata['routenum']) > float(x['routenum']) and float(routedata['routenum']) < float(x['routenum'])+1:
        if float(routedata['routenum']) % 1 == 0.5:
            routedata['routenum']= int(x['routenum'])+1
            routes.insert(int(x['routenum']),routedata )
           
    for idx, x in enumerate(routes):
        x['routenum']=int(idx)+1
    
    competitionsEngine.upsert_routes(routesid, gymid, routeset)

    return routeset





@skala_api_app.route('/gym/<gymid>/<routesid>/rate', methods=['POST'])
@session_or_jwt_required
def route_rating(gymid, routesid):

    data = request.get_json()
    data = json.loads(data)

    note = data.get('notes_user')
    route_finish_status = data.get('route_finish_status')
    grade = data.get('grade_user')
    user_grade = data.get('grade_user')
    route_stars = data.get('route_stars')

    user = competitionsEngine.get_user_by_email(session['email'])
    gym = competitionsEngine.get_gym(gymid)

    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    allroutes = all_routes.get(routesid)

    routeset = allroutes.get('routes')
    
    today = datetime.today().date()
    today = today.strftime('%Y-%m-%d')

    route = None
    for route in routeset:
        if route['id'] == data['id']:
            route = route
            break

    activities = activities_db.get_activities_by_date_by_user(today, user['id'])
    
    rating_activity_name = competitionsEngine.reference_data['current_language']['rating_activity_name']

    activity_id = None
    if (len(activities) == 0):
        activity_id = activities_db.add_activity(user, gym, routesid, rating_activity_name, today)
    else:
        for activity in activities:
            if activity.get('gym_id') == gymid:
                activity = activity
                activity_id = activity.get('id')
                break
        if activity_id is None:
            activity_id = activities_db.add_activity(user, gym, routesid, rating_activity_name, today)
    #activity = activities_db.get_activity(activity_id)

    activity = activities_db.add_activity_attempt(activity_id, route, route_finish_status, note, user_grade, (route_stars or 0))

    
    return json.dumps(activity)


@skala_api_app.route('/activity/gym/<gym_id>', methods=['GET'])
def get_activity_routes_by_gym_id(gym_id):
    # Assuming activities is a list of all activities
    activities = activities_db.get_activities_by_gym_id(gym_id)

    # List to store matching session entries
    matching_entries = []

    # Iterate through all activities
    #return json.dumps(activities)
    return activities
   


@skala_api_app.route('/gym/<gymid>/save', methods=['POST'])
@session_or_jwt_required
def gym_save(gymid):

    formdata = request.form.to_dict(flat=False)

    args1 = request.args
    body = request.data
    bodyj = request.json

    routeid = formdata['routeid']
    routeline = formdata['routeline']
    color1 = formdata['color1']
    color2 = formdata['color2']
    #iscolor2same = formdata['iscolor2same']
    color_modifier = formdata['color_modifier']
    routegrade = formdata['routegrade']
    routename = formdata['routename']
    openedby = formdata['openedby']
    opendate = formdata['opendate']
    notes = formdata['notes']
    routesname = formdata['name'][0]
    permissioned_user = formdata['permissioned_user'][0]

    user = competitionsEngine.get_user_by_email(session['email'])

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return redirect(url_for("skala_api_app.fsgtlogin"))

    routes = []
    for i, routeline1 in enumerate(routeline):
        print (i)
        if routeid[i] == '0':
            routeid[i]=str(uuid.uuid4().hex)
        oneline = competitionsEngine._get_route_dict(routeid[i], str(i+1), routeline[i], color1[i], color2[i],
                                                     color_modifier[i], routegrade[i],
                                           routename[i], openedby[i], opendate[i], notes[i])
        routes.append(oneline)

    routes_dict = {}
    routes_dict['id'] = gym['routesid']
    routes_dict['name'] = routesname
    routes_dict['routes'] = routes

    gym['routes'] = []

    competitionsEngine.update_gym(gym['id'], gym)
    competitionsEngine.update_routes(gym['routesid'], routes_dict)

    gym = competitionsEngine.get_gym(gym['id'])
    gym['routes'] = []
    routes = competitionsEngine.get_routes(gym['routesid'])

    return routes




@skala_api_app.route('/gyms/<gymid>/<routesid>/save', methods=['POST'])
@session_or_jwt_required
def gym_routes_save(gymid, routesid):
    formdata = request.form.to_dict(flat=False)

    args1 = request.args
    body = request.data
    bodyj = request.json

    routeid = formdata['routeid']
    routeline = formdata['routeline']
    color1 = formdata['color1']
    color2 = formdata['color2']
    #iscolor2same = formdata['iscolor2same']
    color_modifier = formdata['color_modifier']
    routegrade = formdata['routegrade']
    routename = formdata['routename']
    openedby = formdata['openedby']
    opendate = formdata['opendate']
    notes = formdata['notes']
    routesname = formdata['name'][0]

    delete = formdata.get('delete')
    save = formdata.get('save')
    copy = formdata.get('copy')

    user = competitionsEngine.get_user_by_email(session['email'])

    gym = competitionsEngine.get_gym(gymid)
    if not competitionsEngine.can_edit_gym(user, gym):
        return Response("{'a':'b'}", status=401, mimetype='application/json')

    routes = []
    for i, routeline1 in enumerate(routeline):
        if routeid[i] == '0':
            routeid[i]=str(uuid.uuid4().hex)
        oneline = competitionsEngine._get_route_dict(routeid[i], str(i+1), routeline[i], color1[i], color2[i],
                                                     color_modifier[i], routegrade[i],
                                           routename[i], openedby[i], opendate[i], notes[i])
        routes.append(oneline)

    routes_dict = {}
    routes_dict['id'] = routesid
    routes_dict['name'] = routesname
    routes_dict['routes'] = routes

    if copy is not None:
        newroutesid = str(uuid.uuid4().hex)
        routes_dict['id'] = newroutesid
        routes_dict['name'] = routes_dict['name']+' copy'
        competitionsEngine.upsert_routes(newroutesid, gymid, routes_dict)
        return redirect(f'/gyms/{gymid}/{newroutesid}/edit')

    competitionsEngine.update_routes(routesid, routes_dict)

    # pickup the default routes to be rendered
    routes = competitionsEngine.get_routes(gym.get('routesid'))

    return routes








@skala_api_app.route('/gyms/<gym_id>/update', methods=['POST'])
@session_or_jwt_required
def gyms_update(gym_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    formdata = request.form.to_dict(flat=False)
    gym = competitionsEngine.get_gym(gym_id)

    if not competitionsEngine.has_permission_for_gym(gym_id, user):
        return " { '7788':'no permission to edit gym' }"

    body = request.data
    bodyj = request.json
    files = request.files
    delete = formdata.get('delete')
    save = formdata.get('save')

    imgfilename = None
    if 'file1' in request.files:
        file1 = request.files['file1']
        if file1.filename is not None and len(file1.filename) > 0:
            imgfilename = gym_id
            imgpath = os.path.join(UPLOAD_FOLDER, imgfilename)
            file1.save(imgpath)

    gymName = formdata['gymName'][0]
    #numberOfRoutes = formdata['numberOfRoutes'][0]
    address = formdata['address'][0]
    url = formdata['url'][0]
    organization = formdata['organization'][0]
    permissioned_user = request.form.get('permissioned_user')

    routesidlist = formdata.get('default_routes')
    if routesidlist is not None:
        routesid = formdata['default_routes'][0]

    if delete is not None:
        competitionsEngine.delete_gym(gym_id)
        competitionsEngine.remove_user_permissions_to_gym(user, gym_id)
        if gym.get('logo_img_id') is not None and len(gym.get('logo_img_id')) > 0:  
            os.remove(os.path.join(UPLOAD_FOLDER, gym['logo_img_id']))
        return redirect(url_for('skala_api_app.gyms'))

    if routesid is None or len(routesid)==0:
        routesid = gym['routesid']

    if len(permissioned_user)>2:
        newuser = competitionsEngine.get_user_by_email(permissioned_user)
        if newuser is not None:
            competitionsEngine.add_user_permissions_to_gym(newuser, gym_id)

    
    gym_json = competitionsEngine.get_gym_json(gym_id, routesid, gymName, None, imgfilename, url, address, organization, None)

    gym.update((k, v) for k, v in gym_json.items() if v is not None)
    competitionsEngine.update_gym(gym_id, gym)

    return


# this doesn't work so well... there is a main_app_ui version that works better
@skala_api_app.route('/image/<img_id>')
def image_route(img_id):
    # Attempt to infer mime type from extension
    ext = os.path.splitext(img_id)[1].lower()
    mime_map = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif'}
    mime_type = mime_map.get(ext, 'application/octet-stream')
    return send_from_directory(UPLOAD_FOLDER, img_id, mimetype=mime_type)


