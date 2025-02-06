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

import json
import os
import io
import glob
import random
import uuid
from datetime import datetime, date, time, timedelta
from src.User import User
import competitionsEngine
import csv
from functools import wraps
import qrcode 
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask
  
import skala_db

from flask import Flask, redirect, url_for, session, request, render_template, send_file, send_from_directory, \
    jsonify, Response, \
    stream_with_context, copy_current_request_context, make_response

import logging

from flask import Blueprint
import activities_db as activity_engine

from io import BytesIO

from flask import send_file
import skala_api

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

#app_ui = Blueprint('app_ui', __name__)

from authlib.integrations.flask_client import OAuth
from authlib.integrations.flask_client import OAuthError

import activities_db as activities_db
#from flask_openapi3 import Info, Tag, APIBlueprint
#from flask_openapi3 import OpenAPI

from src.email_sender import EmailSender

# Initialize EmailSender with necessary configurations
email_sender = EmailSender(
    reference_data=competitionsEngine.reference_data
)


languages = {}

DATA_DIRECTORY = os.getenv('DATA_DIRECTORY')

if DATA_DIRECTORY is None:
    DATA_DIRECTORY = os.getcwd()

#PLAYLISTS_DB = DATA_DIRECTORY + "/db/playlists.sqlite"
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

#tag = Tag(name="UI operations", description='UI operations which return HTML pages - competitionsApp.py')
#app_ui = APIBlueprint('app_ui', __name__, abp_tags=[tag])
app_ui = Blueprint('app_ui', __name__, static_folder='public')

app_ui.debug = True
app_ui.secret_key = 'development'
oauth = OAuth(app_ui)

genres = {"test": "1"}
authenticated = False

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



app_ui.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

UPLOAD_FOLDER = os.path.join(DATA_DIRECTORY,'uploads')

ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

#app_ui.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# User session management setup
# https://flask-login.readthedocs.io/en/latest



@app_ui.before_request
def x(*args, **kwargs):
    skala_api.x(*args, **kwargs)
    

@app_ui.route('/language/<language>')
def set_language(language=None):
    skala_api.set_language(language)
    
    # Get the origin of the request from the Referer header
    origin = request.headers.get('Referer')
    
    # Redirect to the origin if it's not None, otherwise redirect to the home page
    if origin:
        return redirect(origin)
    else:
        return redirect("/")


def login_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if skala_api.is_logged_in():
            return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("app_ui.fsgtlogin"))
    return decorated_function



def admin_required(fn):
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if session != None and (session.get('name') == 'David Mossakowski' or 
            session.get('name') == 'Sebastiao Correia'):
            now = int(datetime.now().timestamp())
            #expiresAt = session['expires_at']
            expiresAtLocaltime = session['expires_at_localtime']
            return fn(*args, **kwargs)
        else:
            session["wants_url"] = request.url
            return redirect(url_for("app_ui.fsgtlogin"))
    return decorated_function



@app_ui.get("/aa")
def index11():



    
    if session.get('username'):
        return '<a class="button" href="/login">logged in </a>'+session.get('username')

    if current_user.is_authenticated:
        return (
            "<p>Hello, {}! You're logged in! Email: {}</p>"
            "<div><p>Google Profile Picture:</p>"
            '<img src="{}" alt="Google profile pic"></img></div>'
            '<a class="button" href="/logout">Logout</a>'.format(
                current_user.name, current_user.email, current_user.profile_pic
            )
        )
    else:
        return '<a class="button" href="/login">Google Login</a>'



@app_ui.route('/competitionRawAdmin', methods=['GET'])
@login_required
@admin_required
def fsgtadminget():
    """
    Load Admin page from competitionRawAdmin.html
    """
    edittype = request.args.get('edittype')
    id = request.args.get('id')
    action = request.args.get('action')
    jsondata = request.args.get('jsondata')
    jsonobject = None

    return render_template('competitionRawAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@app_ui.post('/competitionRawAdmin')
@login_required
@admin_required
def fsgtadmin():
    """
    
    Do admin action

    This is an admin action
    """
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


        if id is not None and action == 'delete':
            competitionsEngine.delete_route(id)
        


    elif edittype == 'activities':
        if jsonobject is not None  and action == 'update':
            #jsonobject = {"success": "competition updated"}
            # None is gymid but this is ok as the routes id will be found
            # competitionsEngine.upsert_routes(id, None, jsonobject)
            return

        if id is not None and action == 'find':
            jsonobject = activities_db.get_activities(id)

        if id is not None and action == 'findall':
            jsonobject = activities_db.get_activities(id)

    else :
        jsonobject = {"error": "choose edit type" }

    return render_template('competitionRawAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@app_ui.route('/adminv2', methods=['GET'])
@login_required
@admin_required
def adminv2():
    edittype = request.args.get('edittype')
    id = request.args.get('id')
    action = request.args.get('action')
    jsondata = request.args.get('jsondata')
    jsonobject = None

    return render_template('adminv2.html',
                           reference_data=competitionsEngine.reference_data
                           )


@app_ui.route('/competition_admin/<competition_id>', methods=['GET'])
#, summary='returns competitionAdmin.html', 
 #           responses={"default": {"description": "Render template competitionAdmin.html"}})
@login_required
def competition_admin_get(competition_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    competition = competitionsEngine.getCompetition(competition_id)

    user_list = competitionsEngine.get_all_user_emails()
    if user is None or competition is None or not competitionsEngine.can_edit_competition(user,competition):
        session["wants_url"] = request.url
        return redirect(url_for('app_ui.getCompetition', competitionId=competition['id']))

    all_routes = competitionsEngine.get_routes_by_gym_id(competition['gym_id'])

    return render_template('competitionAdmin.html',
                           user=user,
                           competition=competition,
                           user_list=user_list,
                           competitionId=competition_id,
                           all_routes = all_routes,
                           reference_data=competitionsEngine.reference_data,
                           id=id)


@app_ui.route('/competition_admin/<competition_id>', methods=['POST'])
@login_required
def competition_admin_post(competition_id):
    remove_climber = request.form.get('remove_climber')
    update_status = request.form.get('update_status')
    permission_admin_user = request.form.get('permission_admin_user')
    permission_scorer_user = request.form.get('permission_scorer_user')
    max_participants = request.form.get('max_participants')
    # get climber id in competition admin table (not none when a change is saved)
    climber_id = request.form.get('update_climber')
    email_content = request.form.get('email_content')

    competition_update_button = request.form.get('competition_update_button')
    delete_competition_button = request.form.get('delete_competition_button')
    change_poster_button = request.form.get('change_poster_button')
    email_sending_button = request.form.get('email_sending_button')
    competition_routes_update_button = request.form.get('competition_routes_update_button')


    edittype = request.form.get('edittype')
    permissioned_user = request.form.get('permissioned_user')

    id = request.form.get('id')
    action = request.form.get('action')
    competition_status = request.form.get('competition_status')

    instructions = request.form.get('instructions')
    if instructions is not None:
        instructions = instructions.strip()

    user_id = request.form.get('userId')

    jsondata = request.form.get('jsondata')
    comp = {}
    jsonobject = None

    imgfilename = None
    if 'file1' in request.files:
        file1 = request.files['file1']
        if file1.filename is not None and len(file1.filename) > 0:
            imgfilename = competition_id
            # this needs a fix for SVG files.. currently they will not be displayed
            # the fix is to img field to each competition.. currently we retrieve the image as a file
            imgpath = os.path.join(UPLOAD_FOLDER, imgfilename)
            file1.save(imgpath)

    user = competitionsEngine.get_user_by_email(session['email'])
    competition = competitionsEngine.getCompetition(competition_id)
    resultMessage = None
    resultError = None

    if user is None or competition is None or not competitionsEngine.can_edit_competition(user,competition):
        session["wants_url"] = request.url
        return redirect(url_for("app_ui.fsgtlogin"))

    
    # add this competition to another user's permissions
    # remove this competition from another users permissions
    # change the state of a competition
    # remove climber from a competition

    if permission_admin_user is not None:
        user2 = competitionsEngine.get_user(user_id)
        competitionsEngine.modify_user_permissions_to_competition(user2, competition_id)
        competitionsEngine.add_user_permission_edit_competition(user2)
        resultMessage= "User added as a competition admin"


    if permission_scorer_user is not None:
        user2 = competitionsEngine.get_user(user_id)
        competitionsEngine.modify_user_permissions_to_competition(user2, competition_id)
        competitionsEngine.add_user_permission_update_routes(user2)
        resultMessage= "User added as scorer"


    if update_status is not None:
        competition['status'] = int(competition_status)
        competitionsEngine.update_competition(competition_id, competition)
        competitionsEngine.setRoutesClimbed2(competition)
        resultMessage= "Status updated"

    if remove_climber is not None:
        competition['climbers'].pop(remove_climber)
        competitionsEngine.update_competition(competition['id'], competition)
        resultMessage= "Climber removed"

    if climber_id is not None:
        competition['climbers'][climber_id]['name'] = request.form.get('name_'+ climber_id)
        competition['climbers'][climber_id]['sex'] = request.form.get('sex_'+ climber_id)
        competition['climbers'][climber_id]['club'] = request.form.get('club_'+ climber_id)
        competition['climbers'][climber_id]['email'] = request.form.get('email_'+ climber_id)
        try:
            # Attempt to retrieve the category from the form data and convert it to an integer
            competition['climbers'][climber_id]['category'] = int(request.form.get('category_' + str(climber_id)))
        except (ValueError, TypeError):
            # Handle the exception if the conversion fails
            print("The provided category is not a valid integer for climber " + competition['climbers'][climber_id]['name'])
            # Set to a default value or handle the error as appropriate
            competition['climbers'][climber_id]['category'] = 0  # Replace default_value with whatever default you wish to use
        competitionsEngine.update_competition(competition['id'], competition)

    if competition_update_button is not None:
        competition_name = request.form.get('competition_name')
        competition_date = request.form.get('competition_date')
        
        max_participants = request.form.get('max_participants')
        # update gym name in the competition if Gym Name is changed somewhere else
        gym = competitionsEngine.get_gym(competition['gym_id'])
        if gym is not None:
            if gym['name'] != competition['gym']:
                competition['gym']=gym['name']
        competition['max_participants']=max_participants

        competitionsEngine.update_competition_details(competition, competition_name, competition_date, instructions)
        resultMessage= "Competition details updated"


    if competition_routes_update_button is not None:
        competition_routes = request.form.get('competition_routes')
        competitionsEngine.update_competition_routes(competition, competition_routes, True)
        resultMessage= "Competition routes updated"


    if delete_competition_button is not None:
        if competitionsEngine.competition_can_be_deleted(competition):
            competitionsEngine.delete_competition(competition['id'])
            return redirect(f'/competitionDashboard')

    if change_poster_button is not None and imgfilename is not None:
        competitionsEngine.update_competition(competition['id'], competition)
        resultMessage= "Poster updated"

    if email_sending_button is not None:
        if email_content is not None and len(email_content) > 20:
            print("email_content: " + email_content)
            recipientCount = competitionsEngine.send_email_to_participants(competition, user['id'], email_content)
            if recipientCount == 0:
                resultError = "No valid email addresses found"
            else:
                resultMessage = "Email sent to " + str(recipientCount) + " participants"
        else:
            resultError = "Email content is empty or too short"
            
    user_list = competitionsEngine.get_all_user_emails()
    all_routes = competitionsEngine.get_routes_by_gym_id(competition['gym_id'])
            
    return render_template('competitionAdmin.html',
                           jsondata=json.dumps(jsonobject),
                           user=user,
                           competition=competition,
                           user_list=user_list,
                           competitionId=competition_id,
                           all_routes = all_routes,
                           reference_data=competitionsEngine.reference_data,
                           id=id,
                           resultMessage=resultMessage,
                           resultError=resultError)


@app_ui.route('/fsgtadmin/<edittype>')
def fsgtadminedit(edittype):
    j = request.args.get('jsondata')

    if edittype == 'user' and j['email'] is not None:
        competitionsEngine.upsert_user(j)

    return render_template('competitionRawAdmin.html',
                           reference_data=competitionsEngine.reference_data)


# for some reason I added a case here to go to the home page
# no idea why
@app_ui.route('/loginchoice')
def fsgtlogin(error=None):    
    return render_template('competitionLogin.html',
                           reference_data=competitionsEngine.reference_data,
                           error=error
                        )
                           










@app_ui.route('/activities', methods=['GET'])
@login_required
def activities():
    user = competitionsEngine.get_user_by_email(session['email'])

    return render_template('activities.html',
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           today=date.today()
                           )


#@app_ui.route('/activities/<activity_id>', methods=['GET'], description='returns activity-detail.html')
@app_ui.route('/activities/<activity_id>', methods=['GET'])
#@login_required
def activity_detail(activity_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    activity = activity_engine.get_activity(activity_id)
    gym = competitionsEngine.get_gym(activity['gym_id'])

    #gym = competitionsEngine.get_gym(journey['gym_id'])

    if activity.get('routes_id') is None:
        routes = competitionsEngine.get_routes("7134a8ef-fa2e-4672-a247-115773183bcd")  # should return  Nanterre routes
    else:
        routes = competitionsEngine.get_routes(activity['routes_id'])

    return render_template('activity-detail.html',
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           activity=activity,
                           routes=routes,
                           gym=gym,
                           today=date.today(),
                           activity_id=activity_id,
                           )


@app_ui.route('/activities/dialog', methods=['GET'])
#@login_required
def activity_detail_dialog():

    user = competitionsEngine.get_user_by_email(session['email'])
    activity = activity_engine.get_activity(activity_id)
    gym = competitionsEngine.get_gym(activity['gym_id'])


    return render_template('activity-detail.html',
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           activity=activity,
                           routes=routes,
                           gym=gym,
                           today=date.today(),
                           activity_id=activity_id,
                           )
 

@app_ui.route('/journey/add', methods=['POST'])
@login_required
def journey_add():
    user = competitionsEngine.get_user_by_email(session['email'])

    date = request.form.get('date')
    gym_id = request.form.get('gym_id')
    comp = {}
    gym = competitionsEngine.get_gym(gym_id)

    journey = activity_engine.add_journey_session(user,gym_id, gym.get('routesid'), date)
    #journey_id = user.get('journey_id')

    #if journey_id is None:
    #    journey = activity_engine.add_journey(user, description)

    journeys = activity_engine._get_journey_sessions_by_user_id(user.get('id'))
    return render_template('skala-journey.html',
                           user=user,
                           journeys=journeys,
                           journey=journey,
                           reference_data=competitionsEngine.reference_data
                           )


@app_ui.route('/journey/<journey_id>', methods=['GET'])
@login_required
def journey_session(journey_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    journey = activity_engine.get_journey_session(journey_id)

    #gym = competitionsEngine.get_gym(journey['gym_id'])

    if journey.get('routes_id') is None:
        routes = competitionsEngine.get_routes("7134a8ef-fa2e-4672-a247-115773183bcd")  # should return  Nanterre routes
    else:
        routes = competitionsEngine.get_routes(journey['routes_id'])

    return render_template('skala-journey-session.html',
                           user=user,
                           journey=journey,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@app_ui.route('/journey/<journey_id>/add', methods=['POST'])
@login_required
def journey_session_entry_add(journey_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    route_finish_status = request.form.get('route_finish_status')
    route_id = request.form.get('route')
    notes = request.form.get('notes')

    comp = {}

    journey = activity_engine.get_journey_session(journey_id)

    journey = activity_engine.add_journey_session_entry(journey_id,route_id, route_finish_status, notes)
    routes = competitionsEngine.get_routes(journey.get('routes_id'))

    return render_template('skala-journey-session.html',
                           user=user,
                           journey=journey,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@app_ui.route('/journey/<journey_id>/<route_id>/remove', methods=['GET'])
@login_required
def journey_session_remove(journey_id, route_id):
    user = competitionsEngine.get_user_by_email(session['email'])
    journey = activity_engine.get_journey_session(journey_id)

    activity_engine.remove_journey_session(journey_id, route_id)
    routes = competitionsEngine.get_routes(journey.get('routes_id'))

    return render_template('skala-journey-session.html',
                           user=user,
                           journey=journey,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )



@app_ui.route('/privacy')
def privacy():
    return render_template('privacy.html',
                           reference_data=competitionsEngine.reference_data
                           )



@app_ui.route('/')
def index():
    langs = competitionsEngine.reference_data['languages']

    language = session.get('language')
    if language is None:
        logging.debug('language is None. setting to fr_FR')
        language = 'fr_FR'
        session['language'] = language

    user = competitionsEngine.get_user_by_email(session.get('email'))
    competitions= competitionsEngine.getCompetitions()

    return render_template('skala3ma.html',
                           competitions=competitions,
                           competitionName=None,
                           session=session,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           #langpack=language,
                            **session
                           )


@app_ui.route('/main')
def main():
    return redirect("/")


@app_ui.route('/competitionCalendar')
def getCompetitionCalendar():

    #username = session.get('username')
    logging.info('competitionCalendar language=' + str(session.get('language')))
    can_create_competition = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is not None:
        can_create_competition = competitionsEngine.can_create_competition(user)
    
    #langs = competitionsEngine.reference_data['languages']
    return render_template('competitionCalendar.html',
                           session=session,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           language=session['language'],
                           #langpack=languages['en_US'],
                           can_create_competition=can_create_competition
                           # **session
                           )


@app_ui.route('/competitionDashboard')
def getCompetitionDashboard():
    # select season year depending on current month;
    # e.g. if 2023-10-01 then season is 2023-24 
    # if 2023-05-01 then season is 2022-23
    current_year = datetime.now().year
    current_month = datetime.now().month
    season = current_year if current_month >= 9 else current_year-1 
    return competitions_by_year(str(season))


@app_ui.route('/competitions/year/<year>')
def competitions_by_year(year):

    username = session.get('username')
    name = request.args.get('name')
    date = request.args.get('date')
    gym = request.args.get('gym')
    if not year.isdigit():
        year = datetime.now().year
    can_create_competition = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is not None:
        can_create_competition = competitionsEngine.can_create_competition(user)
    subheader_message = request.accept_languages
    langs = competitionsEngine.reference_data['languages']
    
    competitions3 = competitionsEngine.get_competitions_by_year(year)
    
    return render_template('competitionDashboard.html',
                           subheader_message=subheader_message,
                           competitions=competitions3,
                           competitionName=None,
                           session=session,
                           user=user,
                           year=year,
                           reference_data=competitionsEngine.reference_data,
                           #langpack=languages['en_US'],
                           can_create_competition=can_create_competition,
                            **session
                           )


@app_ui.route('/newCompetition', methods=['GET'])
@login_required
def new_competition():

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

    all_gyms = competitionsEngine.get_gyms()

    clubs = []

    for gymid in all_gyms:
        gymname = all_gyms[gymid]['name']
        routes = competitionsEngine.get_routes_by_gym_id(gymid)
        for routeid in routes:
            clubs.append ({'gymname':gymname, 'gymid':gymid, 'routesid':routeid, 'routesname':routes[routeid]['name']})


    return render_template('newCompetition.html',
                           competitionName=None,
                           session=session,
                           gyms=gyms,
                           clubs=clubs,
                           reference_data=competitionsEngine.reference_data,

                            **session)


# method to add a new competition
@app_ui.route('/newCompetition', methods=['POST'])
@login_required
def new_competition_post():
    username = session.get('username')
    #if username:
    #    return 'logged in '+str(username)
    #print(username)

    #username = request.args.get('username')
    name = request.form.get('name')
    date = request.form.get('date')
    #gym = request.form.get('gym')
    routesid = request.form.get('routes')
    competition_type = request.form.get('competition_type')
    max_participants = request.form.get('max_participants')
    instructions = request.form.get('instructions')

    comp = {}
    competitionId = None

    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is None or not competitionsEngine.can_create_competition(user):
        return redirect(url_for('app_ui.fsgtlogin', competitionId=competitionId))

    added_by = user['id']
    if name is not None and date is not None and routesid is not None and max_participants is not None:
        competitionId = competitionsEngine.addCompetition(None, added_by, name, date, routesid, max_participants,
                                                          competition_type=competition_type, instructions=instructions)
        # now if an image was provided, save it under the competition id
        # there is only one main image allowed per competition for now
        # any new image will overwrite the previous one
        if 'file1' in request.files:
            file1 = request.files['file1']
            if file1.filename is not None and len(file1.filename) > 0:
                imgpath = os.path.join(UPLOAD_FOLDER, competitionId)
                file1.save(imgpath)

        competitionsEngine.modify_user_permissions_to_competition(user, competitionId, "ADD")
        comp = getCompetition(competitionId)
        return redirect(url_for('app_ui.getCompetition', competitionId=competitionId))

    subheader_message='Welcome '
    competitions= competitionsEngine.getCompetitions()

    return render_template('competitionDashboard.html',
                           subheader_message=subheader_message,
                           competitions=competitions,
                           competitionName=None,
                           session=session,
                           reference_data=competitionsEngine.reference_data,
                            **session)




@app_ui.route('/competitionDashboard/<competitionId>/register')
#@login_required
def addCompetitionClimber(competitionId):
    useremail = session.get('email')
    firstname = request.args.get('firstname')
    lastname = request.args.get('lastname')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    otherclub = request.args.get('otherclub')
    category = request.args.get('category')
    dob = request.args.get('dob')
    
    comp = competitionsEngine.getCompetition(competitionId)
    user = competitionsEngine.get_user_by_email(useremail)
    climber_id = str(uuid.uuid4().hex)
    if user is not None:
        climber_id = user['id']
    form_user = competitionsEngine.get_user_by_email(email)

    competition_accepts_registrations = competitionsEngine.competition_accepts_registrations(comp)
    error_code = ''
    if not competition_accepts_registrations:
        error_code = "error5322"
    
    is_registered = competitionsEngine.is_registered(user, comp)
    climber = None

    # check if user with this email is known and should login themselves to register
    if user is None and form_user is not None and form_user.get('is_confirmed') == 1:
        error_code = "error5316" 

    # the user found by email on form is already registered
    is_form_user_registered = competitionsEngine.is_registered(form_user, comp)
    if is_form_user_registered:
        error_code = "error5321"

    if dob is not None:
        category = competitionsEngine.get_category_from_dob(dob)   
        if category == -1:
            error_code = "error5325"

    if not error_code and not is_registered and firstname is not None and sex is not None and club is not None and email is not None:
        #climber = competitionsEngine.get_climber_by_email(email)
        name = firstname + " " + lastname

        try:
            if club not in competitionsEngine.clubs.values():
                club = otherclub
            climber = competitionsEngine.addClimber(climber_id, competitionId, email, name, firstname, lastname, club, sex, category)
            if useremail is not None and useremail == email and user.get('is_confirmed') == 1:
                competitionsEngine.user_registered_for_competition(climber['id'], name, firstname, lastname, email, climber['sex'],
                                                               climber['club'],  dob)
            comp = competitionsEngine.getCompetition(competitionId)
            competitionName = comp['name']
            #subheader_message = 'You have been registered! Thanks!'
            #return redirect(url_for('app_ui.getCompetition', competitionId=competitionId))
            return render_template("competitionClimberRegistered.html", 
                    competitionId=competitionId,
                    competition=comp,
                    reference_data=competitionsEngine.reference_data,
                    library=None,
                    **session)
        except ValueError as e:
            logging.error('Error adding climber {str(e)}')
            # this user is alrady registered
            error_code = "error5321"
            
    ##   comp=None # this is to not show the list of climbers before registration

    #competitions = competitionsEngine.getCompetitions()
    name = session.get('name')

    if name is None:
        name = ""

    can_unregister = competitionsEngine.can_unregister(user, comp)
    enable_registration = False
    if competition_accepts_registrations and not is_registered and not error_code:
        enable_registration = True

    return render_template('competitionClimber.html',
                           error_code=error_code,
                           competition=comp,
                           competitionId=competitionId,
                           climber=climber,
                           user = user,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=useremail,
                           logged_name=name,
                           can_unregister=can_unregister,
                           is_registered=is_registered,
                           enable_registration=enable_registration,
                            **session)




@app_ui.route('/competitionDashboard/<competitionId>/unregister')
@login_required
def unregister(competitionId):
    if session.get('email') is not None:
        climber = competitionsEngine.get_user_by_email(session.get('email'))
        if climber is not None:
            competitionsEngine.removeClimber(climber['id'], competitionId)
            return redirect(url_for('app_ui.getCompetition', competitionId=competitionId))
        
    return redirect(url_for('app_ui.getCompetition', competitionId=competitionId))



@app_ui.route('/user')
def get_user():
    if session.get('email') is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               reference_data=competitionsEngine.reference_data,
                               subheader_message="No user found",
                               **session)

    climber = competitionsEngine.get_user_by_email(session.get('email'))

    #subheader_message = request.args.get('update_details')

    email = session.get('email')
    name = session.get('name')

    if name is None:
        name = ""

    return render_template('climber.html',
                           #subheader_message=subheader_message,
                           competitionId=None,
                           climber=climber,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=email,
                            **session)



# function to save user details 
@app_ui.route('/updateuser')
def update_user():
    if session.get('email') is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="Login required",
                               **session)

    climber = competitionsEngine.get_user_by_email(session.get('email'))

    firstname = request.args.get('firstname')
    lastname = request.args.get('lastname')
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    clubid = request.args.get('club')
    dob = request.args.get('dob')
    subheader_message = ""

    if clubid is not None and clubid.isnumeric():
        clubid = int(clubid)
        club = competitionsEngine.reference_data['clubs'].get(clubid)
    elif clubid == 'other' and request.args.get('otherclub') is not None and len(request.args.get('otherclub').strip()) > 0:
        club = request.args.get('otherclub').strip()
    else:
        club = None

    error_message = ''
    categoryold = request.args.get('category')

    category = competitionsEngine.get_category_from_dob(dob)
    if category == -1:
        #error_message.append(competitionsEngine.reference_data['current_language']['error5325'])
        error_message='error5325'

    

    email = session.get('email')
    name = session.get('name')

    climber['firstname'] = firstname
    climber['lastname'] = lastname
    climber['fullname'] = fullname
    climber['nick'] = nick
    climber['email'] = email
    climber['sex'] = sex    
    climber['dob'] = dob

    if firstname is None or nick is None or sex is None or club is None or email is None:
        error_message= 'all_fields_required'
        #subheader_message = "Update"

    if error_message is not None and len(error_message) > 0:
        #error_message_str = '. '.join(error_message) + '.'
        return render_template('climber.html',
                               error_message = error_message,
                               competitionId=None,
                               climber=climber,
                               reference_data=competitionsEngine.reference_data,
                               logged_email=email,
                               logged_name=name,
                               **session)

    else:
        climber = competitionsEngine.user_self_update(climber, name, firstname, lastname, nick, sex, club, dob)
        subheader_message = competitionsEngine.reference_data['current_language']['details_saved']
        level = 'success'


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





@app_ui.route('/myresultats')
@login_required
def myskala():
    subheader_message = "My skala"
    
    competition={}


    return render_template("myskala.html", 
                           subheader_message=subheader_message,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           library=None,
                           **session)



@app_ui.route('/mygyms')
@login_required
def get_mygyms():
    if session.get('email') is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               reference_data=competitionsEngine.reference_data,
                               subheader_message="No user found",
                               **session)

    climber = competitionsEngine.get_user_by_email(session.get('email'))
    user = User.from_dict(climber)
    ids = user.get_permissions('gyms')
    
    homegym = competitionsEngine.get_gym(user.get_home_gym())
    
    gyms = competitionsEngine.get_gyms_by_ids(ids)

    email = session.get('email')
    name = session.get('name')

    if name is None:
        name = ""

    return render_template('gyms.html',
                           #subheader_message=subheader_message,
                           competitionId=None,
                           climber=climber,
                           gyms=gyms,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=email,
                            **session)


@app_ui.route('/competitionDetails/<competitionId>')
#@login_required
def getCompetition(competitionId):
    #competitionId = request.args.get('competitionId')

    #comps = skala_db.get_users_with_competition_id(competitionId)
    #print ('matching users', comps)

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


    subheader_message = "CompetitionDetails '" + competition['name'] + "' on "+competition['date']

    # library= {}
    # library['tracks'] = tracks
    # playlist = json.dumps(playlist)
    # u = url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message)
    # return redirect(url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message,
    #                       library=None,
    #                       **session))



    return render_template("competitionDetails.html", competitionId=competitionId,
                           competition=competition,
                           subheader_message=subheader_message,
                           reference_data=competitionsEngine.reference_data,
                           library=None,
                           **session)



@app_ui.route('/competitionResults/<competitionId>')
#@login_required
def getCompetitionResults(competitionId):
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

    rankings = None

    isAdminUser = False

    if session.get('email') is not None: 
        user = competitionsEngine.get_user_by_email(session.get('email'))
        if competitionsEngine.has_permission_for_competition(competitionId, user):
            isAdminUser = True

    if isAdminUser or (competition['status']  in [competitionsEngine.competition_status_closed,
                                    competitionsEngine.competition_status_scoring]): 
        rankings = competitionsEngine.get_sorted_rankings(competition)

    return render_template("competitionResults.html", 
                           competitionId=competitionId,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           rankings = rankings,
                           **session)



# Statistics for a competition
@app_ui.route('/competitionStats/<competitionId>')
#@login_required
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
    rankings = None

    isAdminUser = False
    #if skala_api.is_logged_in():

    if session.get('email') is not None: 
        user = competitionsEngine.get_user_by_email(session.get('email'))
        if competitionsEngine.has_permission_for_competition(competitionId, user):
            isAdminUser = True

    if isAdminUser or (competition['status']  in [competitionsEngine.competition_status_closed,
                                    competitionsEngine.competition_status_scoring]): 
        rankings = competitionsEngine.get_sorted_rankings(competition)


    return render_template("competitionStats.html", competitionId=competitionId,
                           competition=competition,
                           reference_data=competitionsEngine.reference_data,
                           rankings = rankings,
                           **session)



#@app_ui.route('/competitionDashboard/<competitionId>/climber/<climberId>')
#@login_required
# THIS IS NOT USED PROBABLY!!!!
def getCompetitionClimber(competitionId, climberId):
    #competitionId = request.args.get('competitionId')

    routesUpdated = []
    for i in range(100):
        routeChecked = request.args.get("route"+str(i)) != None
        if routeChecked: routesUpdated.append(i)


    #   logging.info(session['id']+' competitionId '+competitionId)
    # r = request
    # username = request.args.get('username')

    competition = None

    if climberId is not None:
        if len(routesUpdated) > 0:
            competitionsEngine.setRoutesClimbed(competitionId, climberId, routesUpdated)
            competition = competitionsEngine.getCompetition(competitionId)
            return render_template('competitionDashboard.html', sortedA=None,
                                   competition=competition,
                                   competitionId=competitionId,
                                   subheader_message="Climber routes saved",
                                    reference_data=competitionsEngine.reference_data,
                                   **session)


        climber = competitionsEngine.getClimber(competitionId,climberId)


    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No climber found",
                               **session)
    elif climber is LookupError:
        return render_template('index.html', sortedA=None,
                                   getPlaylistError="error  ",
                                   library={},
                                   **session)
    elif len(climber) == 0:
        return render_template('index.html', sortedA=None,
                                   getPlaylistError="Playlist has no tracks or it was not found",
                                   library={},
                                   **session)

    competition = competitionsEngine.getCompetition(competitionId)
    subheader_message = climber['name']+"   from "+climber['club']

    # library= {}
    # library['tracks'] = tracks
    # playlist = json.dumps(playlist)
    # u = url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message)
    # return redirect(url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message,
    #                       library=None,
    #                       **session))

    return render_template("competitionDashboard.html", climberId=climberId, climber=climber,
                           subheader_message=subheader_message,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)




@app_ui.route('/competitionResults/<competitionId>/download')
def downloadCompetitionCsv(competitionId):

    competition = competitionsEngine.getCompetition(competitionId)
    gymid = competition['gym']
    #gym = competitionsEngine.get_gym(gymid)
    routesid = competition.get('routesid')
    routes = competitionsEngine.get_routes(routesid)
    if routes is not None:
        routes = routes.get('routes')



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
        data['grades'] = ""
        grades = []
        for routenum in competition['climbers'][climberid]['routesClimbed']:
            if 0 < routenum <= len(routes):
                grades.append(routes[routenum-1]['grade'])
            else:
                # Handle the case where routenum is out of bounds
                grades.append("N/A")
                print(f"Warning: routenum {routenum} is out of bounds for the routes list.")
                        
        
        #data['grades'] = data['grades']+ routes[routenum-1]['grade'] + " "
        #grades.append(routes[routenum-1]['grad e'])
        grades = sorted(grades)
        data['grades'] = ' '.join(grades)
        data['newscore'] = competitionsEngine.calculate_score(grades)

        for i in range(100):
            data.pop('id', None)
            data.pop('email', None)
            data.pop('name',None)
            data.pop('routesClimbed2',None)

            data.pop('AAAAAA',None)

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



@app_ui.route('/competitionRoutesEntry/<competitionId>')
@login_required
def competitionRoutesList(competitionId):
    #competitionId = request.args.get('competitionId')

    user = competitionsEngine.get_user_by_email(session['email'])

    competition = competitionsEngine.getCompetition(competitionId)

    error_code = ""
    if not competitionsEngine.can_update_routes(user,competition):
        error_code = "error5314"

    gymid = competition['gym']
    #gym = competitionsEngine.get_gym(gymid)
    routesid = competition.get('routesid')

    if len(competition.get('climbers').values())>0 and 'lastname' in list(competition.get('climbers').values())[0].keys():
        sorted_data = dict(sorted(competition.get('climbers').items(), key=lambda x: x[1]['lastname'].upper()))
        competition['climbers']= sorted_data

    # library= {}
    # library['tracks'] = tracks
    # playlist = json.dumps(playlist)
    # u = url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message)
    # return redirect(url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message,
    #                       library=None,
    #                       **session))

    return render_template("competitionClimberList.html",
                           error_code=error_code,
                           user=user,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)



@app_ui.route('/competitionRoutes/<competitionId>')
@login_required
def competitionRoutes(competitionId):
    #competitionId = request.args.get('competitionId')

    user = competitionsEngine.get_user_by_email(session['email'])

    competition = competitionsEngine.getCompetition(competitionId)

    error_code = ""
    if not competitionsEngine.can_update_routes(user,competition):
        error_code = "error5314"

    gymid = competition['gym_id']
    gym = competitionsEngine.get_gym(gymid)
    routesid = competition.get('routesid')
    routes = competitionsEngine.get_routes(routesid)
    routesName = routes.get('name')

    if len(competition.get('climbers').values())>0 and 'lastname' in list(competition.get('climbers').values())[0].keys():
        sorted_data = dict(sorted(competition.get('climbers').items(), key=lambda x: x[1]['lastname'].upper()))
        competition['climbers']= sorted_data

    # library= {}
    # library['tracks'] = tracks
    # playlist = json.dumps(playlist)
    # u = url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message)
    # return redirect(url_for('getRandomPlaylist', playlistName=playlistName, playlist=playlist,
    #                       subheader_message=subheader_message,
    #                       library=None,
    #                       **session))

    return render_template("competitionRoutes.html",
                           error_code=error_code,
                           user=user,
                           gym=gym,
                           gymid=gymid,
                           routesid=routesid,
                           routesName=routesName,
                           routes=routes,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)

# enter competition climbed routes for a climber and save them
@app_ui.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['GET'])
@login_required
def routes_climbed(competitionId, climberId):

    if climberId is not None:
        climber = competitionsEngine.getClimber(competitionId,climberId)

    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No climber found",
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
        return redirect(url_for('app_ui.competitionRoutesList', competitionId=competitionId))


    routesid = competition.get('routesid')
    routes = competitionsEngine.get_routes(routesid)

    climber_name = climber.get('name')
    climber_club = climber.get('club')

    #routes = routes['routes']
    subheader_message = str(climber_name)+" - "+str(climber_club)

    return render_template("competitionRoutesEntry.html", climberId=climberId,
                           climber=climber,
                           routes=routes,
                           subheader_message=subheader_message,
                           competition=competition,
                           competitionId=competitionId,
                           reference_data=competitionsEngine.reference_data,
                           **session)


@app_ui.route('/competitionRoutesEntry/<competitionId>/climber/<climberId>', methods=['POST'])
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
                                   subheader_message="Routes saved",
                                    reference_data=competitionsEngine.reference_data,
                                   **session)

        climber = competitionsEngine.getClimber(competitionId,climberId)

    if climber is None:
        return render_template('competitionDashboard.html', sortedA=None,
                               subheader_message="No climber found",
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



@app_ui.route('/migrategyms')
def migrategyms():
    gyms = competitionsEngine.get_gyms()

    nanterre = gyms["1"]
    nanterre['logoimg'] = 'logo-ESN-HD-copy-1030x1030.png'
    nanterre['homepage'] = 'https://www.esnanterre.com/'

    competitionsEngine.update_gym("1", "667", json.dumps(nanterre))
    return redirect(url_for('app_ui.gyms'))




######## GYMS
@app_ui.route('/gyms')
def gyms():
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    ## for future usage to only show confirmed gyms
    #gyms = competitionsEngine.get_gyms(status=competitionsEngine.reference_data.get('gym_status').get('confirmed'))
    gyms = competitionsEngine.get_gyms()
    
    can_create_gym = False
    email = session.get('email')
    user = None
    home_gym = None
    permissioned_gyms = None
    if email is not None:
        user = competitionsEngine.get_user_by_email(email)
        if user is None: # this happens when switching between dev and prod servers
            session.clear()
            return redirect("/")
        u = User.from_dict(user)
        home_gym = u.get_home_gym()
        if home_gym is not None:
            home_gym = competitionsEngine.get_gym(home_gym)
        permissioned_gyms = competitionsEngine.get_gyms_by_ids(u.get_permissions('gyms'))

        # Remove gyms already present in home_gym or permissioned_gyms
        if home_gym and home_gym.get('id') in gyms:
            del gyms[home_gym['id']]

        if home_gym and home_gym.get('id') in permissioned_gyms:
            del permissioned_gyms[home_gym['id']]

        # remove permissioned gyms from rest of gyms    
        if permissioned_gyms:
            for gym_id in permissioned_gyms.keys():
                if gym_id in gyms:
                    del gyms[gym_id]

    if user is not None:
        can_create_gym = competitionsEngine.can_create_gym(user)
    name = session.get('name')

    if name is None:
        name = ""

    if not permissioned_gyms:
        permissioned_gyms = None

    return render_template('gyms.html',
                           competitionId=None,
                           user=user,
                           gyms=gyms,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=email,
                           logged_name=name,
                           can_create_gym=can_create_gym,
                           home_gym=home_gym,
                           permissioned_gyms=permissioned_gyms,
                            **session)




@app_ui.route('/gyms/<gymid>')
def gym_by_id(gymid):
    gym = competitionsEngine.get_gym(gymid)
    #gym['routesid']='abc1'

    if gym is None or len(gym) == 0:
        return redirect('/gyms')
    
    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    
    #routes = all_routes.get(routesid)
    can_create_gym = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_can_edit_gym = False
    routes_dict = competitionsEngine.get_routes_by_gym_id(gymid)
    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is not None:
        user_can_edit_gym = competitionsEngine.can_edit_gym(user, gym)
        can_create_gym = competitionsEngine.can_create_gym(user)
     
    #routes1 = competitionsEngine.get_routes(gym['routesid'])
    routes = routes_dict.get(gym['routesid'])
    routesid = gym['routesid']
    return render_template('gym-main.html',
                           gymid=gymid,
                           routesid=routesid,
                           gyms=None,
                           gym=gym,
                           routes=None,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                           )


@app_ui.route('/gyms/<gymid>/qrcode')
def gym_qrcode_by_id(gymid):
    gym = competitionsEngine.get_gym(gymid)
    #gym['routesid']='abc1'

    if gym is None or len(gym) == 0:
        return redirect('/gyms')
    
    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    
    #routes = all_routes.get(routesid)
    can_create_gym = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_can_edit_gym = False
    routes_dict = competitionsEngine.get_routes_by_gym_id(gymid)
    user = competitionsEngine.get_user_by_email(session.get('email'))
    if user is not None:
        user_can_edit_gym = competitionsEngine.can_edit_gym(user, gym)
        can_create_gym = competitionsEngine.can_create_gym(user)
     
    #routes1 = competitionsEngine.get_routes(gym['routesid'])
    routes = routes_dict.get(gym['routesid'])
    routesid = gym['routesid']
    return render_template('gym-qrcode.html',
                           gymid=gymid,
                           routesid=routesid,
                           gyms=None,
                           gym=gym,
                           routes=None,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                           )




@app_ui.route('/gyms/<gym_id>/<routesid>', methods=['GET'])
#@login_required
def gym_routes_new(gym_id, routesid):

    gym = competitionsEngine.get_gym(gym_id)
    all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    routes = all_routes.get(routesid)
    can_create_gym = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_can_edit_gym = False
    if user is not None:
        user_can_edit_gym = competitionsEngine.can_edit_gym(user, gym)
        can_create_gym = competitionsEngine.can_create_gym(user)
        #activities = skala_api.get_activities()


    return render_template('gym-routes.html',
                           gymid=gym_id,
                           routesid=routesid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                           )



@app_ui.route('/gyms/<gym_id>/<routesid>/beta', methods=['GET'])
#@login_required
def gym_routes_new_beta(gym_id, routesid):

    gym = competitionsEngine.get_gym(gym_id)
    all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    routes = all_routes.get(routesid)
    can_create_gym = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_can_edit_gym = False
    if user is not None:
        user_can_edit_gym = competitionsEngine.can_edit_gym(user, gym)
        can_create_gym = competitionsEngine.can_create_gym(user)
        #activities = skala_api.get_activities()


    return render_template('gym-routes-beta.html',
                           gymid=gym_id,
                           routesid=routesid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                           )






@app_ui.route('/gyms/<gymid>/data')
def gym_data(gymid):
    fullname = request.args.get('fullname')
    nick = request.args.get('nick')
    email = request.args.get('email')
    sex = request.args.get('sex')
    club = request.args.get('club')
    category = request.args.get('category')

    gym = competitionsEngine.get_gym(gymid)
    routes = competitionsEngine.get_routes(gym['routesid'])
    gym['rows']=routes
    return json.dumps(gym)


@app_ui.route('/gyms/<gymid>/edit', methods=['GET'])
@login_required
def gym_edit(gymid):
    

    gym = competitionsEngine.get_gym(gymid)
    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    routes = all_routes.get(gym['routesid'])
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_list = competitionsEngine.get_all_user_emails()


    if not competitionsEngine.has_permission_for_gym(gymid, user):
        return render_template('competitionNoPermission.html',
                               error_code="error5315",
                               competitionId=None,
                               gyms=gyms,
                               reference_data=competitionsEngine.reference_data,
                               **session)

    return render_template('gymedit.html',
                           gymid=gymid,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           all_routes=all_routes,
                           user_list=user_list,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           )




# this is the old HTML javascript form batch routes editor
@app_ui.route('/gyms/<gym_id>/<routesid>/edit', methods=['GET'])
@login_required
def gym_routes_edit(gym_id, routesid):
    gym = competitionsEngine.get_gym(gym_id)
    all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    routes = all_routes.get(routesid)

    user = competitionsEngine.get_user_by_email(session.get('email'))


    if not competitionsEngine.has_permission_for_gym(gym_id, user):
        return render_template('competitionNoPermission.html',
                               error_code="error5315",
                               competitionId=None,
                               gyms=gyms,
                               reference_data=competitionsEngine.reference_data,
                               **session)

    return render_template('gym-routes-batch-edit.html',
                           gymid=gym_id,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           )




@app_ui.route('/gyms/<gymid>/climbers')
def gym_climbers_by_id(gymid):
    gym = competitionsEngine.get_gym(gymid)
    #gym['routesid']='abc1'

    all_routes = competitionsEngine.get_routes_by_gym_id(gymid)
    
    #routes = all_routes.get(routesid)
    can_create_gym = False
    user = competitionsEngine.get_user_by_email(session.get('email'))
    user_can_edit_gym = False
    routes_dict = competitionsEngine.get_routes_by_gym_id(gymid)

    #routes1 = competitionsEngine.get_routes(gym['routesid'])
    routes = routes_dict.get(gym['routesid'])
    routesid = gym['routesid']
    return render_template('gym-climbers.html',
                           gymid=gymid,
                           routesid=routesid,
                           gyms=None,
                           gym=gym,
                           routes=None,
                           all_routes=all_routes,
                           user=user,
                           reference_data=competitionsEngine.reference_data,
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                           )



@app_ui.errorhandler(413)
def request_entity_too_large(error):    
    print(error)
    content_length = request.content_length
    print(content_length)
    return 'Request Too Large', 413


#saving old type of html routes editor
@app_ui.route('/gyms/<gymid>/<routesid>/edit', methods=['POST'])
@login_required
def gym_routes_save(gymid, routesid):
    #args1 = request.args

    #body = request.data
    #bodyj = request.json

    formdata = request.form.to_dict(flat=False)

    routeid = formdata['routeid']
    routeline = formdata['routeline']
    color1 = formdata['color1']
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
        return redirect(url_for("app_ui.fsgtlogin"))

    if delete is not None:
        
        result = competitionsEngine.delete_routes(routesid)

        if result.get('status') == 'success':
            gymroutes = gym.get('routesid')
        
            return redirect(url_for('app_ui.gym_routes_edit', 
                                    gym_id=gymid, routesid=gymroutes, label=result.get('label'), message=result.get('message'), level='success'))
        else:
            message = result.get('message')
            return redirect(url_for('app_ui.gym_routes_edit', 
                                    gym_id=gymid, routesid=routesid, label=result.get('label'), message=result.get('message'), level='danger'))


    routes = []
    for i, routeline1 in enumerate(routeline):
        if routeid[i] == '0':
            routeid[i]=str(uuid.uuid4().hex)
        oneline = competitionsEngine._get_route_dict(routeid[i], str(i+1), routeline[i], color1[i],
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
        return redirect(url_for('app_ui.gym_routes_edit', 
                                    gym_id=gymid, routesid=newroutesid, label="routes_copied", level='success'))

    competitionsEngine.update_routes(routesid, routes_dict)

    # pickup the default routes to be rendered
    routes = competitionsEngine.get_routes(gym.get('routesid'))

    return redirect(url_for('app_ui.gym_routes_edit', 
                                    gym_id=gymid, routesid=routesid, label="routes_saved", level='success'))
   


@app_ui.route('/gyms/<gym_id>/<routesid>/routes_csv')
def downloadRoutesCsv(gym_id, routesid):

    gym = competitionsEngine.get_gym(gym_id)
    all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    routes = all_routes.get(routesid)

    filename = 'routes-'+routes['id']
    routes = routes['routes']

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

    data_file = open('jsonoutput2.csv', 'w', newline='')
    csv_writer = csv.writer(data_file)

    count = 0
    for route in routes:
        route.pop('id',None)
        route.pop('colorfr',None)
        
        if count == 0:
            header = route.keys()
            csv_writer.writerow(header)
            writer.writerow(header)
            count += 1
        out = {}
        

        csv_writer.writerow(route.values())
        writer.writerow(route.values())

    data_file.close()


    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                     "attachment; filename="+filename+".csv"})






# competition tiles
@app_ui.route('/gyms/<gym_id>/<routesid>/download')
def downloadRoutes(gym_id, routesid):

    gym = competitionsEngine.get_gym(gym_id)
    all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    routes = all_routes.get(routesid)

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

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

    data_file = open('jsonoutput.csv', 'w', newline='')
    csv_writer = csv.writer(data_file)

    count = 0
    data = []
    header = routes['routes'][0].copy()
    header.pop('id')
    header.pop('colorfr')
    #header.pop('color_modifier')
    header.pop('opendate')
    header.pop('notes')
    header.pop('openedby')
    
    data = routes['routes']
    csv_writer.writerow(header)
    writer.writerow(header)
    count += 1
    out = {}
    #rethtml="<table>"
    #rethtml="<style>p.one { border-style: solid; border-color: red;}"
    rethtml=""

    for route in routes['routes']:
        route.pop('id')
        route.pop('colorfr')
        #route.pop('color_modifier')
        route.pop('opendate')
        route.pop('notes')
        route.pop('openedby')
        
        csv_writer.writerow(route.values())
        writer.writerow(route.values())
        #rethtml+="<tr><td>"+route['routenum']+"</td><td bgcolor="+route['color1']+">&nbsp;&nbsp;&nbsp;</td><td>"+route['grade']+"</td></tr>"
        rethtml+="<div style='border:1px solid "+route['color1']+"'>"+str(route['routenum'])+"</td><td bgcolor="+route['color1']+">&nbsp;&nbsp;&nbsp; "+route['grade']+" "
        rethtml+="</div>"

    #rethtml+="</table>"
    data_file.close()

    return render_template('gym-print.html',
                           gymid=gym_id,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           )


@app_ui.route('/gyms/<gymid>/edittest')
def edit_test(gymid):
    user = competitionsEngine.get_user_by_email(session['email'])

    return render_template('tabletest.html',
                           reference_data=competitionsEngine.reference_data)


@app_ui.route('/gyms/add', methods=['GET'])
@login_required
def gyms_add_form():
    user = competitionsEngine.get_user_by_email(session['email'])

    if competitionsEngine.can_create_gym(user):
        return render_template('gym-add.html',
                           competitionId=None,
                           gyms=gyms,
                           reference_data=competitionsEngine.reference_data,
                           **session)
    else:
        return render_template('competitionNoPermission.html',
                               competitionId=None,
                               gyms=gyms,
                               reference_data=competitionsEngine.reference_data,
                               **session)


@app_ui.route('/gyms/add', methods=['POST'])
@login_required
def gyms_add():
    user = competitionsEngine.get_user_by_email(session['email'])

    can_create_gym = competitionsEngine.can_create_gym(user)
    formdata = request.form.to_dict(flat=False)

    args1 = request.args
    #body = request.data
    #bodyj = request.json
    files = request.files
    gym_id = str(uuid.uuid4().hex)
    imgfilename = None
    if 'file1' in request.files:
        file1 = request.files['file1']
        if file1.filename is not None and len(file1.filename) > 0:
            #random = str(uuid.uuid4().hex)
            imgfilename = gym_id
            imgpath = os.path.join(UPLOAD_FOLDER, gym_id)
            file1.save(imgpath)

    gymName = formdata['gymName'][0]
    numberOfRoutes = formdata['numberOfRoutes'][0]
    if numberOfRoutes is None or len(numberOfRoutes)==0:
        numberOfRoutes = 10  #default value of routes for a gym
    address = formdata['address'][0]
    url = formdata['url'][0]
    organization = formdata['organization'][0]

    routes = competitionsEngine.generate_dummy_routes(int(numberOfRoutes))
    competitionsEngine.upsert_routes(routes['id'], gym_id, routes)
    gym = competitionsEngine.add_gym(user, gym_id, routes['id'], gymName, imgfilename, url, address, organization, [])
    gym['routes'] = routes
    routes_id = routes['id']
    user_can_edit_gym = competitionsEngine.can_edit_gym(user, gym)
    
    #competitionsEngine.update_gym(gym_id, gym)
    #gym2 = competitionsEngine.get_gym(gym_id)
    #all_routes = competitionsEngine.get_routes_by_gym_id(gym_id)
    #routes=gym2['routes']
    #gyms = competitionsEngine.get_gyms()

    return render_template('gym-routes.html',
                           competitionId=None,
                           gymid=gym_id,
                           routesid=routes_id,
                           gyms=None,
                           gym=gym,
                           routes=routes,
                           reference_data=competitionsEngine.reference_data,
                           logged_email=session['email'],
                           user_can_edit_gym=user_can_edit_gym,
                           can_create_gym=can_create_gym,
                            **session)



# Main method for updating gym data 
@app_ui.route('/gyms/<gym_id>/update', methods=['POST'])
@login_required
def gyms_update(gym_id):
    user = competitionsEngine.get_user_by_email(session['email'])

    formdata = request.form.to_dict(flat=False)

    gym = competitionsEngine.get_gym(gym_id)


    if not competitionsEngine.has_permission_for_gym(gym_id, user):
        return render_template('competitionNoPermission.html',
                               error_code="error5315",
                               competitionId=None,
                               gyms=gyms,
                               reference_data=competitionsEngine.reference_data,
                               **session)

    body = request.data
    #bodyj = request.json
    files = request.files
    delete = formdata.get('delete')
    save = formdata.get('save')
    label = "saved"

    imgfilename = None
    if 'file1' in request.files:
        file1 = request.files['file1']
        if len(file1.filename) > 0:
            #random = str(uuid.uuid4().hex)
            imgfilename = gym_id
            #if 'image/svg' in file1.mimetype:
             #   imgfilename += '.svg'
             # the function sending files was modified to recognise svg files
             # it's an ugly fix but it works
            imgpath = os.path.join(UPLOAD_FOLDER, imgfilename)
            file1.save(imgpath)

    gymName = formdata['gymName'][0]
    #numberOfRoutes = formdata['numberOfRoutes'][0]
    address = formdata['address'][0]
    url = formdata['url'][0]
    organization = formdata['organization'][0]
    permissioned_user_id = request.form.get('userId')
    lat = formdata['lat'][0]
    lon = formdata['lon'][0]

    routesidlist = formdata.get('default_routes')
    if routesidlist is not None:
        routesid = formdata['default_routes'][0]

    if delete is not None:
        competitionsEngine.delete_gym(gym_id)
        competitionsEngine.remove_user_permissions_to_gym(user, gym_id)
        if gym.get('logo_img_id') is not None and len(gym.get('logo_img_id')) > 0:
            if os.path.exists(os.path.join(UPLOAD_FOLDER, gym['logo_img_id'])):
                os.remove(os.path.join(UPLOAD_FOLDER, gym['logo_img_id']))
        return redirect(url_for('app_ui.gyms'))

    if routesid is None or len(routesid)==0:
        routesid = gym['routesid']

    if len(permissioned_user_id)>2:
        newuser = competitionsEngine.get_user(permissioned_user_id)
        if newuser is not None:
            competitionsEngine.add_user_permissions_to_gym(newuser, gym_id)

    #gymid, routesid, name, added_by, logo_img_id, homepage, address, organization, routesA):
    gym_json = competitionsEngine.get_gym_json(gym_id, routesid, gymName, None, imgfilename, url, address, organization, None)
    competitionsEngine.update_gym_coordinates(gym_json, lat, lon)
    # the following takes values from gym_json which are not None and applies them to gym
    gym.update((k, v) for k, v in gym_json.items() if v is not None)
    competitionsEngine.update_gym(gym_id, gym)

    return redirect(url_for('app_ui.gym_by_id', gymid=gym_id, label=label, level='success'))







@app_ui.route('/competitionDashboard/loadData')
def loadData():
    competitionsEngine.init()
    subheader_message='data loaded'
    return render_template("competitionDashboard.html", climberId=None,
                           subheader_message=subheader_message,
                           reference_data=competitionsEngine.reference_data)


@app_ui.route('/image/')
def image_route0():
    #bytes_io = competitionsEngine.get_img(img_id)
    #return send_file(bytes_io, mimetype='image/png')

    #return send_file(os.path.join(UPLOAD_FOLDER, img_id))
    #return app_ui.send_static_file("images/favicon.png")
    return app_ui.send_static_file("images/fsgt-logo-me.png")

def is_svg(file_path):
    """Check if the file content indicates it is an SVG."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read(1024)  # Read the first 1KB of the file
            return '<svg' in content or content.strip().startswith('<?xml')
    except Exception as e:
        return False


@app_ui.route('/image/<img_id>')
def image_route(img_id):
    #bytes_io = competitionsEngine.get_img(img_id)
    #return send_file(bytes_io, mimetype='image/png')

    #return send_file(os.path.join(UPLOAD_FOLDER, img_id))

    #print('image_route', img_id)
    if (img_id is not None and os.path.exists(os.path.join(UPLOAD_FOLDER, img_id))):
        is_svg_file = is_svg(os.path.join(UPLOAD_FOLDER, img_id))

        if is_svg_file:
            mime_type = 'image/svg+xml'
        else:
            mime_type = None
            
            #mime_type = 'application/octet-stream'  # Default MIME type
        
        return send_from_directory(UPLOAD_FOLDER, img_id, mimetype=mime_type)
    else:
        #return app_ui.send_static_file("images/favicon.png")
        return app_ui.send_static_file("images/fsgt-logo-me.png")
    



@app_ui.route('/gym/<gymid>/qr', methods=['GET'])
def gym_qr(gymid):
    try:
         # Construct the URL
        base_url = request.url_root
        url = f"{base_url}gyms/{gymid}"

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(url)

        #img_1 = qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer())
        #img_2 = qr.make_image(image_factory=StyledPilImage, color_mask=RadialGradiantColorMask())
        img_1 = qr.make_image(image_factory=StyledPilImage, embeded_image_path="public/images/favicon.png")

        #qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, image_factory=StyledPilImage)
        #qr.add_data('Some data')

        #img = qrcode.make(url)
        #img = qr.make_image(embeded_image_path="images/fsgt-logo-me.png")
        
        buffer = io.BytesIO()
        img_1.save(buffer)
        buffer.seek(0)

        response = make_response(buffer.getvalue())
        #response.headers['Content-Disposition'] = 'attachment; filename=qr-code.png'
        response.mimetype = 'image/png' 

        return response
    except Exception as e:
        print(e)
        return 'Internal Server Error', 500
    


@app_ui.route('/competition/<competitionid>/qrcode', methods=['GET'])
def competition_qr(competitionid):
    try:
        comp = competitionsEngine.getCompetition(competitionid)
         # Construct the URL
        # Extract competition details
        comp_id = comp['id']
        comp_name = comp['name']
        comp_date = comp['date']
        comp_gym = comp['gym']
        
        # Construct the URL
        base_url = request.url_root
        url = f"{base_url}competitionDetails/{competitionid}"

        # Create vCalendar text
        vcalendar_text = f'''
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Your Organization//Your Product//EN
BEGIN:VEVENT
UID:{comp_id}
DTSTAMP:{comp_date.replace("-", "")}T120000Z
DTSTART;TZID=Europe/Paris:{comp_date.replace("-", "")}T120000
SUMMARY:{comp_name}
LOCATION:{comp_gym}
DESCRIPTION: {url}
URL:{url}
END:VEVENT
END:VCALENDAR
        '''.strip()

        #img_1 = qr.make_image(image_factory=StyledPilImage, module_drawer=RoundedModuleDrawer())
        #img_2 = qr.make_image(image_factory=StyledPilImage, color_mask=RadialGradiantColorMask())
        #img_1 = qr.make_image(image_factory=StyledPilImage, embeded_image_path="public/images/favicon.png")

        #qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, image_factory=StyledPilImage)
        #qr.add_data('Some data')

        #img = qrcode.make(url)
        #img = qr.make_image(embeded_image_path="images/fsgt-logo-me.png")
        
        # Generate QR code
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(vcalendar_text)
        img = qr.make_image()

        buffer = io.BytesIO()
        img.save(buffer)
        buffer.seek(0)


        response = make_response(buffer.getvalue())
        #response.headers['Content-Disposition'] = 'attachment; filename=qr-code.png'
        response.mimetype = 'image/png' 

        return response
    except Exception as e:
        print(e)
        return 'Internal Server Error', 500
    




